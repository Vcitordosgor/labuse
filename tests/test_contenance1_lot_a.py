"""CONTENANCE-1 (Lot A) — la contenance cadastrale (champ Etalab `contenance`) est stockée.

A1 : `ingest_parcels` écrit `parcels.contenance_m2` ; la géométrie et `surface_m2` restent
le DESSIN (ST_Area), intacts. A3 : une ré-ingestion (upsert) remplit/actualise la colonne.
`parse_etalab` normalise la contenance en entier (ou None).
"""
from __future__ import annotations

import json

from sqlalchemy import text

from labuse.ingestion import cadastre_bulk
from labuse.ingestion.cadastre_ingest import ingest_parcels


# ───────────────────────── pur : parse_etalab / coercion ─────────────────────────

def _feature(idu: str, contenance, numero="1") -> dict:
    return {
        "type": "Feature",
        "properties": {"id": idu, "commune": "97415", "section": "CW",
                       "numero": numero, "contenance": contenance},
        "geometry": {"type": "Polygon", "coordinates": [
            [[55.30, -21.00], [55.301, -21.00], [55.301, -21.001],
             [55.30, -21.001], [55.30, -21.00]]]},
    }


def test_parse_etalab_contenance_entier():
    fc = {"features": [_feature("97415000CW0001", 25633),
                       _feature("97415000CW0002", "694"),   # chaîne numérique tolérée
                       _feature("97415000CW0003", None),     # absente → None
                       _feature("97415000CW0004", -5)]}      # absurde → None
    out = {p["idu"]: p["contenance"] for p in cadastre_bulk.parse_etalab(fc)}
    assert out["97415000CW0001"] == 25633
    assert out["97415000CW0002"] == 694
    assert out["97415000CW0003"] is None
    assert out["97415000CW0004"] is None
    assert all(c is None or isinstance(c, int) for c in out.values())


# ───────────────────────── db : ingest écrit contenance_m2 ─────────────────────────

def _ingest(s, idu, contenance):
    parcels = cadastre_bulk.parse_etalab({"features": [_feature(idu, contenance)]})
    return ingest_parcels(s, parcels, "Saint-Paul", None)


def test_ingest_ecrit_contenance_sans_toucher_le_dessin(db_session):
    s = db_session
    _ingest(s, "97415000CW0658", 25633)
    row = s.execute(text(
        "SELECT contenance_m2, round(surface_m2) AS dessin FROM parcels WHERE idu=:i"),
        {"i": "97415000CW0658"}).one()
    # A1 : la contenance est stockée telle quelle (entier) ...
    assert row.contenance_m2 == 25633
    # ... et surface_m2 reste le DESSIN mesuré en 2975 (strictement positif, ≠ contenance).
    assert row.dessin is not None and row.dessin > 0
    assert row.dessin != 25633


def test_reingestion_actualise_la_contenance(db_session):
    s = db_session
    _ingest(s, "97415000CW0659", 1000)
    _ingest(s, "97415000CW0659", 1234)          # upsert sur le même IDU (A3)
    (val,) = s.execute(text(
        "SELECT contenance_m2 FROM parcels WHERE idu=:i"), {"i": "97415000CW0659"}).one()
    assert val == 1234


def test_contenance_absente_reste_nulle(db_session):
    s = db_session
    _ingest(s, "97415000CW0660", None)
    (val,) = s.execute(text(
        "SELECT contenance_m2 FROM parcels WHERE idu=:i"), {"i": "97415000CW0660"}).one()
    assert val is None
