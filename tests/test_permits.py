"""SITADEL — historique des autorisations à proximité (Lot C4), sur PostGIS réel."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.permits import nearby_permits

pytestmark = pytest.mark.db


def _parcel(db, idu, wkt):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Permia','S','1', ST_GeomFromText(:w,4326), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt}).scalar()


def _permit(db, pid, typ, idus, point_wkt=None):
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw) VALUES "
        "(:pid,:t, now() - interval '1 year', CAST(:i AS jsonb),'Permia',"
        "  CASE WHEN CAST(:w AS text) IS NULL THEN NULL ELSE ST_GeomFromText(CAST(:w AS text),4326) END, '{}'::jsonb)"),
        {"pid": pid, "t": typ, "i": json.dumps(idus), "w": point_wkt})


def test_permit_rattache_par_idu(db_session):
    pid = _parcel(db_session, "PMT00001",
                  "POLYGON((55.40 -21.00,55.401 -21.00,55.401 -20.999,55.40 -20.999,55.40 -21.00))")
    _permit(db_session, "PC-RAT", "PC", ["PMT00001"], "POINT(55.4005 -20.9995)")
    pm = nearby_permits(db_session, pid)
    assert pm["count"] >= 1 and pm["rattaches"] == 1
    assert pm["items"][0]["rattache"] is True and pm["items"][0]["type"] == "PC"


def test_permit_proximite_distance(db_session):
    pid = _parcel(db_session, "PMT00002",
                  "POLYGON((55.50 -21.10,55.501 -21.10,55.501 -21.099,55.50 -21.099,55.50 -21.10))")
    _permit(db_session, "PC-NEAR", "DP", [], "POINT(55.5015 -21.0995)")   # ~150 m
    pm = nearby_permits(db_session, pid, radius_m=300)
    assert pm["count"] == 1 and pm["rattaches"] == 0
    it = pm["items"][0]
    assert it["rattache"] is False and it["distance_m"] is not None and it["distance_m"] <= 300


def test_permit_hors_rayon_absent(db_session):
    pid = _parcel(db_session, "PMT00003",
                  "POLYGON((55.60 -21.20,55.601 -21.20,55.601 -21.199,55.60 -21.199,55.60 -21.20))")
    _permit(db_session, "PC-FAR", "PC", [], "POINT(55.610 -21.205)")      # ~1 km
    pm = nearby_permits(db_session, pid, radius_m=300)
    assert pm["count"] == 0
