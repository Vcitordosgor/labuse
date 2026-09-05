"""RETOURS-13 Lot 1 — les tests qui auraient attrapé les défauts R4 / R6 / R9.

R6 : le repli d'ingestion envoyait ELEVE et TRES_ELEVE sur « moyen » — les 484 zones de
mouvement de terrain LES PLUS GRAVES étaient servies comme moyennes, jamais de rouge à l'écran.
R4 : la moyenne tension (ligne_mt, EDF open data) doit être servie par l'endpoint couches.
R9 : la bulle d'un arrêt a besoin des NOMS de lignes (lignes_noms), pas d'un route_id opaque.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.api.app import _MAP_LAYER_KINDS, map_layers_geojson
from labuse.ingestion.layers_ingest import _classe_alea, _normalise_alea

pytestmark = pytest.mark.db


# ── R6 — mapping des degrés réels (mesurés en base le 05/09/2026) ──────────────────────────

def test_r6_degres_graves_ne_sont_plus_ecrases():
    # AVANT : ELEVE/TRES_ELEVE → « moyen » (aucun mot-clé reconnu). APRÈS : classe grave.
    assert _normalise_alea("ELEVE") == ("fort", False)
    assert _normalise_alea("TRES_ELEVE") == ("fort", False)
    assert _classe_alea("ELEVE") == "eleve"
    assert _classe_alea("TRES_ELEVE") == "tres_eleve"


def test_r6_classes_affichage_couvrent_les_8_libelles_reels():
    attendus = {
        "FAIBLE": "faible", "FAIBLE_A_MODERE": "faible",
        "MODERE": "moyen", "MOYEN": "moyen", "MOYEN_B2U": "moyen", "MOYEN_SECURISABLE": "moyen",
        "ELEVE": "eleve", "TRES_ELEVE": "tres_eleve",
    }
    for degre, classe in attendus.items():
        assert _classe_alea(degre) == classe, degre
    # inondation : le triptyque officiel reste
    for degre, classe in {"FAIBLE": "faible", "MOYEN": "moyen", "FORT": "fort"}.items():
        assert _classe_alea(degre) == classe


def test_r6_endpoint_sert_la_classe(db_session):
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = '__test_alea_r6__'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('georisque_alea', 'mouvement_terrain', '__test_alea_r6__', "
        " ST_SetSRID(ST_Buffer(ST_MakePoint(55.5, -21.0), 0.001), 4326), CAST(:a AS jsonb))"),
        {"a": json.dumps({"niveau": "moyen", "classe": "tres_eleve", "degre": "TRES_ELEVE"})})
    fc = map_layers_geojson(kind="georisque_alea", db=db_session, limit=2000)
    mien = next(f for f in fc["features"] if f["properties"]["name"] == "__test_alea_r6__")
    assert mien["properties"]["classe"] == "tres_eleve"   # la classe réelle voyage jusqu'à la carte


# ── R4 — moyenne tension EDF ───────────────────────────────────────────────────────────────

def test_r4_ligne_mt_servie(db_session):
    assert "ligne_mt" in _MAP_LAYER_KINDS
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = '__test_mt__'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('ligne_mt', 'aerien', '__test_mt__', "
        " ST_SetSRID(ST_MakeLine(ST_MakePoint(55.4, -21.0), ST_MakePoint(55.41, -21.0)), 4326), "
        " CAST(:a AS jsonb))"),
        {"a": json.dumps({"statut": "En exploitation"})})
    fc = map_layers_geojson(kind="ligne_mt", db=db_session, limit=2000)
    assert any(f["properties"]["name"] == "__test_mt__" for f in fc["features"])


# ── R9 — bulle d'arrêt : nom + lignes + réseau ─────────────────────────────────────────────

def test_r9_arret_porte_lignes_noms_et_reseau(db_session):
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = '__test_arret_r9__'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('transport_arret', 'Citalis', '__test_arret_r9__', "
        " ST_SetSRID(ST_MakePoint(55.45, -20.9), 4326), CAST(:a AS jsonb))"),
        {"a": json.dumps({"reseau": "Citalis", "stop_id": "X1", "nb_lignes": 2,
                          "lignes": ["Citalis:6", "Citalis:14"], "lignes_noms": ["6", "14"]})})
    fc = map_layers_geojson(kind="transport_arret", db=db_session, limit=20000)
    mien = next(f for f in fc["features"] if f["properties"]["name"] == "__test_arret_r9__")
    assert mien["properties"]["lignes_noms"] == ["6", "14"]   # des NOMS lisibles, pas des route_id
    assert mien["properties"]["reseau"] == "Citalis"
