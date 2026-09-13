"""REPARATIONS-1 lot 4 — RNB, l'identité des bâtiments : tables + rattachement (causes
écrites), registre complet (source, réservoir, donnée, robinet, sentinelle, filtre), et le
bloc « Le bien » qui sert les identifiants sans jamais casser."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def test_registre_rnb_complet():
    from labuse.circuit_etats import NOM_VERS_SLUG
    from labuse.filtres import _registre
    from labuse.ingestion.seed_sources import MODE_ET_CADENCE, SOURCES
    from labuse.registre.donnees import DONNEES
    from labuse.registre.robinets import ROBINETS
    from labuse.registre.tables import RESERVOIR_TABLES
    from labuse.sentinelle import SEED

    nom = "RNB — Référentiel National des Bâtiments"
    assert any(r["name"] == nom for r in SOURCES), "source au catalogue"
    assert nom in MODE_ET_CADENCE
    assert NOM_VERS_SLUG[nom] == "rnb"
    assert "rnb_batiments" in RESERVOIR_TABLES["rnb"].tables
    d = DONNEES["rnb_batiments_liste"]
    assert d.reservoirs == ("rnb",) and d.niveau == "parcelle"
    assert "rnb_batiments_liste" in ROBINETS["fiche_parcelle_le_bien"].chiffres
    assert "rnb" in _registre(), "filtre déclaré"
    assert any(e["name"] == nom and e["methode"] == "temoin" for e in SEED), \
        "sentinelle témoin déclarée (le canal incrémental est /buildings/diff/)"


def test_rattachement_cause_ecrite(db_session):
    """Un bâtiment BD TOPO sans RNB intersectant porte une CAUSE, jamais un silence."""
    from labuse.ingestion.rnb import ensure_tables, mesurer, rattacher
    ensure_tables(db_session)
    db_session.execute(text("DELETE FROM rnb_rattachement_bdtopo"))
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = 'rnb-test-bati'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, name, geom, geom_2975) VALUES ('batiment', 'rnb-test-bati',"
        " ST_SetSRID(ST_GeomFromText('POLYGON((55.3 -21.0,55.3001 -21.0,55.3001 -21.0001,55.3 -21.0))'), 4326),"
        " ST_Transform(ST_SetSRID(ST_GeomFromText('POLYGON((55.3 -21.0,55.3001 -21.0,55.3001 -21.0001,55.3 -21.0))'), 4326), 2975))"))
    r = rattacher(db_session, log_fn=lambda *_: None)
    ligne = db_session.execute(text(
        "SELECT ra.cause FROM rnb_rattachement_bdtopo ra JOIN spatial_layers b ON b.id = ra.layer_id "
        "WHERE b.name = 'rnb-test-bati'")).scalar()
    assert ligne == "aucun_rnb_intersectant"
    assert "par_cause" in r["bdtopo"]


def test_rattachement_spatial_reussit(db_session):
    """Un RNB dont l'emprise recouvre le bâtiment est rattaché (recouvrement ≥ seuil)."""
    from labuse.ingestion.rnb import ensure_tables, rattacher
    ensure_tables(db_session)
    poly = "POLYGON((55.31 -21.01,55.3102 -21.01,55.3102 -21.0102,55.31 -21.0102,55.31 -21.01))"
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = 'rnb-test-bati2'"))
    db_session.execute(text("DELETE FROM rnb_batiments WHERE rnb_id = 'TESTRNB00001'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, name, geom, geom_2975) VALUES ('batiment', 'rnb-test-bati2',"
        f" ST_SetSRID(ST_GeomFromText('{poly}'), 4326),"
        f" ST_Transform(ST_SetSRID(ST_GeomFromText('{poly}'), 4326), 2975))"))
    db_session.execute(text(
        "INSERT INTO rnb_batiments (rnb_id, statut, is_active, insee, shape, shape_2975) VALUES"
        f" ('TESTRNB00001', 'constructed', true, '97411', ST_SetSRID(ST_GeomFromText('{poly}'), 4326),"
        f" ST_Transform(ST_SetSRID(ST_GeomFromText('{poly}'), 4326), 2975))"))
    rattacher(db_session, log_fn=lambda *_: None)
    row = db_session.execute(text(
        "SELECT ra.rnb_id, ra.recouvrement_pct FROM rnb_rattachement_bdtopo ra "
        "JOIN spatial_layers b ON b.id = ra.layer_id WHERE b.name = 'rnb-test-bati2'")).first()
    assert row is not None and row.rnb_id == "TESTRNB00001" and row.recouvrement_pct > 90


def test_le_bien_ne_casse_jamais_sans_rnb(db_session):
    """Base sans table RNB (ou vide) → le bloc « Le bien » sert rnb=[] — jamais un crash."""
    from labuse import bati
    idu = db_session.execute(text("SELECT idu FROM parcels LIMIT 1")).scalar()
    if idu is None:
        pytest.skip("base de test sans parcelle")
    b = bati.le_bien_block(db_session, idu)
    if b is not None:
        assert isinstance(b.get("rnb"), list)
