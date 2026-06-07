"""Test de surface — l'invariant le plus important du brief (§4).

« Ne jamais calculer surface/distance en degrés (4326) → intersections fausses
SANS erreur visible, le pire des bugs. Écrire un test qui vérifie que la surface
d'une parcelle connue tombe juste en m². »

On construit un rectangle d'aire EXACTE en 2975 (donc connue au m² près), on le
stocke en 4326 (comme une vraie parcelle), puis on vérifie que :
  1. la surface mesurée via geo.area_m2 (reprojection 2975) retombe sur l'aire vraie ;
  2. la même mesure côté Python (geo.geom_area_m2) concorde ;
  3. mesurer l'aire en degrés (4326) donne une valeur absurde (le piège à éviter).
"""
from __future__ import annotations

import pytest
from pyproj import Transformer
from shapely.geometry import box
from shapely.ops import transform as shp_transform
from sqlalchemy import func, select, text

from labuse import geo

pytestmark = pytest.mark.db

# Rectangle 50 m × 40 m = 2000 m², ancré sur Saint-Paul (La Réunion).
RECT_W, RECT_H = 50.0, 40.0
EXPECTED_M2 = RECT_W * RECT_H  # 2000.0


def _known_rectangle_wkt_4326() -> tuple[str, float]:
    """Construit un rectangle d'aire exacte en 2975, renvoyé en WKT 4326."""
    # Point d'ancrage : Saint-Paul ~ (lon 55.27, lat -21.01) -> coords 2975.
    to_metric = Transformer.from_crs(geo.SRID_STORAGE, geo.SRID_METRIC, always_xy=True)
    to_wgs = Transformer.from_crs(geo.SRID_METRIC, geo.SRID_STORAGE, always_xy=True)
    x0, y0 = to_metric.transform(55.27, -21.01)
    rect_metric = box(x0, y0, x0 + RECT_W, y0 + RECT_H)
    rect_4326 = shp_transform(to_wgs.transform, rect_metric)
    return rect_4326.wkt, rect_4326.area  # .area ici = aire EN DEGRÉS (le piège)


def test_surface_tombe_juste_en_m2(db_session):
    wkt_4326, area_in_degrees = _known_rectangle_wkt_4326()
    geom = func.ST_GeomFromText(wkt_4326, geo.SRID_STORAGE)

    # 1) Mesure métrique correcte (ST_Transform -> 2975)
    measured_m2 = db_session.execute(select(geo.area_m2(geom))).scalar_one()
    assert measured_m2 == pytest.approx(EXPECTED_M2, abs=0.5), (
        f"Surface attendue ≈ {EXPECTED_M2} m², obtenue {measured_m2} m²"
    )

    # 2) Mesure en DEGRÉS (4326) — doit être absurde (≈ 6e-9), JAMAIS utilisée en métier
    raw_degrees = db_session.execute(select(func.ST_Area(geom))).scalar_one()
    assert raw_degrees < 1e-6, "Le calcul en degrés doit rester un non-sens métrique"
    assert raw_degrees == pytest.approx(area_in_degrees, rel=1e-3)
    # L'écart de 9 ordres de grandeur prouve qu'on ne DOIT jamais mélanger les deux.
    assert measured_m2 / raw_degrees > 1e8


def test_python_area_concorde_avec_postgis(db_session):
    """geo.geom_area_m2 (pyproj) doit concorder avec geo.area_m2 (PostGIS)."""
    from shapely import wkt as shp_wkt

    wkt_4326, _ = _known_rectangle_wkt_4326()
    py_area = geo.geom_area_m2(shp_wkt.loads(wkt_4326))
    pg_area = db_session.execute(
        select(geo.area_m2(func.ST_GeomFromText(wkt_4326, geo.SRID_STORAGE)))
    ).scalar_one()
    assert py_area == pytest.approx(pg_area, rel=1e-6)
    assert py_area == pytest.approx(EXPECTED_M2, abs=0.5)


def test_epsg_2975_est_bien_la_reunion(db_session):
    """Garde-fou : le CRS métrique 2975 est bien RGR92 / UTM 40S."""
    srtext = db_session.execute(
        text("SELECT srtext FROM spatial_ref_sys WHERE srid = :s"), {"s": geo.SRID_METRIC}
    ).scalar_one()
    assert "RGR92" in srtext and "UTM zone 40S" in srtext
