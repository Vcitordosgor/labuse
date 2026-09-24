"""Moteur géospatial pur et déterministe (CDC §4).

Indépendant de React, de la carte et de la base. Ne connaît pas le réel du fictif :
même contrat, même calcul. Entrée non mutée.

Étapes : partir du polygone cadastral → appliquer les reculs par limite (road/side/
rear) → soustraire les exclusions → zone finale d'implantation (Polygon,
MultiPolygon ou zone vide valide) → surface → plafond d'emprise calculé À PART.
Jamais `min(zoneImplantation, plafondEmprise)`.
"""
from __future__ import annotations

from typing import Optional

from shapely.geometry import GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from ._geom import geojson_from_shape, shape_from_geojson, to_metric, to_wgs
from .contract import (
    AppliedRule,
    Coverage,
    GabaritInput,
    GabaritResult,
    NonIntegratedRule,
    RegulatorySource,
)
from .validate import validate_input

INCOMPLETE_MESSAGE = "Calcul incomplet — donnée réglementaire manquante"


def _round(x: float, n: int = 1) -> float:
    return round(float(x), n)


def _as_polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Ne garde que la part surfacique (Polygon/MultiPolygon) d'un résultat booléen."""
    if geom.is_empty:
        return geom
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    if isinstance(geom, GeometryCollection):
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        return unary_union(polys) if polys else geom
    return geom


def _grouped_setbacks(inp: GabaritInput) -> list[AppliedRule]:
    """Regroupe les reculs partageant (ruleId, valeur, source). Ne fusionne jamais si
    la valeur ou la source diffère (CDC §7)."""
    order: list[tuple] = []
    seen: dict[tuple, AppliedRule] = {}
    rules_by_id = {ar.id: ar for ar in inp.applicableRules if ar.id}
    for sb in inp.setbacks:
        src = sb.source or RegulatorySource()
        key = (sb.ruleId, round(sb.setbackM, 4) if sb.setbackM is not None else None,
               src.document, src.zone, src.article, src.versionDate, src.provider)
        if key in seen:
            continue
        ar = rules_by_id.get(sb.ruleId)
        label = (ar.label if ar and ar.label else "Recul")
        seen[key] = AppliedRule(ruleId=sb.ruleId or "", category="setback", label=label,
                                value=sb.setbackM, unit="m", source=src)
        order.append(key)
    return [seen[k] for k in order]


