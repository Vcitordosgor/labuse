"""Raccordement UNIQUE des vraies données → `GabaritInput` (CDC §11).

C'est le SEUL endroit où le réel entre. `compute_gabarit` reste pur : il ne sait pas
si l'entrée vient d'ici ou d'une fixture. Correspondances (CDC §11) :
  cadastre → parcel · PLU (zonage.py) → recul (setbackM)/maxFootprint/maxHeight ·
  classification limites (limites.py = adjacence cadastre + BD TOPO) → type de chaque
  setback (road/side/rear) + géométrie · PPR (verdict du run servi + spatial_layers) →
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
from ._geom import geojson_from_shape, shape_from_geojson, to_metric, to_wgs
from .contract import (
    ApplicableRule,
    Exclusion,
    GabaritInput,
    MaxFootprint,
    MaxHeight,
    ParcelInput,
    ReculSepFormule,
    RegulatorySource,
    Setback,
)
from .limites import classify_parcel_limits

CADASTRE_PROVIDER = "DGFiP — cadastre (PCI)"
PLU_PROVIDER = "LABUSE — règlement PLU validé"
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


def _fraction_hauteur_formule(formule: Optional[str]) -> Optional[float]:
    """FAISA-REGLES-1 (D-024) — lit la FRACTION DE HAUTEUR d'une formule de recul séparatif (« L ≥ h/2 »,
    « au tiers de la différence d'altitude h : h/3 »…) : rend 0,5 pour h/2, 1/3 pour h/3, None si la
    formule ne lie pas le recul à la hauteur. On n'INVENTE rien : sans terme h/n, on renvoie None (le
    plancher sourcé s'applique seul)."""
    if not formule:
        return None
    m = re.search(r"\bh\s*/\s*([234])\b", str(formule).lower())
    return (1.0 / int(m.group(1))) if m else None


# ── MOTEUR-VERITE-FIX-2 LOT A — implantation en limite : décision PURE et STRICTE ──────────────
# RÈGLE (gravée par tests/test_moteur_verite_fix2.py) : une capacité ne peut DÉPASSER le niveau
# prudent que si TOUTES les conditions de l'article qui l'ouvre sont APPLIQUÉES par le moteur.
# Un seul jeton non modélisé, mal formé ou disjonctif → l'ouverture FERME (retrait prudent),
# la mention « capacité supérieure possible, à vérifier » reste ; le verdict reste constructible.

_JETON_FLAGS = ("une_seule_limite", "deux_limites_max")
_JETON_NUMS = ("largeur_terrain_max", "surface_terrain_max", "bascule_surface",
               "profondeur_bande", "lineaire_max_pct")
#: forme STRICTE d'un jeton numérique : « nom:12 », « nom:12,5 m », « nom:400 m² » — RIEN d'autre.
#: (FIX-2 LOT A : « largeur_terrain_max:14 m (≤ 14 m : deux limites…) » était lu 141 414 m — la
#: concaténation de tous les chiffres — et ouvrait deux limites à toute largeur.)
_JETON_NUM_RX = re.compile(r"^(?P<nom>[a-z_]+)\s*:\s*(?P<val>\d+(?:[.,]\d+)?)\s*(?:m²|m2|m)?\s*$")


def jeton_num_strict(tok: str):
    """(nom, valeur) si le jeton est de forme stricte, sinon None (→ FERME l'ouverture)."""
    m = _JETON_NUM_RX.match(tok.strip())
    if not m or m.group("nom") not in _JETON_NUMS:
        return None
    return m.group("nom"), float(m.group("val").replace(",", "."))


#: MOTEUR-VERITE-FIX-3 LOT 1 — LISTE BLANCHE. Tout est fermé par défaut : une ouverture
#: chiffrée n'existe que si la feuille porte la déclaration explicite ET l'état de CHACUNE des
#: huit conditions possibles de l'article (absente_du_texte = l'article ne la pose pas ;
#: mesuree = le moteur la mesure sur la parcelle). Sans cela : retrait prudent, verdict
#: « constructible, capacité supérieure possible, à vérifier ». Le relecteur contrôle la liste
#: EN ENTIER (docs/audit-2026-11/moteur-verite-fix-1/LISTE-BLANCHE.md).
DECLARATION_LISTE_BLANCHE = "toutes les conditions de l'article sont appliquées"
CONDITIONS_LISTE_BLANCHE = (
    "nombre_de_limites", "lineaire_ou_profondeur_en_limite", "bande_depuis_voie",
    "hauteur_en_limite", "angle", "patio", "rupture_mitoyennete", "affectation_graphique")


def liste_blanche_ok(imp: Optional[dict]) -> bool:
    """La feuille porte-t-elle une déclaration de liste blanche COMPLÈTE ?"""
    lb = (imp or {}).get("liste_blanche") or {}
    if str(lb.get("declaration") or "").strip() != DECLARATION_LISTE_BLANCHE:
        return False
    conds = lb.get("conditions") or {}
    return all(str(conds.get(k) or "") in ("absente_du_texte", "mesuree")
               for k in CONDITIONS_LISTE_BLANCHE)


