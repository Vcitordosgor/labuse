"""RETOURS-14 lot carte — les tests qui auraient attrapé les défauts S5 / S6 / S8.

S5 : un permis à parcelle disparue doit être rattaché par la GÉOMÉTRIE d'époque (jamais un
     point d'adresse sur une parcelle qui n'est pas la sienne) ; un repli d'adresse restant ne
     pose PAS de point (geom_approx, dit dans la liste).
S6 : la couche carte lit la géométrie simplifiée MATÉRIALISÉE (geom_simple) — la simplification
     à la volée (~11 s) laissait la couche muette au premier clic.
S8 : la zone « stationnement allégé » (rayon 800 m + parcelles couvertes) est servie.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.api.app import _MAP_LAYER_KINDS, map_layers_geojson

pytestmark = pytest.mark.db


def test_s5_rattachement_geometrique_et_etiquette(db_session):
    from labuse.ingestion.cadastre_historique import ensure_table, rattacher_par_geometrie
    ensure_table(db_session)
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '__test_s5__'"))
    db_session.execute(text("DELETE FROM cadastre_historique WHERE idu = '97411000ZY0001'"))
    db_session.execute(text("DELETE FROM parcels WHERE idu IN ('97411000ZY0002', '97411000ZY0003')"))
    # parcelle d'ORIGINE (disparue) au cadastre d'époque…
    db_session.execute(text(
        "INSERT INTO cadastre_historique (idu, millesime, geom) VALUES "
        "('97411000ZY0001', '2017-07-06', "
        " ST_SetSRID(ST_MakeEnvelope(55.00, -21.60, 55.002, -21.598), 4326))"))
    # …redécoupée en DEUX parcelles actuelles (chacune ~50 %)
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom, geom_2975) VALUES "
        "('97411000ZY0002', 'Saint-Denis', ST_SetSRID(ST_MakeEnvelope(55.00, -21.60, 55.001, -21.598), 4326), "
        " ST_Transform(ST_SetSRID(ST_MakeEnvelope(55.00, -21.60, 55.001, -21.598), 4326), 2975)), "
        "('97411000ZY0003', 'Saint-Denis', ST_SetSRID(ST_MakeEnvelope(55.001, -21.60, 55.002, -21.598), 4326), "
        " ST_Transform(ST_SetSRID(ST_MakeEnvelope(55.001, -21.60, 55.002, -21.598), 4326), 2975))"))
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw) VALUES "
        "('__test_s5__', 'PC', '2016-05-01', '[\"97411000ZY0001\"]'::jsonb, 'Saint-Denis', NULL, "
        " '{\"famille\": \"locaux\"}'::jsonb)"))
    rattacher_par_geometrie(db_session, log_fn=lambda *_: None)
    r = db_session.execute(text(
        "SELECT geom IS NOT NULL AS ok, raw->>'geoloc' AS geoloc, raw->'parcelles_actuelles' AS act, "
        "       (raw->>'origine_redecoupee')::bool AS redec "
        "FROM sitadel_permits WHERE permit_id = '__test_s5__'")).mappings().first()
    assert r["ok"], "le permis doit être posé sur sa parcelle d'origine"
    assert "parcelle d'origine" in r["geoloc"]          # provenance DITE
    assert r["redec"] is True                            # à cheval → étiqueté redécoupée
    assert set(json.loads(json.dumps(r["act"]))) == {"97411000ZY0002", "97411000ZY0003"}


def test_s5_repli_adresse_ne_pose_jamais_un_point(db_session):
    from labuse.ingestion.cadastre_historique import demoter_adresses_restantes
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '__test_s5b__'"))
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw) VALUES "
        "('__test_s5b__', 'PC', '2016-05-01', '[\"97411000ZY0009\"]'::jsonb, 'Saint-Denis', "
        " ST_SetSRID(ST_MakePoint(55.4, -20.9), 4326), "
        " CAST(:r AS jsonb))"),
        {"r": json.dumps({"geoloc": "adresse (BAN interne — parcelle du permis absente du cadastre courant)"})})
    demoter_adresses_restantes(db_session, log_fn=lambda *_: None)
    r = db_session.execute(text(
        "SELECT geom IS NULL AS sans_point, geom_approx IS NOT NULL AS memo, raw->>'geoloc' AS g "
        "FROM sitadel_permits WHERE permit_id = '__test_s5b__'")).mappings().first()
    assert r["sans_point"] and r["memo"]
    assert "approximative" in r["g"]                     # la liste le DIT


def test_s6_endpoint_lit_geom_simple(db_session):
    # la requête de couche doit lire geom_simple (matérialisée) — repli à la volée sinon
    import inspect
    src = inspect.getsource(map_layers_geojson)
    assert "geom_simple" in src


def test_s8_zone_stationnement_allege_servie(db_session):
    assert "tcsp_zone" in _MAP_LAYER_KINDS
    db_session.execute(text("DELETE FROM spatial_layers WHERE kind = 'tcsp_zone' AND name = '__test_s8__'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom) VALUES "
        "('tcsp_zone', 'parcelles', '__test_s8__', "
        " ST_SetSRID(ST_Buffer(ST_MakePoint(55.5, -21.0), 0.002), 4326))"))
    fc = map_layers_geojson(kind="tcsp_zone", db=db_session, limit=100)
    assert any(f["properties"]["name"] == "__test_s8__" for f in fc["features"])
