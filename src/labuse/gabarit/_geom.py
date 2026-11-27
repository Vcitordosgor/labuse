"""Helpers géométriques purs du moteur Gabarit (shapely + pyproj, aucune DB).

Le calcul se fait en CRS MÉTRIQUE (EPSG:2975, RGR92 / UTM 40S — La Réunion) pour que
buffers et surfaces soient en mètres ; les entrées/sorties carte restent en 4326.
Déterministe : aucune source d'horloge/aléa.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform

METRIC_EPSG = 2975
WGS84_EPSG = 4326


@lru_cache(maxsize=2)
def _tf(src: int, dst: int) -> Transformer:
    return Transformer.from_crs(f"EPSG:{src}", f"EPSG:{dst}", always_xy=True)


def shape_from_geojson(gj: dict[str, Any]) -> BaseGeometry:
    """GeoJSON (mapping) -> shapely. Lève si la forme est invalide."""
    return shape(gj)


def geojson_from_shape(geom: BaseGeometry) -> dict[str, Any]:
    return mapping(geom)


def to_metric(geom_4326: BaseGeometry) -> BaseGeometry:
    return shp_transform(_tf(WGS84_EPSG, METRIC_EPSG).transform, geom_4326)


def to_wgs(geom_2975: BaseGeometry) -> BaseGeometry:
    return shp_transform(_tf(METRIC_EPSG, WGS84_EPSG).transform, geom_2975)


def soustraire_intervalles(seg, spans):
    """Retire de [d0,d1] les intervalles `spans` (emprises bâties) → liste de sous-segments."""
    out = [seg]
    for a, b in spans:
        nxt = []
        for s0, s1 in out:
            if b <= s0 or a >= s1:
                nxt.append((s0, s1))
            else:
                if s0 < a:
                    nxt.append((s0, a))
                if b < s1:
                    nxt.append((b, s1))
        out = nxt
    return out
