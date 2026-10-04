"""Raccordement UNIQUE des vraies données → `GabaritInput` (CDC §11).

C'est le SEUL endroit où le réel entre. `compute_gabarit` reste pur : il ne sait pas
si l'entrée vient d'ici ou d'une fixture. Correspondances (CDC §11) :
  cadastre → parcel · PLU (zonage.py) → recul (setbackM)/maxFootprint/maxHeight ·
  classification limites (limites.py = adjacence cadastre + BD TOPO) → type de chaque
  setback (road/side/rear) + géométrie · PPR (cascade_results + spatial_layers) →
  exclusions · analyse → applicableRules · dossier → sources.

GABARIT-2 : la classification des limites passe la mesure (0 faux/70, cf. A0-2-MESURE.md)
→ elle est SERVIE. Chaque limite porte sa source de mesure (BD TOPO, millésime lu dans
`data_sources`, jamais codé en dur) ; le recul appliqué et son article PLU sont dans le
détail de la règle. Une parcelle sans façade / à limite non qualifiée → « Calcul incomplet ».
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..faisabilite.zonage import resolve_zone
from ..faisabilite.zone_servie import zone_dominante
from ..plu.destinations import regles_zone
from ._geom import geojson_from_shape, to_wgs
from .contract import (
    ApplicableRule,
    Exclusion,
    GabaritInput,
    MaxFootprint,
    MaxHeight,
    ParcelInput,
    RegulatorySource,
    Setback,
)
from .limites import classify_parcel_limits

CADASTRE_PROVIDER = "DGFiP — cadastre (PCI)"
PLU_PROVIDER = "LABUSE — règlement PLU validé (config/plu_destinations)"
PPR_PROVIDER = "DEAL Réunion — PPR (zonage réglementaire)"
SUP_PROVIDER = "GPU / API Carto — servitudes d'utilité publique (assiettes)"


@dataclass
class BuildResult:
    input: GabaritInput
    blocking: list[str] = field(default_factory=list)
    raccordement: dict = field(default_factory=dict)


def _num(x) -> Optional[float]:
    """float réel uniquement (None = silence ; 'a_verifier' = ambigu → écarté)."""
    return float(x) if isinstance(x, (int, float)) else None


def _bdtopo_millesime(session: Session) -> str:
    """Millésime BD TOPO lu depuis data_sources (jamais codé en dur)."""
    row = session.execute(text(
        "SELECT ds.source_millesime FROM data_sources ds "
        "WHERE ds.id = (SELECT data_source_id FROM spatial_layers WHERE kind='voirie' "
        "AND data_source_id IS NOT NULL LIMIT 1)"
    )).first()
    return (row[0] if row and row[0] else "millésime non enregistré")


def _feuille_absente(commune: str, zone: str, rubrique: str, feuille: str) -> bool:
    """La feuille de règle est-elle ABSENTE du règlement de la zone (silence prouvé) ? False si la
    zone n'a pas de règles propres (renvoi — traité à part) pour ne pas confondre silence et renvoi."""
    reg = regles_zone(commune, zone) or {}
    if not reg:
        return False
    leaf = (reg.get(rubrique) or {}).get(feuille)
    return not leaf or leaf.get("absent") is True


def _feuille_forme_hors_schema(commune: str, zone: str, rubrique: str, feuille: str, valuekey: str) -> bool:
    """Feuille VALIDÉE mais de forme non chiffrée (ex. hauteur en prospect L ≥ H : statut valide,
    pas de valeur numérique)."""
    reg = regles_zone(commune, zone) or {}
    leaf = (reg.get(rubrique) or {}).get(feuille) or {}
    return str(leaf.get("statut")) == "valide" and not isinstance(leaf.get(valuekey), (int, float))


def _feuille_citation(commune: str, zone: str, rubrique: str, feuille: str) -> str:
    reg = regles_zone(commune, zone) or {}
    leaf = (reg.get(rubrique) or {}).get(feuille) or {}
    return " ".join(f"{leaf.get('citation', '')} {leaf.get('formule', '')}".split())[:220]


def _feuille_article(commune: str, zone: str, rubrique: str, feuille: str) -> str:
    """« Art. U 10.2 » de la feuille (article tel qu'écrit au YAML) — pour citer la source à l'écran."""
    reg = regles_zone(commune, zone) or {}
    leaf = (reg.get(rubrique) or {}).get(feuille) or {}
    a = re.sub(r"^\s*articles?\s+", "", str(leaf.get("article") or "").strip(), flags=re.I)
    return f"Art. {a}" if a else ""