def analyser_condition_implantation(imp: Optional[dict], largeur_m, surface_m2) -> dict:
    """Décision d'implantation d'UN côté — {ouvre: bool, zero: 'toutes'|n|0, bande_m,
    lineaire_pct, detail, mention}. `largeur_m` : largeur mesurée du terrain (ou None),
    `surface_m2` : surface cadastrale (ou None). PURE (aucune géométrie ici).

    FIX-2 LOT A : TOUT ou RIEN — si un jeton de `condition_modelable` n'est pas STRICTEMENT
    modélisé (flag exact ou numérique bien formé), le côté N'OUVRE PAS (zero 0) et porte la
    mention. Fini l'« ouverture + mention » qui chiffrait sans appliquer la condition."""
    d = {"ouvre": False, "zero": 0, "bande_m": None, "lineaire_pct": None,
         "detail": None, "mention": None}
    if imp is None or imp.get("mode") in (None, "retrait_obligatoire"):
        if imp is not None and imp.get("mode") == "retrait_obligatoire" and imp.get("condition_texte"):
            d["mention"] = str(imp["condition_texte"]).strip()[:200]
        return d
    mode = imp["mode"]
    art = (imp.get("article") or "").strip()
    cm = (imp.get("condition_modelable") or "").strip()
    cond_txt = (imp.get("condition_texte") or "conditions du règlement").strip()
    # FIX-3 LOT 1 — LISTE BLANCHE : sans déclaration complète, AUCUNE ouverture chiffrée
    # (même « limite_ou_retrait sans condition » : une condition peut vivre dans le seul texte).
    if not liste_blanche_ok(imp):
        d["mention"] = cond_txt[:200]
        return d
    if mode in ("limite_ou_retrait", "limite_imposee") and not cm:
        lib = ("implantation en limite admise sans condition" if mode == "limite_ou_retrait"
               else "implantation en limite imposée par le règlement")
        d.update(ouvre=True, zero="toutes", detail=(f"{lib} — {art}" if art else lib))
        return d
    jetons = [t.strip() for t in cm.split("+") if t.strip()]
    details = []
    porte_largeur = False
    porte_fermee = False
    a_porte = any(t.strip().startswith("largeur_terrain_max:") for t in jetons)
    for tok in jetons:
        if tok in _JETON_FLAGS:
            n = 1 if tok == "une_seule_limite" else 2
            d["zero"] = "toutes" if d["zero"] == "toutes" else max(d["zero"] or 0, n)
            details.append("en limite sur une seule limite" if n == 1 else "en limite sur deux limites au plus")
            continue
        js = jeton_num_strict(tok)
        if js is None:
            # jeton inconnu, « non », disjonctif (« OU ») ou MAL FORMÉ → l'ouverture FERME.
            d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None,
                     detail=None, mention=cond_txt[:200])
            return d
        nom, val = js
        if nom == "largeur_terrain_max":
            # FIX-3 LOT 2 — la largeur est une PORTE mesurée SUR LA VOIE : remplie, elle ACTIVE
            # les jetons de nombre de limites ; non remplie, le côté FERME (règle appliquée,
            # pas une mention) — Sainte-Rose Ud ouvrait « toutes » sous le seuil et une au-delà.
            # En mode imposé, « au moins une » reste imposée au-delà du seuil.
            if largeur_m is None:
                d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None,
                         mention=(cond_txt[:160] + " (largeur sur voie non mesurable)"))
                return d
            if largeur_m <= val:
                porte_largeur = True
                details.append(f"largeur sur voie {largeur_m:g} m ≤ {val:g} m")
            elif mode == "limite_imposee":
                porte_largeur = True
                d["zero"] = "toutes" if d["zero"] == "toutes" else max(d["zero"] or 0, 1)
                details.append(f"largeur {largeur_m:g} m > {val:g} m — au moins une limite imposée")
            else:
                porte_fermee = True
        elif nom == "surface_terrain_max":
            if surface_m2 and float(surface_m2) <= val:
                d["zero"] = "toutes"
                details.append(f"surface du terrain {float(surface_m2):g} m² ≤ {val:g} m²")
        elif nom == "bascule_surface":
            if not surface_m2:
                d.update(ouvre=False, zero=0, bande_m=None, lineaire_pct=None, detail=None,
                         mention=(cond_txt[:160] + " (surface non connue)"))
                return d
            n = 2 if float(surface_m2) <= val else 1
            d["zero"] = "toutes" if d["zero"] == "toutes" else max(d["zero"] or 0, n)
            details.append(f"{n} limite(s) admise(s) (surface {float(surface_m2):g} m² "
                           f"{'≤' if n == 2 else '>'} {val:g} m²)")
        elif nom == "profondeur_bande":
            d["bande_m"] = val
            details.append(f"dans une bande de {val:g} m depuis la voie")
        elif nom == "lineaire_max_pct":
            d["lineaire_pct"] = val
            details.append(f"sur au plus {val:g} % du linéaire")
    if porte_fermee:
        # porte de largeur évaluée NON remplie → le côté ferme, règle appliquée (pas de mention)
        return {"ouvre": False, "zero": 0, "bande_m": None, "lineaire_pct": None,
                "detail": None, "mention": None}
    if a_porte and porte_largeur and not d["zero"]:
        d["zero"] = "toutes"          # porte seule, sans jeton de nombre : le texte n'en fixe pas
    if d["bande_m"] and not d["zero"]:
        d["zero"] = "toutes"
    d["ouvre"] = bool(d["zero"])
    if details and d["ouvre"]:
        d["detail"] = ("; ".join(details) + (f" — {art}" if art else ""))[:220]
    return d


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
        # CONTENANCE-1 (Lot C) : surface de la parcelle pour le PLAFOND d'emprise (CES × surface) =
        # contenance si présente, sinon dessin. La ZONE d'implantation (zone_m.area) reste la forme
        # géométrique réelle (C2) ; son aire est ramenée à l'échelle contenance là où elle alimente
        # une capacité client (faisabilite/db.py, facteur C3).
        "SELECT id, commune, COALESCE(contenance_m2, ST_Area(geom_2975)) AS surface_m2, "
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
    recul_formule_obj: Optional[ReculSepFormule] = None   # MOTEUR-VERITE-FIX-1 (LOT 1)
    imp_lat: Optional[dict] = None                        # MOTEUR-VERITE-FIX-1 (LOT 2)
    imp_fond: Optional[dict] = None
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
            # MOTEUR-VERITE-FIX-1 (LOT 1) — recul séparatif « L ≥ H/n (min X m) » : H est la hauteur
            # à l'ÉGOUT du bâtiment ENVISAGÉ, pas le faîtage maximal de la zone (la régression D-024
            # du 31/10 insétait h×frac au faîtage sur toutes les limites : 19 permis réels couverts en
            # octobre ne l'étaient plus — VERITE-TERRAIN-3, erreur V1 étage 2, témoin AO1919
            # 564 m² → 73 m²). Le builder transmet désormais la FORMULE au moteur (reculSepFormule) ;
            # engine.compute_gabarit évalue chaque nombre de niveaux admis (égout envisagé = n × étage)
            # et RETIENT le scénario au plancher maximal. Les setbacks d'entrée portent le MINIMUM
            # sourcé ; sans hauteur validée, la formule reste « non intégrée » (on ne devine pas H).
            recul_sep_formule = None
            recul_formule_obj = None
            _frac_h = _fraction_hauteur_formule(getattr(zr, "recul_limites_formule", None))
            _h_ref_type = getattr(zr, "h_reference", None)
            if (_frac_h is not None and recul_sep is not None and recul_sep > 0
                    and _h_ref_type != "egout"):
                # MOTEUR-VERITE-FIX-3 LOT 1 — le texte ne fixe PAS l'égout comme référence
                # (hauteur totale de façade, prospect altimétrique point à point, ou non lu) :
                # le scénario niveau-par-niveau à l'égout ne s'applique PAS. Référence PRUDENTE =
                # faîtage de la zone (le recul le plus grand plausible — capacité ≤ main).
                _h_prud = haut if haut is not None else egout
                if _h_prud is not None:
                    _rec_p = round(max(float(recul_sep), float(_h_prud) * _frac_h), 1)
                    if _rec_p > recul_sep:
                        recul_sep = _rec_p
                    recul_sep_formule = (
                        f"recul séparatif = max(min, H×{_frac_h:.3g}) — référence PRUDENTE "
                        f"H = faîtage {_h_prud:g} m (le texte ne fixe pas l'égout : "
                        f"{_h_ref_type or 'référence non lue à l''article'}) → {recul_sep:g} m")
                    racc.setdefault("regles_non_integrees", []).append(
                        "retrait relatif : référence de hauteur non « égout » — scénario "
                        "niveau-par-niveau NON appliqué (référence prudente faîtage)")
                else:
                    racc.setdefault("regles_non_integrees", []).append(
                        "recul séparatif lié à la hauteur non chiffrable : hauteur de zone non validée")
            elif _frac_h is not None and recul_sep is not None and recul_sep > 0:
                from ..faisabilite.engine import Hypotheses
                _etage = float(Hypotheses.charger(commune).etage_m)
                _nmax = None
                if isinstance(getattr(zr, "niveaux_max", None), int):
                    _nmax = int(zr.niveaux_max) + 1
                elif egout is not None:
                    _nmax = max(1, int(egout // _etage))
                elif haut is not None:
                    _nmax = max(1, int((haut - _etage) // _etage))
                if _nmax is not None:
                    recul_formule_obj = ReculSepFormule(
                        fraction=_frac_h, minimumM=float(recul_sep), etageM=_etage,
                        niveauxMax=_nmax,
                        formule=str(getattr(zr, "recul_limites_formule", "") or ""))
                    recul_sep_formule = (
                        f"recul séparatif = max({recul_sep:g} m, H×{_frac_h:.3g}), H = égout du "
                        f"bâtiment envisagé — scénario retenu par le moteur niveau par niveau "
                        f"(R+0…R+{_nmax - 1})")
                else:
                    racc.setdefault("regles_non_integrees", []).append(
                        "recul séparatif lié à la hauteur (ex. h/2) non chiffrable : hauteur de zone non validée")
            racc["plu"] = {"emprise_pct": emp, "hauteur_faitage_m": haut, "hauteur_egout_m": egout,
                           "recul_voie_m": recul_voie, "recul_sep_m": recul_sep, "source": plu_zone_src.document}
            if recul_sep_formule:
                racc["plu"]["recul_sep_formule"] = recul_sep_formule
            # MOTEUR-VERITE-FIX-1 (LOT 2) — modes d'implantation par côté (calibrés, validés-only).
            imp_lat = getattr(zr, "implantation_laterales", None)
            imp_fond = getattr(zr, "implantation_fond", None)
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
                elif egout is not None and getattr(zr, "hauteur_estimee", False):
                    # RECETTE-PROD-1 (A7) — la zone est calibrée pour l'enveloppe (emprise/reculs) mais sa
                    # HAUTEUR est une table graphique par secteur (non réductible à une valeur unique). La
                    # valeur de repli est SERVIE et UTILISÉE (volume 3D indicatif), mais marquée ESTIMÉE
                    # (`estimee=True`) → l'écran et les PDF l'étiquettent « Estimé », jamais comme la valeur
                    # validée du règlement. Le gabarit reste calculable, sans le faux « PLU non calibré ».
                    art = _feuille_article(commune, work_zone, "hauteur", "egout")
                    cit = _feuille_citation(commune, work_zone, "hauteur", "egout")
                    est_src = RegulatorySource(document=f"PLU — {commune}", zone=work_zone, article=art or None,
                                               provider="LABUSE — hauteur estimée (table graphique par secteur)")
                    max_height = MaxHeight(ruleId=f"{work_zone}-hauteur", meters=egout,
                                           status="integrated", basis="egout", estimee=True, source=est_src)
                    applicable.append(ApplicableRule(
                        id=f"{work_zone}-hauteur", label="Hauteur réglementaire — à l'égout (Estimé)",
                        category="maxHeight", integrationStatus="integrated",
                        detail=(f"{egout:g} m à l'égout · Estimé — table graphique par secteur"
                                + (f" ({cit})" if cit else "")),
                        source=est_src))
                    racc.setdefault("hauteur_egout", {"m": egout, "article": art, "estimee": True})
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
                # DOCS-COHERENCE-1 (A6) — stationnement & pleine terre CHIFFRÉS depuis la MÊME calibration
                # PLU que le Dossier §4 et l'Étude §2 (regles_zone), avec la mention « non intégrée au
                # gabarit » (le gabarit ne les modélise pas) et l'article cité. Par logement seulement
                # (barème par typologie non chiffré ici) : repli « Règle connue, non chiffrée ».
                _rz = regles_zone(commune, work_zone) or {}
                _st = (_rz.get("stationnement") or {}).get("par_logement") or {}
                if _st.get("places") is not None and _st.get("statut") == "valide":
                    _np, _arts = _st["places"], _st.get("article")
                    _stat_detail = (f"{_np:g} place{'s' if _np >= 2 else ''} / logement — non intégrée au gabarit"
                                    + (f" (art. {_arts})" if _arts else ""))
                    _stat_src = RegulatorySource(document=f"PLU — {commune}", zone=work_zone,
                                                 article=_arts or None, provider=PLU_PROVIDER)
                else:
                    _stat_detail, _stat_src = "Règle connue, non chiffrée", plu_zone_src
                applicable.append(ApplicableRule(id="STAT", label="Stationnement", category="other",
                                                 integrationStatus="not_integrated",
                                                 detail=_stat_detail, source=_stat_src))
                _pt = (_rz.get("pleine_terre") or {}).get("pct") or {}
                if _pt.get("pct") is not None and _pt.get("statut") == "valide":
                    _npt, _artp = _pt["pct"], _pt.get("article")
                    _esp_detail = (f"{_npt:g} % de pleine terre — non intégrée au gabarit"
                                   + (f" (art. {_artp})" if _artp else ""))
                    _esp_src = RegulatorySource(document=f"PLU — {commune}", zone=work_zone,
                                                article=_artp or None, provider=PLU_PROVIDER)
                else:
                    _esp_detail, _esp_src = "Règle connue, non chiffrée", plu_zone_src
                applicable.append(ApplicableRule(id="ESP", label="Espaces libres", category="other",
                                                 integrationStatus="not_integrated",
                                                 detail=_esp_detail, source=_esp_src))

    # --- risques : PPR zone rouge (réglementaire, per-parcelle) ---------------
    # GABARIT-3D-3 (LOT 3) — le verdict PPR est lu dans le RUN SERVI (`served_cascade_lines` →
    # `dryrun_cascade_results` du run épinglé, dédupliqué + arbitré), comme le reste de l'app, et NON
    # plus dans la table figée `cascade_results` (rail legacy mort). La part ROUGE exclue, elle, reste
    # déterminée EN DIRECT par la géométrie/classification unique `labuse_ppr_couleur` (ci-dessous).
    from ..api.served_cascade import served_cascade_lines
    _risques = [l for l in served_cascade_lines(session, idu) if l.get("layer_name") == "risques"]
    _risques.sort(key=lambda l: l.get("result") == "HARD_EXCLUDE", reverse=True)
    ppr = _risques[0] if _risques else None
    ppr_src = RegulatorySource(document="PPR — zonage réglementaire", provider=PPR_PROVIDER)
    exclusions: list[Exclusion] = []
    # PPR-UNIQUE-1 — la part ROUGE exclue est déterminée EN DIRECT par la classification UNIQUE
    # `labuse_ppr_couleur` (rouge ∪ code non classé), pas par le run de cascade figé : une parcelle
    # en zone `i` (Saint-Philippe, non reconnue par l'ancien `subtype='INTERDICTION'`) voit quand
    # même son rouge exclu. GEOMETRIE-1 lot A — ST_ClipByBox2D avant l'intersection fine (mégapolygones
    # PPR ~320 k sommets) ; résultat identique (parcelle ⊆ sa bbox). ST_MakeValid par sécurité.
    gj = session.execute(text(
        "SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(ST_Intersection("
        "  ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), p.geom_2975), 4326), 3)) "
        "FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind='ppr' "
        "AND labuse_ppr_couleur(sl.subtype, sl.attrs) <> 'bleu' AND ST_Intersects(sl.geom_2975, p.geom_2975) "
        "GROUP BY p.geom_2975"
    ), {"pid": pid}).first()
    ppr_rouge = False
    if gj and gj[0]:
        geo = json.loads(gj[0])
        if geo.get("coordinates"):
            ppr_rouge = True
            exclusions.append(Exclusion(id="ppr-rouge", ruleId="PPR", type="ppr_rouge",
                                        label="PPR zone rouge exclue", geometry=geo, source=ppr_src))
    racc["ppr"] = {"result": ppr.get("result") if ppr else None,
                   "detail": ppr.get("detail") if ppr else None, "rouge": ppr_rouge}
    sources.append(ppr_src)
    applicable.append(ApplicableRule(
        id="PPR", label="PPR — analyse", category="exclusion",
        integrationStatus="integrated" if ppr_rouge else "not_integrated",
        detail=((ppr["detail"] if ppr else None)
                or ("Zone rouge PPR exclue de l'assiette (classification unique PPR-UNIQUE-1)."
                    if ppr_rouge else "Aucune zone rouge PPR sur la parcelle")), source=ppr_src))

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
    #
    # PPR-PARTIEL-A (règle de Vic, 06/10/2026) — REMPLACE le « 0 par prudence » pré-merge. L'enveloppe
    # `pm1` (rouge + bleu indistinctement) n'est JAMAIS re-soustraite : le ROUGE SEUL est déjà découpé
    # ci-dessus (exclusion `ppr-rouge`, :348-365), et le BLEU reste constructible sous prescriptions
    # comme partout ailleurs dans l'app. On supprime donc la sur-déduction `OR EXISTS(... INTERDICTION)`
    # qui, dès qu'une parcelle touchait du rouge, retranchait l'enveloppe entière → 3 888 parcelles U/AU
    # servies à 0 (588 ha, PPR-PARTIEL-1). Le gabarit vaut désormais > 0 sur la partie hors rouge ; la
    # cascade lit la MÊME partie hors rouge (faisabilite : SOFT_FLAG « constructible sur la partie hors
    # zone rouge », plus HARD_EXCLUDE) — une seule géométrie, deux lecteurs, plus d'incohérence. Les
    # garde-fous (tenant / surface / accès voie / emprise) décident si ce > 0 est servi ou ramené à 0
    # AVEC MOTIF (jamais un 0 muet). Les autres SUP (ac1..el10, pm2/pm3) restent des exclusions réelles.
    # MOTEUR-VERITE-FIX-1 (LOT 3, V8) — la SUP `ac2` (sites inscrits/classés) est un régime d'AVIS
    # de l'architecte des Bâtiments de France, PAS une interdiction de construire : elle retirait
    # 83 % d'une parcelle réelle (97413000CY1293, « LA POINTE AU SEL ») alors qu'on y construit sous
    # avis. Elle sort de la déduction ; une ALERTE la signale (règle vérifiée, surface intacte).
    sup_gj = session.execute(text(
        "SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(ST_Intersection("
        "  ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), p.geom_2975), 4326), 3)) "
        "FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind = 'sup' "
        "AND sl.subtype <> 'pm1' "          # enveloppe PPR : JAMAIS re-soustraite (rouge seul déjà déduit)
        "AND sl.subtype <> 'ac2' "          # LOT 3 (V8) : avis ABF, jamais une surface retirée
        "AND sl.commune = p.commune "
        "AND ST_Intersects(sl.geom_2975, p.geom_2975) GROUP BY p.geom_2975"
    ), {"pid": pid}).first()
    _sup_present = bool(sup_gj and sup_gj[0] and json.loads(sup_gj[0]).get("coordinates"))
    if _sup_present:
        exclusions.append(Exclusion(id="sup", ruleId="SUP", type="sup",
                                    label="Servitude d'utilité publique déduite",
                                    geometry=json.loads(sup_gj[0]), source=sup_src))
    _ac2 = session.execute(text(
        "SELECT COALESCE(sl.attrs->>'libelle', sl.name) FROM spatial_layers sl, parcels p "
        "WHERE p.id = :pid AND sl.kind = 'sup' AND sl.subtype = 'ac2' AND sl.commune = p.commune "
        "AND ST_Intersects(sl.geom_2975, p.geom_2975) LIMIT 1"), {"pid": pid}).first()
    _ac2 = _ac2[0] if (_ac2 and _ac2[0]) else None     # (None,) des bases de test = absente
    if _ac2:
        applicable.append(ApplicableRule(
            id="sup-ac2", label="Site protégé (AC2)", category="exclusion",
            integrationStatus="integrated",
            detail=(f"Servitude AC2 « {str(_ac2).strip()} » : avis de l'architecte des "
                    "Bâtiments de France requis — aucune surface retirée (régime d'avis, pas une "
                    "interdiction)."), source=sup_src))
        racc.setdefault("alertes", []).append("AC2 — avis ABF requis (aucune surface retirée)")
    # RECETTE-OUTILS-2 (R17) — les SUP sont TOUJOURS contrôlées (la requête ci-dessus tranche présence
    # vs absence) : une absence VÉRIFIÉE est « intégrée » (vérifiée), pas « non modélisée ». Avant, le
    # PDF/outil marquait les SUP « non modélisées » tout en écrivant « Aucune SUP sur la parcelle » —
    # contradiction. Le statut est donc « integrated » dans les deux cas ; seul le détail diffère.
    applicable.append(ApplicableRule(
        id="SUP", label="Servitudes d'utilité publique", category="exclusion",
        integrationStatus="integrated",
        detail=("assiette SUP déduite de la zone d'implantation" if _sup_present
                else ("SUP présente : AC2 (site protégé — autorisation spéciale/avis ABF, aucune "
                      "surface déduite)" if _ac2 else "Aucune SUP sur la parcelle")), source=sup_src))

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
        # CHASSE-DOCS-FIX-1 (E-17) — le millésime (ex. « BD TOPO® V3 (IGN) … ») est DÉJÀ porté par
        # versionDate ; ne pas le recoller dans provider, sinon « …+ BD TOPO BD TOPO® V3 … » (doublon).
        bdtopo_src = RegulatorySource(
            document="BD TOPO® — voirie + cadastre",
            versionDate=mill, provider="LABUSE — adjacence cadastre + BD TOPO")
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

        # MOTEUR-VERITE-FIX-1 (LOT 2) — IMPLANTATION PAR CÔTÉ. Quand le règlement admet (ou impose)
        # la construction EN LIMITE séparative, le retrait n'est plus appliqué sur ces arêtes :
        #   · limite_ou_retrait / limite_imposee sans condition → recul 0 sur toutes les arêtes du côté ;
        #   · condition MODÉLISABLE : largeur_terrain_max:X (largeur = petit côté du rectangle englobant
        #     minimal, mesurée) → 0 si remplie, retrait sinon (condition évaluée, pas de mention) ;
        #     une_seule_limite / deux_limites_max → recul 0 sur la (les) arête(s) latérale(s) la (les)
        #     plus longue(s) — le choix qui maximise le plancher, admis par la règle ;
        #   · condition NON modélisable → retrait appliqué + MENTION « implantation en limite possible
        #     sous conditions : capacité supérieure possible, à vérifier » (jamais un faux "exigu").
        # Les arêtes posées en limite portent le ruleId `limite-sep-limite` (recul 0 sourcé) : la
        # formule H/n du LOT 1 ne re-insète QUE les arêtes `limite-sep` restantes.
        def _largeur_terrain_m():
            # MOTEUR-VERITE-FIX-3 LOT 2 — la « largeur sur voie » des règlements se mesure SUR LA
            # VOIE (somme des arêtes classées voie), jamais sur le petit côté du rectangle
            # englobant (doublon FIX-2 retiré). Pas d'arête voie qualifiée → None (condition non
            # évaluable → l'ouverture FERME, mention).
            try:
                _l = sum(float(e.geom.length) for e in lim.edges if e.type == "voie")
                return round(_l, 1) if _l > 0 else None
            except Exception:  # noqa: BLE001
                return None

        # MOTEUR-VERITE-FIX-2 LOT A — décision PURE (analyser_condition_implantation) : tout jeton
        # non strictement modélisé FERME l'ouverture (chiffre prudent + mention, verdict conservé).
        _larg = None
        if any("largeur_terrain_max" in str((i or {}).get("condition_modelable") or "")
               for i in (imp_lat, imp_fond)):
            _larg = _largeur_terrain_m()
        dec_lat = analyser_condition_implantation(imp_lat, _larg, surface)
        dec_fond = analyser_condition_implantation(imp_fond, _larg, surface)
        _mentions = [m for m in (dec_lat["mention"], dec_fond["mention"]) if m]
        if _mentions or dec_lat["detail"] or dec_fond["detail"]:
            racc["implantation"] = {"laterales": imp_lat, "fond": imp_fond,
                                    "appliques": [d for d in (dec_lat["detail"], dec_fond["detail"]) if d],
                                    "mentions": _mentions}

        def _setbacks_for(edges, include_voie):
            # FIX-2 LOT A — le fond ne passe à 0 que si SON texte l'admet expressément (feuille
            # fond ouvrante) ; et quand latérales et fond s'ouvrent par le MÊME article indistinct
            # avec un PLAFOND n de limites, le budget n s'applique AU TOTAL (n arêtes les plus
            # longues parmi latérales + fond), jamais n latérales PLUS tout le fond.
            from shapely.ops import unary_union as _uu, substring as _substr
            voie_geoms = [e.geom for e in edges if e.type == "voie"]
            def _band(bm):
                if not bm or not voie_geoms:
                    return None               # pas de voie mesurable → prudence : pas de limite
                return _uu([g.buffer(bm) for g in voie_geoms])
            side_edges = [e for e in edges if e.type == "side"]
            rear_edges = [e for e in edges if e.type == "rear"]
            fond_expres = dec_fond["ouvre"]
            meme_article = (fond_expres and dec_lat["ouvre"]
                            and (imp_lat or {}).get("article") == (imp_fond or {}).get("article"))
            zero_ids = set()
            if dec_lat["ouvre"] and dec_lat["zero"] == "toutes":
                zero_ids |= {id(e) for e in side_edges}
            if fond_expres and dec_fond["zero"] == "toutes" and not (
                    meme_article and isinstance(dec_lat["zero"], int)):
                zero_ids |= {id(e) for e in rear_edges}
            if dec_lat["ouvre"] and isinstance(dec_lat["zero"], int) and dec_lat["zero"] > 0:
                bassin = side_edges + (rear_edges if meme_article else [])
                tri = sorted(bassin, key=lambda e: -float(e.geom.length))
                zero_ids |= {id(e) for e in tri[:dec_lat["zero"]]}
            if (fond_expres and isinstance(dec_fond["zero"], int) and dec_fond["zero"] > 0
                    and not meme_article):
                tri = sorted(rear_edges, key=lambda e: -float(e.geom.length))
                zero_ids |= {id(e) for e in tri[:dec_fond["zero"]]}

            def _emettre(i, e, dec, en_limite):
                # FIX-3 LOT 2 — un CONTOUR FERMÉ (anneau : parcelle enclavée dont tout le périmètre
                # est classé en une seule « arête ») n'est JAMAIS posé en limite : le mettre à 0
                # ouvrait tout le périmètre (Sainte-Suzanne AH0293, L'Étang-Salé AY0554,
                # Saint-Paul AH1368, Le Tampon AW0503 — relecture FIX-3).
                if en_limite and getattr(e.geom, "is_ring", False):
                    en_limite = False
                    racc.setdefault("implantation", {}).setdefault("mentions", []).append(
                        "contour fermé non qualifié (une seule arête sur tout le périmètre) : "
                        "implantation en limite non appliquée — à vérifier")
                if not en_limite:
                    setbacks.append(Setback(id=f"lim-{i}", ruleId="limite-sep", type=e.type,
                                            geometry=geojson_from_shape(to_wgs(e.geom)),
                                            setbackM=recul_sep, source=bdtopo_src))
                    return
                g_lim, g_ret = e.geom, None
                band = _band(dec["bande_m"])
                if dec["bande_m"]:
                    if band is None:
                        g_lim, g_ret = None, e.geom       # bande non mesurable → tout en retrait
                    else:
                        g_lim = e.geom.intersection(band)
                        g_ret = e.geom.difference(band)
                if g_lim is not None and not g_lim.is_empty and dec["lineaire_pct"]:
                    frac = max(0.0, min(1.0, dec["lineaire_pct"] / 100.0))
                    parts_lim, parts_ret = [], []
                    geoms = ([g_lim] if g_lim.geom_type == "LineString"
                             else [g for g in getattr(g_lim, "geoms", []) if g.geom_type == "LineString"])
                    for g in geoms:
                        parts_lim.append(_substr(g, 0.0, frac, normalized=True))
                        parts_ret.append(_substr(g, frac, 1.0, normalized=True))
                    g_lim = _uu([p for p in parts_lim if not p.is_empty]) if parts_lim else None
                    extra = _uu([p for p in parts_ret if not p.is_empty]) if parts_ret else None
                    g_ret = _uu([x for x in (g_ret, extra) if x is not None and not x.is_empty]) \
                        if (g_ret is not None or extra is not None) else None
                for j, (g, rid, dd) in enumerate(((g_lim, "limite-sep-limite", 0.0),
                                                  (g_ret, "limite-sep", recul_sep))):
                    if g is None or g.is_empty or g.length < 0.05:
                        continue
                    setbacks.append(Setback(id=f"lim-{i}-{j}", ruleId=rid, type=e.type,
                                            geometry=geojson_from_shape(to_wgs(g)),
                                            setbackM=dd, source=bdtopo_src))

            for i, e in enumerate(edges):
                if e.type == "side":
                    _emettre(i, e, dec_lat, id(e) in zero_ids)
                elif e.type == "rear":
                    _emettre(i, e, dec_fond if fond_expres else dec_lat, id(e) in zero_ids)
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
            # MOTEUR-VERITE-FIX-1 (LOT 2) — arêtes posées EN LIMITE (recul 0 sourcé au règlement).
            if ((dec_lat["ouvre"] and any(e.type == "side" for e in edges))
                    or (dec_fond["ouvre"] and any(e.type == "rear" for e in edges))):
                _det = " ; ".join(d for d in (dec_lat["detail"], dec_fond["detail"]) if d)
                applicable.append(ApplicableRule(
                    id="limite-sep-limite", label="Limites séparatives — en limite",
                    category="setback", integrationStatus="integrated",
                    detail=f"Recul 0 m — {_det} — PLU {commune} {work_zone} (validé)",
                    source=bdtopo_src))
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
        reculSepFormule=recul_formule_obj,
        maxFootprint=max_footprint,
        maxHeight=max_height,
        exclusions=exclusions,
        applicableRules=applicable,
        sources=sources,
    )
    return BuildResult(input=inp, blocking=blocking, raccordement=racc)


def rescale_zone_contenance(db, idu: str, result) -> None:
    """RECETTE-OUTILS-4 (U4) — ré-échelonne l'aire de la zone d'implantation sur la CONTENANCE cadastrale
    (repère de la Faisabilité), EXACTEMENT comme l'endpoint /outils/gabarit (api/gabarit.py), À APPELER
    juste avant `deduire_bati_de_zone`. Sans ça, les chemins PDF (construire_gabarit, robinet_fiche) qui
    ne passent pas par l'endpoint partaient de l'aire du DESSIN (ex. 176 m²) et affichaient « déduit
    46 m² » au lieu de « 40 » (170 → 130) : la déduction prend pour référence l'aire AVANT, qui doit être
    la même partout. Best-effort (jamais un document cassé)."""
    try:
        z, s = getattr(result, "zoneImplantationM2", None), getattr(result, "surfaceParcelleM2", None)
        if not z or not s:
            return
        from sqlalchemy import text
        dessin = db.execute(text("SELECT ST_Area(geom_2975) FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if dessin and float(dessin) > 0:
            result.zoneImplantationM2 = round(float(z) * float(s) / float(dessin), 1)
    except Exception:  # noqa: BLE001 — l'échelle contenance n'est jamais un bloqueur
        pass


def appliquer_note_a_cheval(db: Session, idu: str, result) -> None:
    """FAISA-REGLES-1 (D-025/D-026) — sur parcelle À CHEVAL, pose `pctPortionZone` et `surfaceNote` depuis
    la SOURCE UNIQUE de zonage (zone_servie.zone_dominante — la même que la fiche §PLU / Comparer) : part
    constructible + contenance + zone constructible servie. Appelée par l'endpoint outil ET le builder PDF,
    pour que l'ÉCRAN et le PDF portent la MÊME mise en garde (le gabarit n'est calculé que sur la part
    constructible). Best-effort : jamais un bloqueur."""
    try:
        racc = getattr(result, "raccordement", None) or {}
        if not (racc.get("zone") or {}).get("a_cheval"):
            return
        from ..faisabilite.zone_servie import zone_dominante
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        zs = zone_dominante(db, pid) if pid else None
        pct = zs.pct_constructible if zs else None
        if pct is None:
            return
        contenance = db.execute(text("SELECT contenance_m2 FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        result.pctPortionZone = round(pct)
        uu = [p["zone"] for p in (zs.parts or []) if p.get("fam") in ("U", "AU")]
        zn = uu[0] if len(uu) == 1 else None
        if contenance:
            portion = round(float(contenance) * pct / 100)   # % NON arrondi × contenance
            result.surfaceNote = (f"Contenance cadastrale {int(contenance)} m² — dont ~{portion} m² "
                                  + (f"en zone {zn}" if zn else "en zone constructible")
                                  + " (parcelle à cheval).")
    except Exception:  # noqa: BLE001 — la note à-cheval n'est jamais un bloqueur
        pass


def appliquer_verdict_constructibilite(db: Session, idu: str, result) -> None:
    """NU5-FIX-1 (A-O1/O2) — LA garde unique de constructibilité du Gabarit, lue via la MÊME
    fonction que la fiche (`faisabilite.potentiel_batir`). Si la parcelle est DÉFINITIVEMENT
    inconstructible (`constructible is False` : zone fermée A/N, AU non ouverte, habitat interdit,
    terrain exigu, PPR rédhibitoire), le Gabarit NE DESSINE AUCUN VOLUME et rend le verdict
    « inconstructible » + le motif — au lieu d'une enveloppe géométrique trompeuse (zone Uem
    « habitat interdit » servait 763 m², R+5) ou d'un « Calcul incomplet » qui suggère une attente
    de donnée (zone N / A / AU fermée / PPR rouge 100 %).

    Ne touche RIEN quand `constructible` vaut True (gabarit servi) ou None (donnée absente →
    « incomplete » reste « incomplete » : on ne transforme pas un trou de donnée en interdiction).
    Les AU à ouverture CONDITIONNELLE servie (conditionnelle_operation…) restent `constructible`
    → leur enveloppe « après ouverture » est conservée (décision CHASSE-FIX-1/C06). Appelée par
    l'endpoint outil ET le builder PDF → écran et PDF portent le MÊME verdict. Best-effort."""
    if result is None:
        return
    try:
        from ..faisabilite.potentiel_batir import potentiel_batir
        pot = potentiel_batir(db, idu)
    except Exception:  # noqa: BLE001 — caches absents → pas de verdict, jamais une 500
        return
    if pot.get("constructible") is not False:
        return
    motif = pot.get("motif") or pot.get("libelle") or "Parcelle inconstructible"
    result.status = "inconstructible"
    result.message = motif
    # aucun volume servi : ni zone d'implantation, ni plafond, ni hauteur, ni 3D, ni retraits.
    for _champ in ("zoneImplantationM2", "zoneImplantationGeoJSON", "retraitsGeoJSON",
                   "exclusionsGeoJSON", "plafondEmpriseM2", "hauteurReglementaireM",
                   "hauteurEgoutM", "batiDeduitM2", "terrainNote"):
        if hasattr(result, _champ):
            setattr(result, _champ, None)
    # on CONSERVE contourGeoJSON + surfaceParcelleM2 + raccordement + batiExistant (contexte carte).


def deduire_bati_de_zone(result) -> None:
    """RECETTE-OUTILS-3 (S7 / S10) — rend la zone d'implantation et le bâti COHÉRENTS et UNIQUES pour
    l'app (2D/3D) et le PDF (p1 schéma, p3 3D). Deux opérations, in place sur un `GabaritResult` servi :

      · S10 — le bâti existant est DÉCOUPÉ au contour cadastral (il débordait : ex. 36 % sur « 36 Rue
        des Jacarandas », bâti voisin / emprise BD TOPO imprécise) — chaque bâtiment garde sa hauteur ;
      · S7 (décision Vic) — la zone d'implantation DÉDUIT l'emprise du bâti conservé (zone − bâti) :
        `zoneImplantationM2` devient la valeur APRÈS déduction, `batiDeduitM2` porte l'emprise retranchée.

    Best-effort : toute erreur géométrique laisse le résultat intact (jamais un document cassé). Aires en
    mètres (CRS métrique 2975), géométries re-servies en WGS84."""
    if result is None or getattr(result, "status", None) != "ok":
        return
    # RECETTE-OUTILS-4 (U4) — « déduit » = surface RÉELLEMENT retirée de la zone AFFICHÉE : la valeur
    # AVANT déduction (le `zoneImplantationM2` servi par le moteur, avant qu'on l'écrase) moins la
    # valeur APRÈS. On NE repart PAS de l'aire re-projetée `zone_m.area`, qui diffère de quelques m²
    # du chiffre moteur — sinon « 170 → 130 » affichait « déduit 46 » au lieu de « 40 ».
    orig_m2 = getattr(result, "zoneImplantationM2", None)
    z_gj = getattr(result, "zoneImplantationGeoJSON", None)
    b_fc = getattr(result, "batiExistantGeoJSON", None)
    if not z_gj or not b_fc or not (b_fc.get("features") if isinstance(b_fc, dict) else None):
        return
    try:
        from shapely.geometry import mapping, shape
        from shapely.ops import unary_union
        from shapely.validation import make_valid
        from ._geom import to_metric, to_wgs
        contour_m = make_valid(to_metric(shape(result.contourGeoJSON))) if result.contourGeoJSON else None
        zone_m = make_valid(to_metric(shape(z_gj)))
        if zone_m.is_empty or zone_m.area <= 0:
            return
        feats, batis_m = [], []
        for f in b_fc["features"]:
            if not f.get("geometry"):
                continue
            gm = make_valid(to_metric(shape(f["geometry"])))
            if contour_m is not None:
                gm = gm.intersection(contour_m)           # S10 — découpe au contour
            if gm.is_empty:
                continue
            batis_m.append(gm)
            feats.append({"type": "Feature", "properties": f.get("properties") or {},
                          "geometry": mapping(to_wgs(gm))})
        if not batis_m:
            return
        bati_union = unary_union(batis_m)
        zone_deduit = zone_m.difference(bati_union)        # S7 — déduction du bâti
        if zone_deduit.is_empty:
            return
        brute_m2, deduit_m2 = round(zone_m.area), round(zone_deduit.area)
        result.batiExistantGeoJSON = {"type": "FeatureCollection", "features": feats}
        result.zoneImplantationGeoJSON = mapping(to_wgs(zone_deduit))
        result.zoneImplantationM2 = deduit_m2
        # U4 — retrait réel = (avant affiché) − (après). Repli sur l'aire re-projetée si le moteur
        # n'a pas posé de valeur avant (jamais négatif).
        ref_avant = round(orig_m2) if isinstance(orig_m2, (int, float)) else brute_m2
        result.batiDeduitM2 = max(0, ref_avant - deduit_m2)
    except Exception:  # noqa: BLE001 — géométrie dégénérée : on garde le résultat non déduit
        pass
