"""RETOURS-13 R5 — le test qui garde la couche TCSP (remplace le test BAOBAB de RETOURS-12 C2).

Décision Vic (05/09/2026) : la couche BAOBAB seule est RETIRÉE — la vraie couche « Transport en
commun en site propre » sert les tronçons OSM (site_propre / couloir, distinction DITE) et les
STATIONS dérivées (arrêts GTFS ≤ 60 m d'un site propre). Le fait fiche se mesure À LA STATION,
seuil 800 m (art. L151-36, loi n° 2025-1129 du 26/11/2025 — vérifié sur Légifrance le 05/09/2026).
Test AUTO-SUFFISANT : on pose parcelle + station + tronçons, aucune ingestion, aucun réseau.
"""
from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from labuse.api.app import _proximites_block, map_layers_geojson

pytestmark = pytest.mark.db

TEST_IDU = "97411000ZZ9001"
LON, LAT = 55.45, -20.89


def _setup(db) -> None:
    db.execute(text("DELETE FROM spatial_layers WHERE name LIKE '__test_tcsp%'"))
    db.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": TEST_IDU})
    db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "(:i, 'Saint-Denis', "
        " ST_SetSRID(ST_Buffer(ST_MakePoint(:lon, :lat), 0.0002), 4326), "
        " ST_Transform(ST_SetSRID(ST_Buffer(ST_MakePoint(:lon, :lat), 0.0002), 4326), 2975))"),
        {"i": TEST_IDU, "lon": LON, "lat": LAT})
    # une STATION à ~310 m de la parcelle (0.003° de longitude au 974) → sous 800 m garanti
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('tcsp_station', 'en_service', '__test_tcsp_station__', "
        " ST_SetSRID(ST_MakePoint(:lon+0.003, :lat), 4326), CAST(:a AS jsonb))"),
        {"lon": LON, "lat": LAT,
         "a": json.dumps({"statut": "Dérivé", "reseau": "Citalis", "lignes_noms": ["12"]})})
    # deux TRONÇONS : un site propre + un couloir (la distinction doit voyager jusqu'à l'écran)
    line = "ST_SetSRID(ST_MakeLine(ST_MakePoint(:lon-0.001, :lat), ST_MakePoint(:lon+0.001, :lat)), 4326)"
    for sub, nat in (("site_propre", "chaussée dédiée aux bus (site propre)"),
                     ("couloir", "couloir réservé — pas un site propre L151-36")):
        db.execute(text(
            f"INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
            f"('tcsp_troncon', :s, '__test_tcsp_troncon__', {line}, CAST(:a AS jsonb))"),
            {"lon": LON, "lat": LAT, "s": sub,
             "a": json.dumps({"etat": "en_service", "nature": nat})})


def test_couche_tcsp_sert_troncons_et_distinction(db_session):
    _setup(db_session)
    fc = map_layers_geojson(kind="tcsp_troncon", db=db_session, limit=2000)
    miens = [f for f in fc["features"] if f["properties"]["name"] == "__test_tcsp_troncon__"]
    subs = {f["properties"]["subtype"] for f in miens}
    assert {"site_propre", "couloir"} <= subs        # la distinction est DITE, jamais fusionnée
    assert all(f["geometry"]["type"] in ("LineString", "MultiLineString") for f in miens)
    st = map_layers_geojson(kind="tcsp_station", db=db_session, limit=2000)
    assert any(f["properties"]["name"] == "__test_tcsp_station__" for f in st["features"])


def test_baobab_axe_retire(db_session):
    # R5 : le kind synthétique tcsp_axe n'existe plus (couche BAOBAB retirée, pas un vestige)
    with pytest.raises(HTTPException):
        map_layers_geojson(kind="tcsp_axe", db=db_session, limit=100)


def test_fiche_drapeau_station_800m(db_session):
    _setup(db_session)
    bloc = _proximites_block(db_session, TEST_IDU)
    assert bloc and bloc.get("tcsp"), "la fiche doit porter la station TCSP la plus proche"
    tcsp = bloc["tcsp"]
    assert tcsp["sous_800m"] is True                       # station à ~310 m
    assert tcsp["station"] == "__test_tcsp_station__"
    # base légale vérifiée sur Légifrance : 800 m · 1 place · 0,5 LLS · qualité de desserte ·
    # le plafond S'IMPOSE (jamais « peut moduler ») mais rien d'autre n'est promis.
    assert "800 m" in tcsp["libelle"]
    assert "1 place" in tcsp["libelle"]
    assert "0,5" in tcsp["libelle"]
    assert "L151-36" in tcsp["libelle"]
    assert "qualité de la desserte" in tcsp["libelle"]
    assert "vol d'oiseau" in tcsp["source"]                # CE 2022 : depuis la station, à vol d'oiseau


def test_pas_de_faux_positif_stationnement(db_session):
    """Doctrine : le drapeau ne promet RIEN au-delà du texte — la condition de desserte est dite."""
    _setup(db_session)
    tcsp = _proximites_block(db_session, TEST_IDU)["tcsp"]
    bas = tcsp["libelle"].lower()
    assert "reste à instruire" in bas
    for interdit in ("réduction de stationnement garantie", "stationnement réduit", "moins de places obligatoire"):
        assert interdit not in bas
