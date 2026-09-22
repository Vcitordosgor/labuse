"""Validation stricte AVANT tout calcul (CDC §3).

`validate_input` renvoie la liste des motifs d'échec (vide = valide). Le moteur, dès
qu'un motif existe, ne produit AUCUNE zone, AUCUNE métrique, AUCUNE 3D et affiche
exactement « Calcul incomplet — donnée réglementaire manquante ».

Une valeur égale à zéro est VALIDE si elle est explicitement fournie et sourcée.
"""
from __future__ import annotations

from typing import Optional

from shapely.geometry.base import BaseGeometry

from ._geom import shape_from_geojson, to_metric
from .contract import GabaritInput, RegulatorySource

TOL_ON_BOUNDARY_M = 0.5   # une limite doit longer le contour à ≤ 0,5 m
COVER_MIN_RATIO = 0.98    # le périmètre doit être couvert à ≥ 98 % par les limites


class GabaritValidationError(Exception):
    """Levée par le raccordement quand une donnée réglementaire nécessaire manque."""

    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def _source_ok(s: Optional[RegulatorySource]) -> bool:
    return s is not None and bool(s.document) and s.document.strip() != ""


def _same_source(a: RegulatorySource, b: RegulatorySource) -> bool:
    """Cohérence source valeur ↔ source règle applicable (document/article/version)."""
    return (a.document == b.document and a.article == b.article
            and a.versionDate == b.versionDate)


def _polygon(gj: Optional[dict]) -> Optional[BaseGeometry]:
    if not gj:
        return None
    try:
        g = shape_from_geojson(gj)
    except Exception:
        return None
    return g


