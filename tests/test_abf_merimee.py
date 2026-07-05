"""ABF / Mérimée (clôture Vague B) — parsing coords + abords (tampon 500 m) + intersection parcelle.

Schéma figé sur un enregistrement RÉEL vérifié live 05/07/2026 (Mérimée, Saint-Denis 97411).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.connectors.merimee import MerimeeConnector
from labuse.ingestion.abf_merimee import FLAG, bilan, ingest, parcelles_intersectees

REC = {"reference": "PA97400001", "denomination_de_l_edifice": "chapelle",
       "nature_de_la_protection": "arrêté", "commune_forme_editoriale": "Saint-Denis",
       "cog_insee_lors_de_la_protection": ["97411"],
       "coordonnees_au_format_wgs84": {"lat": -20.8829, "lon": 55.4571}}


# ───────────────────────── pur ─────────────────────────

def test_coords():
    assert MerimeeConnector.coords(REC) == (55.4571, -20.8829)         # (lon, lat)
    assert MerimeeConnector.coords({"coordonnees_au_format_wgs84": {"lat": 48.85, "lon": 2.35}}) is None  # métropole
    assert MerimeeConnector.coords({}) is None


# ───────────────────────── DB : abords + intersection ─────────────────────────

class _Stub:
    def __init__(self, records):
        self._r = records

    def fetch_reunion(self):
        yield from self._r

    coords = staticmethod(MerimeeConnector.coords)


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


@pytest.mark.db
def test_ingest_abords_et_intersection(db_session):
    # parcelle À ~120 m du MH (dans le tampon 500 m) et une À ~2 km (hors tampon).
    _parcel(db_session, "97411000AA0001", "Saint-Denis",
            "POLYGON((55.4581 -20.8829, 55.4582 -20.8829, 55.4582 -20.8828, 55.4581 -20.8828, 55.4581 -20.8829))")
    _parcel(db_session, "97411000AA0002", "Saint-Denis",
            "POLYGON((55.48 -20.86, 55.481 -20.86, 55.481 -20.859, 55.48 -20.859, 55.48 -20.86))")
    db_session.flush()

    res = ingest(db_session, connector=_Stub([REC]))
    assert res == {"mh_total": 1, "mh_geolocalises": 1}

    row = db_session.execute(text(
        "SELECT subtype, name, attrs->>'flag', attrs->>'reference', ST_GeometryType(geom) "
        "FROM spatial_layers WHERE kind='abf'")).first()
    assert row[0] == "arrêté" and row[1] == "chapelle"
    assert row[2] == FLAG                                  # « covisibilité à instruire »
    assert row[3] == "PA97400001"
    assert "Polygon" in row[4]                             # le tampon est un polygone, pas un point

    assert parcelles_intersectees(db_session) == 1        # seule la parcelle proche est dans le tampon
    b = bilan(db_session)
    assert b["abords"] == 1 and b["parcelles_intersectees"] == 1


@pytest.mark.db
def test_ingest_purge_ancien(db_session):
    # un ancien abf (ex-GPU) est purgé au réingest.
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom) VALUES "
        "('abf','AC1','vieux', ST_SetSRID(ST_GeomFromText('POINT(55.45 -20.88)'),4326))"))
    db_session.flush()
    ingest(db_session, connector=_Stub([REC]))
    assert db_session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='abf' AND name='vieux'")).scalar() == 0
    assert db_session.execute(text("SELECT count(*) FROM spatial_layers WHERE kind='abf'")).scalar() == 1
