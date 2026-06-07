"""Discipline des systèmes de coordonnées — LE point dur du brief (§4).

La Réunion n'est PAS en Lambert-93. Système projeté local : RGR92 / UTM 40S.

    SRID_STORAGE = 4326   -> stockage des géométries (WGS84, ce que rendent les API)
    SRID_METRIC  = 2975   -> TOUTE opération métrique (surface, distance, buffer…)

Règle absolue : ne JAMAIS calculer une surface/distance en degrés (4326).
On reprojette systématiquement en 2975 via ST_Transform avant toute mesure.
Ce module centralise ces expressions pour qu'aucun appelant n'ait à y penser.
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Float, func
from sqlalchemy.sql.elements import ColumnElement

SRID_STORAGE = 4326   # WGS84
SRID_METRIC = 2975    # RGR92 / UTM zone 40 Sud (La Réunion)


# ───────────────────────── Expressions SQL (PostGIS) ─────────────────────────

def to_metric(geom: ColumnElement) -> ColumnElement:
    """Reprojette une géométrie 4326 vers le CRS métrique 2975."""
    return func.ST_Transform(geom, SRID_METRIC)


def area_m2(geom: ColumnElement) -> ColumnElement:
    """Surface en m² (jamais en degrés)."""
    return func.ST_Area(to_metric(geom)).cast(Float)


def distance_m(geom_a: ColumnElement, geom_b: ColumnElement) -> ColumnElement:
    """Distance en mètres entre deux géométries 4326."""
    return func.ST_Distance(to_metric(geom_a), to_metric(geom_b)).cast(Float)


def buffer_m(geom: ColumnElement, meters: float) -> ColumnElement:
    """Tampon de `meters` mètres, rendu en 4326 (buffer calculé en métrique)."""
    return func.ST_Transform(func.ST_Buffer(to_metric(geom), meters), SRID_STORAGE)


def intersection_area_ratio(geom: ColumnElement, other: ColumnElement) -> ColumnElement:
    """Part de la surface de `geom` couverte par `other` (0..1), calculée en 2975.

    Robuste au cas surface nulle (renvoie 0).
    """
    inter = func.ST_Area(func.ST_Intersection(to_metric(geom), to_metric(other)))
    base = func.ST_Area(to_metric(geom))
    return func.coalesce(inter / func.nullif(base, 0.0), 0.0).cast(Float)


# ───────────────────────── Côté Python (pyproj / shapely) ─────────────────────────

@lru_cache(maxsize=1)
def _transformer_4326_to_2975():
    from pyproj import Transformer

    return Transformer.from_crs(SRID_STORAGE, SRID_METRIC, always_xy=True)


def geom_area_m2(geom_4326) -> float:
    """Surface (m²) d'une géométrie shapely exprimée en 4326, via reprojection 2975.

    Utile côté Python (tests, calculs hors base) — même résultat que `area_m2` en SQL.
    """
    from shapely.ops import transform

    metric = transform(_transformer_4326_to_2975().transform, geom_4326)
    return float(metric.area)