def validate_input(inp: GabaritInput) -> list[str]:  # noqa: C901 — check-list linéaire du CDC
    errs: list[str] = []

    # --- catalogue des sources ------------------------------------------------
    if not inp.sources:
        errs.append("catalogue des sources absent")
    for s in inp.sources:
        if not _source_ok(s):
            errs.append("une source du catalogue a un document vide")
    catalogue = {s.document for s in inp.sources if _source_ok(s)}

    def _check_value_source(src: Optional[RegulatorySource], quoi: str):
        if not _source_ok(src):
            errs.append(f"{quoi} : source manquante ou document vide")
        elif src.document not in catalogue:
            errs.append(f"{quoi} : source absente du catalogue")

    # --- parcelle -------------------------------------------------------------
    p = inp.parcel
    if p is None:
        errs.append("parcelle absente")
        parcel_geom_m = None
    else:
        if not p.id:
            errs.append("identifiant de parcelle manquant")
        if p.areaM2 is None or p.areaM2 <= 0:
            errs.append("surface cadastrale manquante ou nulle")
        _check_value_source(p.source, "parcelle")
        pg = _polygon(p.geometry)
        if pg is None or pg.is_empty:
            errs.append("géométrie de parcelle absente ou illisible")
            parcel_geom_m = None
        elif not pg.is_valid or pg.geom_type not in ("Polygon", "MultiPolygon"):
            errs.append("géométrie de parcelle invalide")
            parcel_geom_m = None
        else:
            parcel_geom_m = to_metric(pg)

    # --- reculs / limites -----------------------------------------------------
    boundary_m = parcel_geom_m.boundary if parcel_geom_m is not None else None
    lines_m: list[BaseGeometry] = []
    for i, sb in enumerate(inp.setbacks):
        tag = f"recul[{sb.id or i}]"
        if sb.type not in ("road", "side", "rear"):
            errs.append(f"{tag} : type de limite absent ou invalide")
        if sb.setbackM is None or sb.setbackM < 0:
            errs.append(f"{tag} : valeur de recul manquante")
        _check_value_source(sb.source, tag)
        lg = _polygon(sb.geometry)
        if lg is None or lg.is_empty or lg.geom_type != "LineString":
            errs.append(f"{tag} : géométrie de limite absente ou non linéaire")
            continue
        lm = to_metric(lg)
        lines_m.append(lm)
        # la limite doit suivre le contour de la parcelle
        if boundary_m is not None and lm.hausdorff_distance(
                boundary_m.intersection(lm.buffer(TOL_ON_BOUNDARY_M * 4)) or lm) > TOL_ON_BOUNDARY_M:
            if lm.difference(boundary_m.buffer(TOL_ON_BOUNDARY_M)).length > TOL_ON_BOUNDARY_M:
                errs.append(f"{tag} : la limite ne suit pas la parcelle")

    # couverture du périmètre par les limites
    if boundary_m is not None and not inp.setbacks:
        errs.append("aucune limite fournie : périmètre non couvert")
    elif boundary_m is not None and lines_m:
        covered = None
        for lm in lines_m:
            band = lm.buffer(TOL_ON_BOUNDARY_M)
            part = boundary_m.intersection(band)
            covered = part if covered is None else covered.union(part)
        ratio = (covered.length / boundary_m.length) if covered is not None else 0.0
        if ratio < COVER_MIN_RATIO:
            errs.append(f"périmètre insuffisamment couvert par les limites "
                        f"({ratio * 100:.0f} % < {COVER_MIN_RATIO * 100:.0f} %)")

    # --- plafond d'emprise ----------------------------------------------------
    # status 'absent' = silence prouvé du règlement (comme un zéro explicite, CDC §3) : sourcé, servi.
    mf = inp.maxFootprint
    if mf is not None and mf.status == "absent":
        _check_value_source(mf.source, "plafond d'emprise (non réglementé)")
    elif mf is None or mf.percent is None or mf.percent < 0:
        errs.append("plafond d'emprise : valeur manquante")
    else:
        _check_value_source(mf.source, "plafond d'emprise")

    # --- hauteur --------------------------------------------------------------
    # status 'not_integrated' = forme validée non chiffrée (prospect L ≥ H) : sourcée, 2D servie, 3D non.
    mh = inp.maxHeight
    if mh is not None and mh.status == "not_integrated":
        _check_value_source(mh.source, "hauteur réglementaire (non chiffrée)")
    elif mh is None or mh.meters is None or mh.meters < 0:
        errs.append("hauteur réglementaire : valeur manquante")
    else:
        _check_value_source(mh.source, "hauteur réglementaire")

    # --- exclusions -----------------------------------------------------------
    for i, ex in enumerate(inp.exclusions):
        tag = f"exclusion[{ex.id or i}]"
        if not ex.type:
            errs.append(f"{tag} : type manquant")
        if not ex.label:
            errs.append(f"{tag} : libellé manquant")
        _check_value_source(ex.source, tag)
        eg = _polygon(ex.geometry)
        if eg is None or eg.is_empty or eg.geom_type not in ("Polygon", "MultiPolygon"):
            errs.append(f"{tag} : géométrie d'exclusion absente ou invalide")
        elif not eg.is_valid:
            errs.append(f"{tag} : géométrie d'exclusion invalide")

    # --- inventaire applicableRules ------------------------------------------
    if not inp.applicableRules:
        errs.append("inventaire applicableRules absent")
    for i, ar in enumerate(inp.applicableRules):
        if ar.integrationStatus not in ("integrated", "not_integrated"):
            errs.append(f"applicableRule[{ar.id or i}] : état d'intégration invalide")
        if ar.category not in ("setback", "maxFootprint", "maxHeight", "exclusion", "other"):
            errs.append(f"applicableRule[{ar.id or i}] : catégorie invalide")
        if not _source_ok(ar.source):
            errs.append(f"applicableRule[{ar.id or i}] : source manquante")

    # une analyse des risques explicitement sourcée DOIT exister (jamais déduite d'un
    # tableau exclusions vide)
    if not any(ar.category == "exclusion" and _source_ok(ar.source)
               for ar in inp.applicableRules):
        errs.append("analyse des risques absente de applicableRules")

    # --- cohérence ruleId ↔ règle applicable ↔ source ------------------------
    rules_by_id = {ar.id: ar for ar in inp.applicableRules if ar.id}

    def _check_rule_link(rule_id: Optional[str], src: Optional[RegulatorySource], quoi: str):
        if not rule_id:
            errs.append(f"{quoi} : ruleId manquant")
            return
        ar = rules_by_id.get(rule_id)
        if ar is None:
            errs.append(f"{quoi} : aucune règle correspondante dans applicableRules")
            return
        if ar.integrationStatus == "not_integrated":
            errs.append(f"{quoi} : règle utilisée mais marquée non intégrée")
        if _source_ok(src) and _source_ok(ar.source) and not _same_source(src, ar.source):
            errs.append(f"{quoi} : source différente de celle de la règle applicable")

    for i, sb in enumerate(inp.setbacks):
        _check_rule_link(sb.ruleId, sb.source, f"recul[{sb.id or i}]")
    if mf is not None:
        _check_rule_link(mf.ruleId, mf.source, "plafond d'emprise")
    # la hauteur en prospect est DÉCLARÉE non intégrée (pas « utilisée ») : on vérifie le lien de source
    # mais pas le drapeau « utilisée mais non intégrée » (qui n'a de sens que pour une valeur appliquée).
    if mh is not None and mh.status != "not_integrated":
        _check_rule_link(mh.ruleId, mh.source, "hauteur réglementaire")
    for i, ex in enumerate(inp.exclusions):
        _check_rule_link(ex.ruleId, ex.source, f"exclusion[{ex.id or i}]")

    return errs