def compute_gabarit(inp: GabaritInput) -> GabaritResult:
    """Valide puis calcule. Ne mute jamais l'entrée."""
    errs = validate_input(inp)
    if errs:
        return GabaritResult(status="incomplete", message=INCOMPLETE_MESSAGE,
                             validationErrors=errs)

    # --- géométries en métrique (copies ; l'entrée n'est pas mutée) ----------
    parcel_4326 = shape_from_geojson(inp.parcel.geometry)
    parcel_m = to_metric(parcel_4326)

    buffers = []
    for sb in inp.setbacks:
        line_m = to_metric(shape_from_geojson(sb.geometry))
        if sb.setbackM and sb.setbackM > 0:
            buffers.append(line_m.buffer(sb.setbackM))
    setback_union = unary_union(buffers) if buffers else None

    after_setbacks = parcel_m.difference(setback_union) if setback_union is not None else parcel_m
    after_setbacks = _as_polygonal(after_setbacks)

    excl_polys = [to_metric(shape_from_geojson(ex.geometry)) for ex in inp.exclusions]
    excl_union = unary_union(excl_polys) if excl_polys else None
    zone_m = after_setbacks.difference(excl_union) if excl_union is not None else after_setbacks
    zone_m = _as_polygonal(zone_m)

    # bandes de retrait (pour la carte) = ce que les reculs retirent de la parcelle
    retrait_m = _as_polygonal(parcel_m.difference(after_setbacks)) if setback_union is not None else None
    excl_in_parcel_m = _as_polygonal(parcel_m.intersection(excl_union)) if excl_union is not None else None

    # --- métriques ------------------------------------------------------------
    mf, mh = inp.maxFootprint, inp.maxHeight
    footprint_absent = mf.status == "absent"
    hauteur_non_integree = mh.status == "not_integrated"

    surface_parcelle = float(inp.parcel.areaM2)          # valeur cadastrale sourcée
    zone_m2 = float(zone_m.area)
    # plafond calculé À PART (jamais min()) ; None si le règlement ne fixe pas de CES (silence prouvé)
    plafond_m2 = None if footprint_absent else surface_parcelle * mf.percent / 100.0
    hauteur = None if hauteur_non_integree else float(mh.meters)

    # --- couverture réglementaire ---------------------
    # emprise absente = « vérifiée — sans plafond » (le silence est une donnée) ; hauteur prospect = non intégrée.
    risk_ok = any(ar.category == "exclusion" and ar.source and ar.source.document
                  for ar in inp.applicableRules)
    coverage = Coverage(reculs=bool(inp.setbacks), hauteur=not hauteur_non_integree,
                        emprise=True, risques=risk_ok)

    # --- règles appliquées + non intégrées -----------------------------------
    applied: list[AppliedRule] = _grouped_setbacks(inp)
    rules_by_id = {ar.id: ar for ar in inp.applicableRules if ar.id}
    _mfr = rules_by_id.get(mf.ruleId)
    applied.append(AppliedRule(
        ruleId=mf.ruleId or "", category="maxFootprint",
        label=(_mfr.label if _mfr and _mfr.label else ("Emprise au sol" if footprint_absent else "Emprise maximale")),
        value=None if footprint_absent else mf.percent, unit=None if footprint_absent else "%",
        detail=(_mfr.detail if footprint_absent and _mfr else None), source=mf.source))
    # la hauteur en prospect n'est PAS une règle appliquée : elle va dans « non intégrées » (ci-dessous)
    if not hauteur_non_integree:
        applied.append(AppliedRule(
            ruleId=mh.ruleId or "", category="maxHeight",
            label=(rules_by_id.get(mh.ruleId).label if rules_by_id.get(mh.ruleId) else "Hauteur maximale"),
            value=mh.meters, unit="m", source=mh.source))
    for ex in inp.exclusions:
        ar = rules_by_id.get(ex.ruleId)
        applied.append(AppliedRule(
            ruleId=ex.ruleId or "", category="exclusion",
            label=(ar.label if ar and ar.label else (ex.label or "Exclusion")),
            detail=ex.label, source=ex.source))

    non_integ = [NonIntegratedRule(id=ar.id, label=ar.label or (ar.id or "règle"),
                                   source=ar.source)
                 for ar in inp.applicableRules if ar.integrationStatus == "not_integrated"]

    def _gj(g: Optional[BaseGeometry]):
        if g is None or g.is_empty:
            return None
        return geojson_from_shape(to_wgs(g))

    return GabaritResult(
        status="ok",
        surfaceParcelleM2=_round(surface_parcelle),
        zoneImplantationM2=_round(zone_m2),
        plafondEmpriseM2=None if plafond_m2 is None else _round(plafond_m2),
        plafondEmpriseStatus=mf.status,
        hauteurReglementaireM=None if hauteur is None else _round(hauteur),
        hauteurSource=mh.source,
        hauteurStatus=mh.status,
        hauteurBase=mh.basis,
        hauteurEgoutM=None if mh.egoutMeters is None else _round(mh.egoutMeters),
        coverage=coverage,
        appliedRules=applied,
        nonIntegratedRules=non_integ,
        contourGeoJSON=_gj(parcel_m),
        zoneImplantationGeoJSON=_gj(zone_m),
        retraitsGeoJSON=_gj(retrait_m),
        exclusionsGeoJSON=_gj(excl_in_parcel_m),
    )
