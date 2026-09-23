"""Parcelle fictive de démonstration (CDC §9).

Toutes les sources sont marquées FICTIVES. Les mocks utilisent EXACTEMENT le même
contrat que les futures données réelles ; aucune logique spécifique au fictif ne vit
dans le moteur. Géométries construites en métrique (2975) puis converties en 4326
pour que les surfaces annoncées soient exactes (1 180 m², plafond 472 m²).
"""
from __future__ import annotations

from shapely.geometry import Polygon

from ._geom import geojson_from_shape, to_metric, to_wgs
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

# origine métrique près de Saint-Paul (La Réunion) — le fictif vit dans un repère réel
_ORIGIN = to_metric(__import__("shapely").geometry.Point(55.29, -21.03))
_X0, _Y0 = _ORIGIN.x, _ORIGIN.y
_W, _H = 40.0, 29.5  # 40 × 29,5 = 1 180 m²

_PLU = RegulatorySource(document="PLU fictif", zone="UC", provider="LABUSE — démonstration (fictif)")
_PPR = RegulatorySource(document="PPR fictif", zone="rouge", versionDate="2024-03-15",
                        provider="LABUSE — démonstration (fictif)")
_CAD = RegulatorySource(document="Cadastre fictif", provider="LABUSE — démonstration (fictif)")


def _seg_gj(ax: float, ay: float, bx: float, by: float) -> dict:
    from shapely.geometry import LineString
    return geojson_from_shape(to_wgs(LineString([(ax, ay), (bx, by)])))


def _poly_gj(coords: list[tuple[float, float]]) -> dict:
    return geojson_from_shape(to_wgs(Polygon(coords)))


def demo_gabarit_input() -> GabaritInput:
    x0, y0, w, h = _X0, _Y0, _W, _H
    parcel = Polygon([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)])
    parcel_gj = geojson_from_shape(to_wgs(parcel))

    src_voie = RegulatorySource(document="PLU fictif", zone="UC", article="UC 6",
                                provider=_PLU.provider)
    src_sep = RegulatorySource(document="PLU fictif", zone="UC", article="UC 7",
                               provider=_PLU.provider)
    src_emp = RegulatorySource(document="PLU fictif", zone="UC", article="UC 9",
                               provider=_PLU.provider)
    src_haut = RegulatorySource(document="PLU fictif", zone="UC", article="UC 10",
                                provider=_PLU.provider)

    setbacks = [
        Setback(id="s-road", ruleId="UC6", type="road", setbackM=5.0, source=src_voie,
                geometry=_seg_gj(x0, y0, x0 + w, y0)),
        Setback(id="s-right", ruleId="UC7", type="side", setbackM=3.0, source=src_sep,
                geometry=_seg_gj(x0 + w, y0, x0 + w, y0 + h)),
        Setback(id="s-rear", ruleId="UC7", type="rear", setbackM=3.0, source=src_sep,
                geometry=_seg_gj(x0 + w, y0 + h, x0, y0 + h)),
        Setback(id="s-left", ruleId="UC7", type="side", setbackM=3.0, source=src_sep,
                geometry=_seg_gj(x0, y0 + h, x0, y0)),
    ]

    # exclusion PPR rouge partielle (un coin du fond de parcelle)
    excl = Exclusion(id="ppr-1", ruleId="PPR-R", type="ppr_rouge",
                     label="PPR zone rouge exclue", source=_PPR,
                     geometry=_poly_gj([(x0 + w - 12, y0 + h - 12), (x0 + w, y0 + h - 12),
                                        (x0 + w, y0 + h), (x0 + w - 12, y0 + h)]))

    applicable = [
        ApplicableRule(id="UC6", label="Recul voie", category="setback",
                       integrationStatus="integrated", detail="5 m", source=src_voie),
        ApplicableRule(id="UC7", label="Limites séparatives", category="setback",
                       integrationStatus="integrated", detail="3 m", source=src_sep),
        ApplicableRule(id="UC9", label="Emprise maximale", category="maxFootprint",
                       integrationStatus="integrated", detail="40 %", source=src_emp),
        ApplicableRule(id="UC10", label="Hauteur maximale", category="maxHeight",
                       integrationStatus="integrated", detail="10 m", source=src_haut),
        ApplicableRule(id="PPR-R", label="PPR — zone rouge", category="exclusion",
                       integrationStatus="integrated", detail="Zone rouge exclue", source=_PPR),
        ApplicableRule(id="STAT", label="Stationnement", category="other",
                       integrationStatus="not_integrated",
                       detail="Règle connue, non chiffrée dans LABUSE", source=_PLU),
        ApplicableRule(id="ESP", label="Espaces libres", category="other",
                       integrationStatus="not_integrated",
                       detail="Règle connue, non chiffrée dans LABUSE", source=_PLU),
    ]

    return GabaritInput(
        parcel=ParcelInput(id="FICTIF-UC-001", geometry=parcel_gj, areaM2=1180.0, source=_CAD),
        setbacks=setbacks,
        maxFootprint=MaxFootprint(ruleId="UC9", percent=40.0, source=src_emp),
        maxHeight=MaxHeight(ruleId="UC10", meters=10.0, source=src_haut),
        exclusions=[excl],
        applicableRules=applicable,
        sources=[_CAD, src_voie, src_sep, src_emp, src_haut, _PPR, _PLU],
    )