def _voie_citation_flags(commune: str, zone: str) -> tuple[bool, bool, str, str]:
    """Lit la citation validée `retraits.voie` de la (commune, zone) et dit si elle vise « voies
    ET emprises publiques » (→ arête domaine public = voie) et/ou les « voies privées ». Renvoie
    (emprises_publiques, voies_privees, article, citation). Aucune règle inventée : tout vient du texte."""
    voie = ((regles_zone(commune, zone) or {}).get("retraits") or {}).get("voie") or {}
    if str(voie.get("statut", "")) != "valide":
        return (False, False, "", "")
    txt = f"{voie.get('formule', '')} {voie.get('citation', '')}".lower()
    ep = "emprise" in txt and "publiqu" in txt
    vp = ("voie" in txt or "voies" in txt) and ("priv" in txt)
    return (ep, vp, str(voie.get("article", "") or ""), " ".join(f"{voie.get('formule', '')} "
            f"{voie.get('citation', '')}".split())[:200])


def _multizone_split(session: Session, parcel_id: int):
    """Découpe une parcelle à cheval par zone PLU (plu_gpu_zone, morceaux ≥ 5 %). Retourne
    (zones_constructibles [(code, pct)], exclusions_non_constructibles [(code, pct, geojson4326)],
    bandes_ignorees [(code, pct)]). Une zone A/N est non constructible → exclue (0 implantation),
    jamais bloquante. Le découpage multi-CES (≥ 2 zones constructibles) est hors GABARIT-4."""
    # VITESSE-FIX-1 lot B — la géométrie d'intersection parcelle × plu_gpu_zone est précalculée
    # (`parcel_couche_intersection`) quand la table est FRAÎCHE : on lit la géométrie brute rangée
    # (sans perte) et on réapplique EXACTEMENT les mêmes expressions aval → sortie identique. Sinon,
    # calcul au vol (repli). `area_m2` rangé = ST_Area(ST_Intersection(p, z)) [commutatif → identique].
    # fraiche_zone : n'est vrai que si la population ZONE PLU a été explicitement construite
    # (build --with-zone). Par défaut (build servitudes seulement) → False → calcul au vol.
    from ..couche_intersection import fraiche_zone as _inter_fraiche_zone
    if _inter_fraiche_zone(session):
        sql = """
        SELECT z.attrs->>'libelle' AS code, z.attrs->>'typezone' AS tz,
               pci.area_m2 AS area_m2,
               pci.area_m2 / NULLIF(ST_Area(p.geom_2975), 0) AS pct,
               ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(pci.geom_2975, 4326), 3)) AS gj,
               ST_AsText(ST_CollectionExtract(pci.geom_2975, 3)) AS g2975
        FROM parcel_couche_intersection pci
        JOIN spatial_layers z ON z.id = pci.layer_id
        JOIN parcels p ON p.id = pci.parcel_id
        WHERE pci.parcel_id = :pid AND pci.kind = 'plu_gpu_zone'
        """
    else:
        sql = """
        SELECT z.attrs->>'libelle' AS code, z.attrs->>'typezone' AS tz,
               ST_Area(ST_Intersection(z.geom_2975, p.geom_2975)) AS area_m2,
               ST_Area(ST_Intersection(z.geom_2975, p.geom_2975)) / NULLIF(ST_Area(p.geom_2975), 0) AS pct,
               ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(
                   ST_Intersection(z.geom_2975, p.geom_2975), 4326), 3)) AS gj,
               ST_AsText(ST_CollectionExtract(ST_Intersection(z.geom_2975, p.geom_2975), 3)) AS g2975
        FROM spatial_layers z, parcels p
        WHERE p.id = :pid AND z.kind = 'plu_gpu_zone' AND ST_Intersects(z.geom_2975, p.geom_2975)
        """
    rows = session.execute(text(sql), {"pid": parcel_id}).mappings().all()
    cons, noncons, bandes = [], [], []
    for r in rows:
        pct = float(r["pct"] or 0)
        if pct < 0.05:
            if pct > 0:
                bandes.append((r["code"], round(pct * 100, 1)))
            continue
        geo = json.loads(r["gj"]) if r["gj"] else None
        geo = geo if geo and geo.get("coordinates") else None
        rec = {"code": r["code"], "pct": round(pct * 100, 1), "area": float(r["area_m2"] or 0),
               "gj": geo, "wkt": r["g2975"]}
        (noncons if str(r["tz"]) in ("A", "N") else cons).append(rec)
    return cons, noncons, bandes


