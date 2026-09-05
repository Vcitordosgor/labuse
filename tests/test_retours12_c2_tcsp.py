"""RETOURS-12 C2 — le test qui garde l'AXE DE TRANSPORT STRUCTURANT (BAOBAB Express).

Le tracé est dérivé du GTFS déjà en base (transport_ligne, route_id='BAO'). On vérifie :
  1. la couche synthétique `tcsp_axe` sert bien ce tracé (une ligne, jamais un aplat/point) ;
  2. la fiche porte le fait « distance à l'axe » avec le drapeau < 500 m (modulation possible du
     stationnement — jamais promise, à vérifier au PLU).
Test AUTO-SUFFISANT (la base de test n'a pas de parcelles) : on pose une parcelle et une ligne BAO
qui la traverse, on interroge les fonctions serveur directement (pas d'ingestion, pas de réseau).
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.api.app import _proximites_block, map_layers_geojson

pytestmark = pytest.mark.db

TEST_IDU = "97411000ZZ9001"
LON, LAT = 55.45, -20.89


def _setup(db) -> None:
    db.execute(text("DELETE FROM spatial_layers WHERE name = '__test_baobab__'"))
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": TEST_IDU})
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i, 'Saint-Denis', "
        " ST_SetSRID(ST_Buffer(ST_MakePoint(:lon, :lat), 0.0002), 4326), "
        " ST_Transform(ST_SetSRID(ST_Buffer(ST_MakePoint(:lon, :lat), 0.0002), 4326), 2975))"),
        {"i": TEST_IDU, "lon": LON, "lat": LAT})
    # ligne BAO passant PAR la parcelle (distance ~0 → sous 500 m garanti)
    line = ("ST_SetSRID(ST_MakeLine(ST_MakePoint(:lon-0.001, :lat), ST_MakePoint(:lon+0.001, :lat)), 4326)")
    db.execute(text(
        f"INSERT INTO spatial_layers (kind, subtype, name, geom, geom_2975, attrs) VALUES "
        f"('transport_ligne', 'Citalis', '__test_baobab__', {line}, ST_Transform({line}, 2975), CAST(:a AS jsonb))"),
        {"lon": LON, "lat": LAT, "a": json.dumps({"route_id": "BAO", "reseau": "Citalis", "gtfs_maj": "2026-07-16"})})


def test_couche_tcsp_axe_sert_le_trace_baobab(db_session):
    _setup(db_session)
    fc = map_layers_geojson(kind="tcsp_axe", db=db_session)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= 1
    f = fc["features"][0]
    assert f["geometry"]["type"] in ("LineString", "MultiLineString")   # un TRACÉ, jamais un aplat/point
    assert f["properties"]["name"] == "BAOBAB Express"


def test_fiche_porte_le_fait_axe_structurant_sous_500m(db_session):
    _setup(db_session)
    bloc = _proximites_block(db_session, TEST_IDU)
    assert bloc and bloc.get("tcsp"), "la fiche doit porter la proximité à l'axe structurant"
    tcsp = bloc["tcsp"]
    assert tcsp["sous_500m"] is True                      # la ligne passe par la parcelle
    assert "PEUT moduler" in tcsp["libelle"]              # jamais une promesse
    assert "à vérifier dans le PLU" in tcsp["libelle"]
    assert "BAOBAB" in tcsp["libelle"]


def test_pas_de_faux_positif_stationnement(db_session):
    """Doctrine : jamais une réduction PROMISE — le libellé signale un point à instruire."""
    _setup(db_session)
    tcsp = _proximites_block(db_session, TEST_IDU)["tcsp"]
    bas = tcsp["libelle"].lower()
    assert "rien n'est promis" in bas or "à vérifier" in bas
    for interdit in ("réduction de stationnement garantie", "stationnement réduit", "moins de places obligatoire"):
        assert interdit not in bas
