"""Aménités OSM (Vague C bonus) — parsing Overpass + distance par parcelle.

Sélecteurs/catégories figés (école/santé/commerce/tcsp). Vérifié live 05/07/2026 (Saint-Paul).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion.amenites import (
    CATEGORIES,
    _points,
    _query,
    compute_amenites_commune,
    sample_report,
)


# ───────────────────────── pur ─────────────────────────

def test_categories():
    assert set(CATEGORIES) == {"ecole", "sante", "commerce", "tcsp"}


def test_query_bbox():
    q = _query('["amenity"="school"]', (55.2, -21.1, 55.4, -20.9))
    assert "node[" in q and "way[" in q and "out center" in q
    assert "-21.1,55.2,-20.9,55.4" in q     # s,w,n,e (ordre Overpass)


def test_points():
    data = {"elements": [
        {"type": "node", "lon": 55.27, "lat": -21.01, "tags": {"name": "École A"}},
        {"type": "way", "center": {"lon": 55.28, "lat": -21.02}, "tags": {"name": "Collège B"}},
        {"type": "node", "tags": {}},          # sans coords → ignoré
    ]}
    pts = list(_points(data))
    assert pts == [(55.27, -21.01, "École A"), (55.28, -21.02, "Collège B")]


# ───────────────────────── DB : distances ─────────────────────────

def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


def _poi(db, cat, lon, lat):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom) VALUES "
        "('amenite',:cat,:cat, ST_SetSRID(ST_Point(:lon,:lat),4326))"),
        {"cat": cat, "lon": lon, "lat": lat})


@pytest.mark.db
def test_compute_distances(db_session):
    # parcelle au centre ; école à ~110 m, santé à ~2 km ; pas de commerce/tcsp.
    _parcel(db_session, "97415000AA0001", "Saint-Paul",
            "POLYGON((55.2700 -21.0100, 55.2701 -21.0100, 55.2701 -21.0099, 55.2700 -21.0099, 55.2700 -21.0100))")
    _poi(db_session, "ecole", 55.2710, -21.0100)      # ~100 m à l'est
    _poi(db_session, "ecole", 55.30, -21.05)          # loin
    _poi(db_session, "sante", 55.29, -21.01)          # ~2 km
    db_session.flush()

    n = compute_amenites_commune(db_session, "Saint-Paul")
    assert n == 1
    row = db_session.execute(text(
        "SELECT dist_ecole_m, dist_sante_m, dist_commerce_m, dist_tcsp_m "
        "FROM parcel_amenites a JOIN parcels p ON p.id=a.parcel_id WHERE p.commune='Saint-Paul'")).first()
    assert 50 < row[0] < 200          # école la plus proche ~100 m (pas celle au loin)
    assert 1500 < row[1] < 2500       # santé ~2 km
    assert row[2] is None and row[3] is None   # pas de commerce/tcsp → NULL (pas de faux 0)

    rep = sample_report(db_session, "Saint-Paul")
    assert rep["distances_medianes_m"]["parcelles"] == 1


@pytest.mark.db
def test_compute_idempotent(db_session):
    _parcel(db_session, "97415000AA0001", "Saint-Paul",
            "POLYGON((55.27 -21.01, 55.271 -21.01, 55.271 -21.009, 55.27 -21.009, 55.27 -21.01))")
    _poi(db_session, "ecole", 55.271, -21.01)
    db_session.flush()
    compute_amenites_commune(db_session, "Saint-Paul")
    compute_amenites_commune(db_session, "Saint-Paul")   # re-run
    assert db_session.execute(text("SELECT count(*) FROM parcel_amenites")).scalar() == 1  # upsert
