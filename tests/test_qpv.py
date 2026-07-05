"""QPV 2024 (Vague C bonus) — parsing feature + intersection parcelle.

Schéma figé sur une feature RÉELLE vérifiée live 05/07/2026 (ANCT QP2024, 974).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion.qpv import bilan, ingest, parcelles_en_qpv, parse_feature

FEAT = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[
        [55.290, -21.010], [55.294, -21.010], [55.294, -21.006], [55.290, -21.006], [55.290, -21.010]]]},
    "properties": {"code_qp": "QN97414I", "lib_qp": "Le Gol", "insee_dep": "974",
                   "insee_com": "97414", "lib_com": "Saint-Louis", "siren_epci": "200011710"},
}


# ───────────────────────── pur ─────────────────────────

def test_parse_feature():
    p = parse_feature(FEAT)
    assert p["kind"] == "qpv" and p["name"] == "Le Gol"
    assert p["attrs"]["code_qp"] == "QN97414I"
    assert p["attrs"]["insee_com"] == "97414" and p["attrs"]["generation"] == "2024"
    assert p["commune"] == "Saint-Louis"


def test_parse_feature_sans_geometrie():
    assert parse_feature({"properties": {}, "geometry": None}) is None


# ───────────────────────── DB : intersection ─────────────────────────

class _Stub:
    def __init__(self, feats):
        self._f = feats

    def fetch_dep(self, dep="974"):
        yield from self._f


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


@pytest.mark.db
def test_ingest_et_intersection(db_session):
    res = ingest(db_session, connector=_Stub([FEAT]))
    assert res == {"qpv": 1}
    # parcelle DANS le QPV + une HORS.
    _parcel(db_session, "97414000AA0001", "Saint-Louis",
            "POLYGON((55.291 -21.009, 55.292 -21.009, 55.292 -21.008, 55.291 -21.008, 55.291 -21.009))")
    _parcel(db_session, "97414000AA0002", "Saint-Louis",
            "POLYGON((55.10 -21.20, 55.101 -21.20, 55.101 -21.199, 55.10 -21.199, 55.10 -21.20))")
    db_session.flush()
    assert parcelles_en_qpv(db_session) == 1
    b = bilan(db_session)
    assert b["qpv"] == 1 and b["communes"] == 1 and b["parcelles_en_qpv"] == 1


@pytest.mark.db
def test_ingest_idempotent(db_session):
    ingest(db_session, connector=_Stub([FEAT]))
    ingest(db_session, connector=_Stub([FEAT]))   # re-run purge + réinsère
    assert db_session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='qpv'")).scalar() == 1
