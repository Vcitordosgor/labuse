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
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..faisabilite.zonage import resolve_zone
from ..faisabilite.zone_servie import zone_dominante
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


def _has_chemin_neighbor(session: Session, parcel_id: int) -> bool:
    """Voisin cadastré collé de type CHEMIN privé : élancé (compacité < 3), sans bâti, non
    traversé par un axe carrossable BD TOPO (sinon ce serait une parcelle-voirie). Signale une
    enclave desservie par voie privée (E2)."""
    return bool(session.execute(text(
        """SELECT EXISTS(
             SELECT 1 FROM parcels o
             WHERE o.id <> :pid
               AND ST_DWithin(o.geom_2975, (SELECT geom_2975 FROM parcels WHERE id=:pid), 0.5)
               AND (ST_Area(o.geom_2975) / NULLIF(ST_Perimeter(o.geom_2975), 0)) < 3.0
               AND NOT EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment'
                              AND ST_Intersects(b.geom_2975, o.geom_2975))
               AND NOT EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie'
                              AND v.subtype NOT IN ('Sentier','Escalier')
                              AND ST_Intersects(v.geom_2975, o.geom_2975)))"""
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

    # --- zone dominante + multi-zones ----------------------------------------
    zs = zone_dominante(session, pid)
    racc["zone"] = {"code": zs.zone, "famille": zs.zone_fam, "a_cheval": zs.a_cheval}
    if zs.a_cheval:
        blocking.append("parcelle à cheval sur ≥ 2 zones PLU (règle non unique)")
    if not zs.zone:
        blocking.append("zone PLU indéterminée")

    # --- règles PLU via zonage.py (validées-only ; propose = bloquant) --------
    if zs.zone:
        zr = resolve_zone(zs.zone, commune)
        if zr is None:
            blocking.append(f"zone {zs.zone} hors calibrage PLU")
        elif getattr(zr, "regle_non_validee", None):
            blocking.append(f"règle PLU non validée (propose) : {zr.regle_non_validee}")
        elif not getattr(zr, "calibree", False):
            blocking.append(f"PLU non calibré pour la zone {zs.zone} (estimation générique)")
        else:
            plu_zone_src = RegulatorySource(document=f"PLU — {commune}", zone=zs.zone, provider=PLU_PROVIDER)
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
            if emp is not None:
                max_footprint = MaxFootprint(ruleId=f"{zs.zone}-emprise", percent=emp, source=plu_zone_src)
                applicable.append(ApplicableRule(id=f"{zs.zone}-emprise", label="Emprise maximale",
                                                 category="maxFootprint", integrationStatus="integrated",
                                                 detail=f"{emp:g} %", source=plu_zone_src))
            else:
                blocking.append("emprise (CES) non réglementée / non validée")
            if haut is not None:
                max_height = MaxHeight(ruleId=f"{zs.zone}-hauteur", meters=haut, source=plu_zone_src)
                applicable.append(ApplicableRule(id=f"{zs.zone}-hauteur", label="Hauteur maximale",
                                                 category="maxHeight", integrationStatus="integrated",
                                                 detail=f"{haut:g} m", source=plu_zone_src))
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
        gj = session.execute(text(
            "SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Transform(ST_Intersection("
            "  ST_Union(sl.geom_2975), p.geom_2975), 4326), 3)) "
            "FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind='ppr' "
            "AND sl.subtype='INTERDICTION' AND ST_Intersects(sl.geom_2975, p.geom_2975) "
            "GROUP BY p.geom_2975"
        ), {"pid": pid}).first()
        if gj and gj[0]:
            geo = json.loads(gj[0])
            if geo.get("coordinates"):
                exclusions.append(Exclusion(id="ppr-rouge", ruleId="PPR", type="ppr_rouge",
                                            label="PPR zone rouge exclue", geometry=geo, source=ppr_src))

    # --- classification des limites (SERVIE) --------------------------------
    setbacks: list[Setback] = []
    voies_privees = False   # citation PLU « voies privées » (câblé au lot C)
    if not blocking:  # n'y toucher que si le PLU est complet et unique
        lim = classify_parcel_limits(session, pid)
        mill = _bdtopo_millesime(session)
        bdtopo_src = RegulatorySource(
            document="BD TOPO® — troncon_de_route (voirie) + cadastre",
            versionDate=mill, provider=f"LABUSE — adjacence cadastre + BD TOPO {mill}")

        def _rule_voie(detail):
            return ApplicableRule(id="limite-voie", label="Recul voie", category="setback",
                                  integrationStatus="integrated", detail=detail, source=bdtopo_src)

        def _rule_sep():
            return ApplicableRule(id="limite-sep", label="Limites séparatives", category="setback",
                                  integrationStatus="integrated",
                                  detail=f"Recul séparatif {recul_sep:g} m — PLU {commune} {zs.zone} (validé)",
                                  source=bdtopo_src)

        def _setbacks_for(edges, include_voie):
            for i, e in enumerate(edges):
                if e.type in ("side", "rear"):
                    setbacks.append(Setback(id=f"lim-{i}", ruleId="limite-sep", type=e.type,
                                            geometry=geojson_from_shape(to_wgs(e.geom)),
                                            setbackM=recul_sep, source=bdtopo_src))
                elif include_voie and e.type == "voie":
                    setbacks.append(Setback(id=f"lim-{i}", ruleId="limite-voie", type="road",
                                            geometry=geojson_from_shape(to_wgs(e.geom)),
                                            setbackM=recul_voie, source=bdtopo_src))

        if lim is None:
            blocking.append("géométrie de parcelle indisponible")
        else:
            n_voie = sum(1 for e in lim.edges if e.type == "voie")
            n_sep = sum(1 for e in lim.edges if e.type in ("side", "rear"))
            racc["classification"] = {"provider": bdtopo_src.provider, "voie": n_voie, "side":
                                      sum(1 for e in lim.edges if e.type == "side"),
                                      "rear": sum(1 for e in lim.edges if e.type == "rear"),
                                      "non_classees": lim.non_classees}
            if lim.non_classees:
                blocking.append("Limites de la parcelle non qualifiées (voie / limite séparative) — "
                                + " ; ".join(lim.non_classees))
            elif not lim.has_voie:
                # ENCLAVE : E1 servie en séparatives seules (recul voie « sans objet ») ;
                # E2 (chemin privé cadastré) bloquée sauf citation visant les voies privées.
                if _has_chemin_neighbor(session, pid) and not voies_privees:
                    blocking.append("parcelle sans façade sur voie : accès par voie privée non qualifiée")
                    racc["enclave"] = "E2 (chemin privé)"
                elif recul_sep is None:
                    blocking.append("recul sur limite séparative non réglementé / non validé")
                else:
                    sources.append(bdtopo_src)
                    applicable.append(_rule_sep())
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
                    applicable.append(_rule_voie(f"Recul voie {recul_voie:g} m — PLU {commune} {zs.zone} (validé)"))
                    applicable.append(_rule_sep())
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
