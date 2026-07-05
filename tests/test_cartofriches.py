"""Cartofriches (Vague C1) — parsing friche + rattachement parcelle exact (refcad) / polygone.

Schéma figé sur une friche RÉELLE vérifiée live 05/07/2026 (site_id 97415_10812, FRICHE DE SAVANNA).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion.cartofriches import (
    _refcad,
    ingest_commune,
    parcelles_croisees,
    parse_friche,
    sample_report,
)

# Feature GeoJSON réelle simplifiée (géométrie réduite à un petit carré autour de Savanna).
FEATURE = {
    "id": "97415_10812", "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[
        [55.2974, -20.9885], [55.2977, -20.9885], [55.2977, -20.9882], [55.2974, -20.9882], [55.2974, -20.9885]]]},
    "properties": {
        "site_nom": "FRICHE DE SAVANNA", "site_type": "inconnu", "site_statut": "friche avec projet",
        "comm_insee": "97415", "proprio_personne": "personne morale",
        "unite_fonciere_surface": 2022796.05, "source_nom": "Appel à projet Fonds Friches",
        "nature": "fond friche", "urba_zone_type": "U",
        "unite_fonciere_refcad": ["97415000BH0152", "97415000BH0156", "97415000BH0157"]},
}
DETAIL = {"sol_pollution_existe": "inconnu", "site_vocadomi": "mixte", "p_residentiel": None,
          "taux_artif_ff": 5, "urba_zone_lib": "U1e - ", "proprio_nom": ["{", "\"", "D"]}  # proprio_nom cassé, ignoré


# ───────────────────────── parsing (pur) ─────────────────────────

def test_refcad_normalise():
    assert _refcad({"unite_fonciere_refcad": ["A", "B"]}) == ["A", "B"]
    assert _refcad({"unite_fonciere_refcad": "['X', 'Y']"}) == ["X", "Y"]   # chaîne → liste
    assert _refcad({}) == []


def test_parse_friche():
    p = parse_friche(FEATURE, DETAIL)
    assert p["kind"] == "friche"
    assert p["subtype"] == "friche avec projet"
    assert p["name"] == "FRICHE DE SAVANNA"
    assert p["geometry"]["type"] == "Polygon"
    assert p["attrs"]["site_id"] == "97415_10812"
    assert p["attrs"]["refcad"] == ["97415000BH0152", "97415000BH0156", "97415000BH0157"]
    assert p["attrs"]["detail"]["site_vocadomi"] == "mixte"
    assert "proprio_nom" not in p["attrs"]["detail"]        # champ cassé écarté (pas dans DETAIL_FIELDS)


def test_parse_friche_sans_geometrie():
    assert parse_friche({"id": "x", "properties": {}, "geometry": None}) is None
    assert parse_friche({"id": "x", "properties": {}, "geometry": {"type": "Polygon"}}) is None


# ───────────────────────── ingestion / croisement (DB) ─────────────────────────

class _StubConn:
    def __init__(self, features):
        self._f = features

    def geofriches(self, insee):
        yield from self._f

    def detail(self, site_id):
        return DETAIL


def _parcel(db, idu, commune, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i,:c, ST_SetSRID(ST_GeomFromText(:w),4326), ST_Transform(ST_SetSRID(ST_GeomFromText(:w),4326),2975)) "
        "ON CONFLICT (idu) DO NOTHING"), {"i": idu, "c": commune, "w": wkt})


@pytest.mark.db
def test_ingest_et_croisement_exact(db_session):
    ingest_commune(db_session, "97415", "Saint-Paul", connector=_StubConn([FEATURE]))
    assert db_session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='friche' AND commune='Saint-Paul'")).scalar() == 1

    # Une parcelle dont l'IDU est dans refcad (rattachement EXACT) + une DANS le polygone mais
    # hors refcad (fallback polygone) + une hors des deux.
    _parcel(db_session, "97415000BH0152", "Saint-Paul",   # ∈ refcad, loin géographiquement
            "POLYGON((55.10 -21.10, 55.101 -21.10, 55.101 -21.099, 55.10 -21.099, 55.10 -21.10))")
    _parcel(db_session, "97415000BH9999", "Saint-Paul",   # ∉ refcad mais SOUS le polygone friche
            "POLYGON((55.2975 -20.9884, 55.2976 -20.9884, 55.2976 -20.9883, 55.2975 -20.9883, 55.2975 -20.9884))")
    _parcel(db_session, "97415000BH0001", "Saint-Paul",   # ni l'un ni l'autre
            "POLYGON((55.00 -21.30, 55.001 -21.30, 55.001 -21.299, 55.00 -21.299, 55.00 -21.30))")
    db_session.flush()

    cr = parcelles_croisees(db_session, "Saint-Paul")
    assert cr["exact_refcad"] == 1        # BH0152 par son IDU (même si géographiquement ailleurs)
    assert cr["polygone"] == 1            # BH9999 par intersection géométrique

    rep = sample_report(db_session, "Saint-Paul")
    assert rep["friches"] == 1
    assert rep["exemples"][0]["name"] == "FRICHE DE SAVANNA"
    assert rep["exemples"][0]["n_parcelles"] == 3


@pytest.mark.db
def test_ingest_idempotent(db_session):
    conn = _StubConn([FEATURE])
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)
    ingest_commune(db_session, "97415", "Saint-Paul", connector=conn)   # re-run purge + réinsère
    assert db_session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE kind='friche' AND commune='Saint-Paul'")).scalar() == 1