def _touche_ravine(session: Session, parcel_id: int) -> bool:
    """La parcelle longe-t-elle une ravine BD TOPO ou le trait de côte (≤ 8 m) ?"""
    return bool(session.execute(text(
        "SELECT EXISTS(SELECT 1 FROM spatial_layers g WHERE g.kind IN ('ravine','trait_de_cote') "
        "AND ST_DWithin(g.geom_2975, (SELECT geom_2975 FROM parcels WHERE id=:pid), 8))"
    ), {"pid": parcel_id}).scalar())


def build_gabarit_input(session: Session, idu: str) -> Optional[BuildResult]:
    """Assemble l'entrée réelle. Renvoie None si la parcelle est inconnue.
    `BuildResult.blocking` liste les données réglementaires nécessaires manquantes."""
    row = session.execute(text(
        "SELECT id, commune, ST_Area(geom_2975) AS surface_m2, "
        "ST_AsGeoJSON(geom) AS geojson FROM parcels WHERE idu = :i"
    ), {"i": idu}).mappings().first()
    if not row:
        return None
    pid, commune = row["id"], row["commune"]
    surface = float(row["surface_m2"]) if row["surface_m2"] is not None else None
    geom = json.loads(row["geojson"]) if row["geojson"] else None

    blocking: list[str] = []
    racc: dict = {"parcelle": {"idu": idu, "commune": commune,
                              "surface_m2": round(surface, 1) if surface else None}}

    cadastre_src = RegulatorySource(document="Cadastre — parcelle " + idu, provider=CADASTRE_PROVIDER)
    sources = [cadastre_src]
    applicable: list[ApplicableRule] = []
    max_footprint: Optional[MaxFootprint] = None
    max_height: Optional[MaxHeight] = None
    recul_voie = recul_sep = None
    plu_zone_src: Optional[RegulatorySource] = None

    # --- zone dominante + multi-zones (découpage) ----------------------------
    zs = zone_dominante(session, pid)
    racc["zone"] = {"code": zs.zone, "famille": zs.zone_fam, "a_cheval": zs.a_cheval}
    work_zone = zs.zone            # zone dont on lit les règles (réassignée si découpage)
    mz_sub_geom_wkt: Optional[str] = None      # morceau constructible (2975) à classer
    mz_extra_neighbors: list[str] = []         # parties A/N (2975) = voisins de la coupure interne
    if zs.a_cheval:
        cons, noncons, bandes = _multizone_split(session, pid)
        racc["multizone"] = {"constructibles": [(c["code"], c["pct"]) for c in cons],
                             "non_constructibles": [(c["code"], c["pct"]) for c in noncons],
                             "bandes_ignorees": bandes}
        if not cons:
            blocking.append("parcelle entièrement en zone non constructible (A/N)")
        elif len(cons) >= 2:
            # ≥ 2 zones constructibles distinctes = découpage multi-CES → hors GABARIT-4
            blocking.append("parcelle sur ≥ 2 zones constructibles distinctes ("
                            + ", ".join(c["code"] for c in cons) + ") : découpage multi-CES non servi")
        elif not cons[0]["gj"] or not cons[0]["wkt"]:
            blocking.append("découpage multi-zones : géométrie du morceau constructible indisponible")
        else:
            # une seule zone constructible : le gabarit est calculé sur CE morceau (la/les partie(s)
            # A/N non constructibles sont hors du morceau et deviennent des voisins de la coupure).
            work_zone = cons[0]["code"]
            mz_sub_geom_wkt = cons[0]["wkt"]
            geom = cons[0]["gj"]                 # contour = partie constructible
            surface = cons[0]["area"]            # surface + plafond calculés sur le morceau
            mz_extra_neighbors = [c["wkt"] for c in noncons if c["wkt"]]
            racc["multizone"]["servie_sur"] = f"{work_zone} ({cons[0]['pct']:g} %)"
            for c in bandes:
                racc.setdefault("bandes_ignorees", []).append(f"zone {c[0]} non retenue, {c[1]:g} %")
    if not work_zone:
        blocking.append("zone PLU indéterminée")

    # --- règles PLU via zonage.py (validées-only ; propose = bloquant) --------
    if work_zone:
        zr = resolve_zone(work_zone, commune)
        if zr is None:
            blocking.append(f"zone {work_zone} hors calibrage PLU")
        elif getattr(zr, "regle_non_validee", None):
            blocking.append(f"règle PLU non validée (propose) : {zr.regle_non_validee}")
        elif not getattr(zr, "calibree", False):
            blocking.append(f"PLU non calibré pour la zone {work_zone} (estimation générique)")
        else:
            # renvoi de zone (AU→U) : zonage.py résout et cite la zone de rattachement (via_renvoi)
            via_renvoi = getattr(zr, "via_renvoi", None)
            racc["zone"]["via_renvoi"] = via_renvoi
            plu_zone_src = RegulatorySource(
                document=f"PLU — {commune}", zone=work_zone,
                provider=PLU_PROVIDER + (f" · {via_renvoi}" if via_renvoi else ""))
            sources.append(plu_zone_src)
            emp = _num(getattr(zr, "emprise_sol_pct", None))
            haut = _num(getattr(zr, "hf_m", None))  # faîtage : sert l'extrusion 3D
            egout = _num(getattr(zr, "he_m", None))
            recul_voie = _num(getattr(zr, "recul_voirie_m", None))
            recul_sep = _num(getattr(zr, "recul_limites_sep_m", None))
            if recul_voie is None and getattr(zr, "recul_voirie_alignement", False):
                recul_voie = 0.0   # alignement = recul 0 explicite, sourcé
            if recul_sep is None and getattr(zr, "recul_limites_alignement", False):
                recul_sep = 0.0
            racc["plu"] = {"emprise_pct": emp, "hauteur_faitage_m": haut, "hauteur_egout_m": egout,
                           "recul_voie_m": recul_voie, "recul_sep_m": recul_sep, "source": plu_zone_src.document}
            silence_total = (not regles_zone(commune, work_zone) and not via_renvoi
                             and emp is None and haut is None and recul_voie is None and recul_sep is None)
            if silence_total:
                # zone SANS règles d'implantation propres et sans renvoi résolu (ex. Le Port Uv —
                # destinations réglées, forme bâtie non réglée). Pas de recul → gabarit incalculable :
                # bloc honnête, distinct de « CES non validée ».
                blocking.append(f"zone {work_zone} sans règles d'implantation propres : le règlement ne "
                                "fixe ni recul, ni hauteur, ni emprise (renvoi non résolu ou silence total)")
            else:
                if emp is not None:
                    max_footprint = MaxFootprint(ruleId=f"{work_zone}-emprise", percent=emp,
                                                 status="integrated", source=plu_zone_src)
                    applicable.append(ApplicableRule(id=f"{work_zone}-emprise", label="Emprise maximale",
                                                     category="maxFootprint", integrationStatus="integrated",
                                                     detail=f"{emp:g} %", source=plu_zone_src))
                elif _feuille_absente(commune, work_zone, "emprise_sol", "ces"):
                    # silence prouvé du règlement : servi « non réglementé » (donnée sourcée, CDC §3)
                    max_footprint = MaxFootprint(ruleId=f"{work_zone}-emprise", percent=None,
                                                 status="absent", source=plu_zone_src)
                    applicable.append(ApplicableRule(
                        id=f"{work_zone}-emprise", label="Emprise au sol", category="maxFootprint",
                        integrationStatus="integrated",
                        detail=f"non réglementée — PLU {commune} zone {work_zone} : silence du règlement",
                        source=plu_zone_src))
                    racc.setdefault("silences", []).append("emprise_sol.ces")
                else:
                    blocking.append("emprise (CES) non réglementée / non validée")
                if haut is not None:
                    # faîtage servi ; l'égout, s'il est aussi fixé, part en sous-ligne (GABARIT-6)
                    max_height = MaxHeight(ruleId=f"{work_zone}-hauteur", meters=haut,
                                           status="integrated", basis="faitage",
                                           egoutMeters=egout if egout is not None else None,
                                           source=plu_zone_src)
                    applicable.append(ApplicableRule(id=f"{work_zone}-hauteur", label="Hauteur maximale",
                                                     category="maxHeight", integrationStatus="integrated",
                                                     detail=f"{haut:g} m", source=plu_zone_src))
                elif egout is not None:
                    # PLU-CALIBRAGE-8 — le règlement borne la hauteur À L'ÉGOUT sans fixer de faîtage
                    # (ex. Salazie U 10, La Possession, Le Tampon). On sert cette valeur telle quelle :
                    # l'écran dit « à l'égout » (jamais un faîtage implicite) et la source cite l'article.
                    art = _feuille_article(commune, work_zone, "hauteur", "egout")
                    cit = _feuille_citation(commune, work_zone, "hauteur", "egout")
                    egout_src = RegulatorySource(document=f"PLU — {commune}", zone=work_zone,
                                                 article=art or None, provider=PLU_PROVIDER)
                    max_height = MaxHeight(ruleId=f"{work_zone}-hauteur", meters=egout,
                                           status="integrated", basis="egout", source=egout_src)
                    applicable.append(ApplicableRule(
                        id=f"{work_zone}-hauteur", label="Hauteur réglementaire — à l'égout",
                        category="maxHeight", integrationStatus="integrated",
                        detail=f"{egout:g} m à l'égout" + (f" — {cit}" if cit else ""),
                        source=egout_src))
                    racc.setdefault("hauteur_egout", {"m": egout, "article": art})
                elif _feuille_forme_hors_schema(commune, work_zone, "hauteur", "faitage", "m"):
                    # hauteur en PROSPECT (L ≥ H) : validée mais non chiffrée → non intégrée. 2D servie,
                    # 3D indisponible. Aucun calcul de H depuis L (hors mandat).
                    cit = _feuille_citation(commune, work_zone, "hauteur", "faitage")
                    max_height = MaxHeight(ruleId=f"{work_zone}-hauteur", meters=None,
                                           status="not_integrated", source=plu_zone_src)
                    applicable.append(ApplicableRule(
                        id=f"{work_zone}-hauteur", label="Hauteur réglementaire (prospect L ≥ H)",
                        category="maxHeight", integrationStatus="not_integrated",
                        detail=f"non chiffrée — {cit}" if cit else "non chiffrée (prospect L ≥ H)",
                        source=plu_zone_src))
                    racc.setdefault("non_integrees", []).append("hauteur (prospect)")
                else:
                    blocking.append("hauteur réglementaire non validée")
                applicable.append(ApplicableRule(id="STAT", label="Stationnement", category="other",
                                                 integrationStatus="not_integrated",
                                                 detail="Règle connue, non chiffrée", source=plu_zone_src))
                applicable.append(ApplicableRule(id="ESP", label="Espaces libres", category="other",
                                                 integrationStatus="not_integrated",
                                                 detail="Règle connue, non chiffrée", source=plu_zone_src))

    # --- risques : PPR zone rouge (réglementaire, per-parcelle) ---------------
    ppr = session.execute(text(
        "SELECT result, severity, detail FROM cascade_results "
        "WHERE parcel_id = :pid AND layer_name = 'risques' ORDER BY (result = 'HARD_EXCLUDE') DESC LIMIT 1"
    ), {"pid": pid}).mappings().first()
    ppr_src = RegulatorySource(document="PPR — zonage réglementaire", provider=PPR_PROVIDER)
    ppr_rouge = bool(ppr and ppr["result"] == "HARD_EXCLUDE" and "PPR zone rouge" in (ppr["detail"] or ""))
    racc["ppr"] = {"result": ppr["result"] if ppr else None,
                   "detail": ppr["detail"] if ppr else None, "rouge": ppr_rouge}
    sources.append(ppr_src)
    applicable.append(ApplicableRule(
        id="PPR", label="PPR — analyse", category="exclusion",
        integrationStatus="integrated" if ppr_rouge else "not_integrated",
        detail=(ppr["detail"] if ppr else "Aucune zone rouge PPR sur la parcelle"), source=ppr_src))
    exclusions: list[Exclusion] = []
    if ppr_rouge:
        # GEOMETRIE-1 lot A — ST_ClipByBox2D avant l'intersection fine (même optimisation que
        # _greve_certaine_m2, cf. faisabilite/db.py). Les polygones PPR INTERDICTION montent à
        # 320 k sommets ; les rogner d'abord à la bbox de la parcelle rend l'intersection O(petit).
        # Résultat STRICTEMENT identique : parcelle ⊆ sa bbox, donc rien de ce qui est coupé
        # ne pouvait intersecter la parcelle. ST_MakeValid par sécurité sur le morceau clippé.
        gj = session.execute(text(
            "SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(ST_Intersection("
            "  ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), p.geom_2975), 4326), 3)) "
            "FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind='ppr' "
            "AND sl.subtype='INTERDICTION' AND ST_Intersects(sl.geom_2975, p.geom_2975) "
            "GROUP BY p.geom_2975"
        ), {"pid": pid}).first()
        if gj and gj[0]:
            geo = json.loads(gj[0])
            if geo.get("coordinates"):
                exclusions.append(Exclusion(id="ppr-rouge", ruleId="PPR", type="ppr_rouge",
                                            label="PPR zone rouge exclue", geometry=geo, source=ppr_src))

    # --- SUP : servitudes d'utilité publique déduites de la zone d'implantation ----------------
    # RETOUCHES-1 lot D.15 — ER et EBC sont DÉJÀ retranchés par le résiduel (_GREVE) ; le MOTEUR
    # unique GEOMETRIE-1 (compute_gabarit) ignorait encore le SUP. On l'ajoute ICI (kind='sup') :
    # le gabarit-outil ET le résiduel (qui lit l'assiette gabarit) en tiennent désormais compte.
    # Même optimisation que le PPR (ST_ClipByBox2D avant l'intersection fine). Pas de re-run : le
    # prochain run résiduel le prendra (mandat).
    sup_src = RegulatorySource(document="SUP — servitudes d'utilité publique", provider=SUP_PROVIDER)
    sources.append(sup_src)   # fix/sup-source — en MIROIR du PPR (l. ~342) : la source de l'exclusion SUP
    # DOIT figurer au catalogue, sinon validate_input la rejette (« exclusion[sup] : source absente du
    # catalogue ») → compute_gabarit=incomplete → repli residuel_legacy pour TOUTE parcelle sous SUP
    # (régression RUN11-VS-RUN10 §8 : 73 609 parcelles, communes des Hauts vidées).
    # VITESSE (fix/sup-source) — `sl.commune = p.commune` en MIROIR de _greve_certaine_m2
    # (faisabilite/db.py). Le ST_ClipByBox2D était déjà là, mais SANS scope commune : la SUP `el10`
    # (~1 055 km², 24 copies — une par commune) a une bbox insulaire, donc les ~48 lignes SUP qui la
    # portent passaient toutes le pré-filtre GiST et subissaient le ST_Intersects fin par parcelle.
    # Scoper à la commune ramène ce nombre à ~5 (les 417 SUP portent TOUTES une commune, 0 NULL) →
    # ×2,9 sur les parcelles sous SUP. RÉSULTAT IDENTIQUE au m² (écart max 1,2e-10 m² sur 55 golden
    # + 500 parcelles sous SUP) : une parcelle appartient à UNE commune, et sa SUP y est rattachée.
    # ORACLE-FIX-1 (Lot B) — EXCLURE la SUP `pm1` (enveloppe PPR). Constat ORACLE-1 sur S10
    # (97409000AB0018) : §5 « PPR zone BLEUE — constructible SOUS PRESCRIPTIONS » vs §10 « Zone
    # d'implantation 0 m² / Exclusion ». La cause n'est PAS le PPR lui-même (lu correctement en
    # SOFT_FLAG par la cascade et par le bloc PPR ci-dessus, qui n'exclut QUE subtype='INTERDICTION'
    # = rouge), mais ce bloc SUP qui soustrayait ÉGALEMENT la SUP `pm1` = « Enveloppe des zonages
    # réglementaires » du PPR (311 lignes île). L'enveloppe couvre bleue ET rouge indistinctement →
    # une parcelle en zone bleue (constructible) voyait toute son emprise exclue. C'était une DEUXIÈME
    # lecture, incohérente, du même PPR. On ne la lit plus qu'une fois (bloc PPR → INTERDICTION). Les
    # autres SUP (ac1/ac2/ac3/ac4 monuments·sites, el10, pm2/pm3) restent des exclusions réelles.
    sup_gj = session.execute(text(
        "SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(ST_Intersection("
        "  ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), p.geom_2975), 4326), 3)) "
        "FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind = 'sup' "
        "AND sl.subtype <> 'pm1' "          # enveloppe PPR : lue par le bloc PPR (rouge), pas ici
        "AND sl.commune = p.commune "
        "AND ST_Intersects(sl.geom_2975, p.geom_2975) GROUP BY p.geom_2975"
    ), {"pid": pid}).first()
    _sup_present = bool(sup_gj and sup_gj[0] and json.loads(sup_gj[0]).get("coordinates"))
    if _sup_present:
        exclusions.append(Exclusion(id="sup", ruleId="SUP", type="sup",
                                    label="Servitude d'utilité publique déduite",
                                    geometry=json.loads(sup_gj[0]), source=sup_src))
    applicable.append(ApplicableRule(
        id="SUP", label="Servitudes d'utilité publique", category="exclusion",
        integrationStatus="integrated" if _sup_present else "not_integrated",
        detail=("assiette SUP déduite de la zone d'implantation" if _sup_present
                else "Aucune SUP sur la parcelle"), source=sup_src))

    # --- citation PLU retraits.voie : couvre-t-elle « voies ET emprises publiques » / voies privées ?
    emprises_publiques = voies_privees = False
    voie_article = voie_citation = ""
    if work_zone and not blocking:
        emprises_publiques, voies_privees, voie_article, voie_citation = _voie_citation_flags(commune, work_zone)
        racc["citation_voie"] = {"emprises_publiques": emprises_publiques, "voies_privees": voies_privees,
                                 "article": voie_article, "citation": voie_citation}

    # --- classification des limites (SERVIE) --------------------------------
    setbacks: list[Setback] = []
    if not blocking:  # n'y toucher que si le PLU est complet et unique
        lim = classify_parcel_limits(session, pid, emprises_publiques=emprises_publiques,
                                     voies_privees=voies_privees,
                                     sub_geom_wkt=mz_sub_geom_wkt,
                                     extra_neighbors_wkt=mz_extra_neighbors or None)
        mill = _bdtopo_millesime(session)
        bdtopo_src = RegulatorySource(
            document="BD TOPO® — troncon_de_route (voirie) + cadastre",
            versionDate=mill, provider=f"LABUSE — adjacence cadastre + BD TOPO {mill}")
        # arête sur domaine public non cadastré, classée voie par la citation « voies et emprises publiques »
        empub_src = RegulatorySource(
            document=f"Domaine public non cadastré — PLU {commune} {work_zone} {voie_article}".strip(),
            article=voie_article or None,
            provider=f"LABUSE — cadastre (non cadastré = domaine public) + citation PLU {voie_article}".strip())
        # arête collée à une parcelle de voie privée cadastrée (E2), servie par citation « voies privées »
        voiepriv_src = RegulatorySource(
            document=f"Parcelle de voie privée (cadastre) — PLU {commune} {work_zone} {voie_article}".strip(),
            article=voie_article or None,
            provider=f"LABUSE — parcelle de voie privée (cadastre) + citation PLU {voie_article}".strip())

        def _src_for(e):
            if e.type == "voie" and e.source_kind == "emprise_publique":
                return empub_src
            if e.type == "voie" and e.source_kind == "voie_privee":
                return voiepriv_src
            return bdtopo_src

        def _ruleid_for(e):
            if e.type in ("side", "rear"):
                return "limite-sep"
            if e.source_kind == "emprise_publique":
                return "limite-emprise-publique"
            if e.source_kind == "voie_privee":
                return "limite-voie-privee"
            return "limite-voie"

        def _setbacks_for(edges, include_voie):
            for i, e in enumerate(edges):
                if e.type in ("side", "rear"):
                    setbacks.append(Setback(id=f"lim-{i}", ruleId="limite-sep", type=e.type,
                                            geometry=geojson_from_shape(to_wgs(e.geom)),
                                            setbackM=recul_sep, source=bdtopo_src))
                elif include_voie and e.type == "voie":
                    setbacks.append(Setback(id=f"lim-{i}", ruleId=_ruleid_for(e), type="road",
                                            geometry=geojson_from_shape(to_wgs(e.geom)),
                                            setbackM=recul_voie, source=_src_for(e)))

        def _rules_present(edges, include_voie):
            """Déclare une règle applicable par (type, source) réellement servi (V5f / validate)."""
            if recul_sep is not None and any(e.type in ("side", "rear") for e in edges):
                applicable.append(ApplicableRule(id="limite-sep", label="Limites séparatives",
                    category="setback", integrationStatus="integrated",
                    detail=f"Recul séparatif {recul_sep:g} m — PLU {commune} {work_zone} (validé)", source=bdtopo_src))
            if include_voie and any(e.type == "voie" and e.source_kind == "bdtopo" for e in edges):
                applicable.append(ApplicableRule(id="limite-voie", label="Recul voie", category="setback",
                    integrationStatus="integrated",
                    detail=f"Recul voie {recul_voie:g} m — PLU {commune} {work_zone} (validé)", source=bdtopo_src))
            if include_voie and any(e.type == "voie" and e.source_kind == "emprise_publique" for e in edges):
                applicable.append(ApplicableRule(id="limite-emprise-publique", label="Recul voie (emprise publique)",
                    category="setback", integrationStatus="integrated",
                    detail=f"Recul voie {recul_voie:g} m appliqué au domaine public — « voies et emprises "
                           f"publiques », PLU {commune} {work_zone} {voie_article}".strip(), source=empub_src))
                sources.append(empub_src)
            if include_voie and any(e.type == "voie" and e.source_kind == "voie_privee" for e in edges):
                applicable.append(ApplicableRule(id="limite-voie-privee", label="Recul voie (voie privée)",
                    category="setback", integrationStatus="integrated",
                    detail=f"Recul voie {recul_voie:g} m appliqué à la voie privée cadastrée — « voies "
                           f"privées », PLU {commune} {work_zone} {voie_article}".strip(), source=voiepriv_src))
                sources.append(voiepriv_src)

        if lim is None:
            blocking.append("géométrie de parcelle indisponible")
        else:
            n_voie = sum(1 for e in lim.edges if e.type == "voie")
            n_sep = sum(1 for e in lim.edges if e.type in ("side", "rear"))
            racc["classification"] = {"provider": bdtopo_src.provider, "voie": n_voie, "side":
                                      sum(1 for e in lim.edges if e.type == "side"),
                                      "rear": sum(1 for e in lim.edges if e.type == "rear"),
                                      "emprise_publique": sum(1 for e in lim.edges
                                                              if e.type == "voie" and e.source_kind == "emprise_publique"),
                                      "voie_privee": sum(1 for e in lim.edges
                                                         if e.type == "voie" and e.source_kind == "voie_privee"),
                                      "aretes_residuelles_rattachees": lim.residual_attached,
                                      "non_classees": lim.non_classees}
            if lim.residual_attached:
                racc["classification"]["note_residuelles"] = (
                    f"{lim.residual_attached} arête(s) résiduelle(s) rattachée(s) "
                    "(artefact de numérisation : segments tous < 1 m, run < 2 % du périmètre)")
            if any(e.source_kind == "voie_privee" for e in lim.edges):
                racc["enclave"] = "E2 (voie privée cadastrée servie — citation « voies privées »)"
            # ravine / littoral longé par une arête emprise publique → recul ravine non chiffré (not_integrated)
            if any(e.source_kind == "emprise_publique" for e in lim.edges) and _touche_ravine(session, pid):
                applicable.append(ApplicableRule(id="ravine", label="Recul ravine / littoral", category="other",
                    integrationStatus="not_integrated",
                    detail="Recul propre aux ravines / au littoral non chiffré dans LABUSE — arête traitée "
                           "comme emprise publique", source=RegulatorySource(
                               document="Géorisques / BD TOPO — ravine / trait de côte", provider="LABUSE")))
            if lim.non_classees:
                blocking.append("Limites de la parcelle non qualifiées (voie / limite séparative) — "
                                + " ; ".join(lim.non_classees))
            elif not lim.has_voie:
                # ENCLAVE. E2 (voie privée cadastrée détectée) sans citation « voies privées » → bloc
                # honnête : le recul sur la voie privée d'accès n'est pas réglé (GABARIT-3/4 conservé,
                # même verdict que si l'arête d'accès était captée en « non qualifiée »). E1 (aucune voie
                # privée détectée) → servie en séparatives seules, recul voie « sans objet ».
                if lim.private_road and not voies_privees:
                    blocking.append("parcelle sans façade sur voie : desservie par une voie privée "
                                    "cadastrée — le règlement ne précise pas le recul sur voie privée")
                    racc["enclave"] = "E2 (voie privée cadastrée — citation absente, bloc)"
                elif recul_sep is None:
                    blocking.append("recul sur limite séparative non réglementé / non validé")
                else:
                    sources.append(bdtopo_src)
                    _rules_present(lim.edges, include_voie=False)
                    applicable.append(ApplicableRule(
                        id="limite-voie-sansobjet", label="Recul voie", category="setback",
                        integrationStatus="integrated",
                        detail="parcelle sans façade sur voie — recul voie sans objet", source=bdtopo_src))
                    _setbacks_for(lim.edges, include_voie=False)
                    racc["enclave"] = "E1 (séparatives seules)"
            else:
                if recul_voie is None:
                    blocking.append("recul sur voie non réglementé / non validé")
                if n_sep and recul_sep is None:
                    blocking.append("recul sur limite séparative non réglementé / non validé")
                if not blocking:
                    sources.append(bdtopo_src)
                    _rules_present(lim.edges, include_voie=True)
                    _setbacks_for(lim.edges, include_voie=True)

    inp = GabaritInput(
        parcel=ParcelInput(id=idu, geometry=geom, areaM2=round(surface, 1) if surface else None,
                           source=cadastre_src),
        setbacks=setbacks,
        maxFootprint=max_footprint,
        maxHeight=max_height,
        exclusions=exclusions,
        applicableRules=applicable,
        sources=sources,
    )
    return BuildResult(input=inp, blocking=blocking, raccordement=racc)
