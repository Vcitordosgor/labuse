"""RETOURS-21 Lot A — l'aléa mouvement de terrain servi au BON niveau.

Le mapping R6 (ELEVE/TRES_ELEVE = « fort ») était juste dans le code, mais la donnée SERVIE
gardait `niveau='moyen'` (ingérée avant le correctif) : le score en héritait, et le filtre
CIRCUIT-3 mettait `georisques_mvt` en quarantaine. `reclassifier_alea_niveau` réaligne la donnée
sur le mapping, sans re-tirer le WFS, à l'identique d'une ré-ingestion, et de façon idempotente.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.layers_ingest import reclassifier_alea_niveau

pytestmark = pytest.mark.db


def test_reclassifier_realigne_eleve_sur_fort(db_session):
    db_session.execute(text("DELETE FROM spatial_layers WHERE name LIKE '__r21_alea_%'"))
    # une zone périmée (ELEVE servie « moyen ») + une déjà alignée (MOYEN=moyen)
    for name, attrs in [
        ("__r21_alea_grave__", {"niveau": "moyen", "classe": "eleve", "degre": "ELEVE"}),
        ("__r21_alea_moyen__", {"niveau": "moyen", "classe": "moyen", "degre": "MOYEN"}),
    ]:
        db_session.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
            "('georisque_alea', 'mouvement_terrain', :n, "
            " ST_SetSRID(ST_Buffer(ST_MakePoint(55.5, -21.0), 0.001), 4326), CAST(:a AS jsonb))"),
            {"n": name, "a": json.dumps(attrs)})
    reclassifier_alea_niveau(db_session, log_fn=lambda *_: None)
    grave = db_session.execute(text(
        "SELECT attrs->>'niveau', attrs->>'classe' FROM spatial_layers WHERE name='__r21_alea_grave__'")).first()
    assert grave == ("fort", "eleve")   # niveau de cascade réaligné, classe d'affichage conservée
    moyen = db_session.execute(text(
        "SELECT attrs->>'niveau' FROM spatial_layers WHERE name='__r21_alea_moyen__'")).scalar()
    assert moyen == "moyen"             # une zone déjà juste n'est pas touchée
    db_session.execute(text("DELETE FROM spatial_layers WHERE name LIKE '__r21_alea_%'"))


def test_reclassifier_idempotent(db_session):
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = '__r21_alea_idem__'"))
    db_session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('georisque_alea', 'mouvement_terrain', '__r21_alea_idem__', "
        " ST_SetSRID(ST_Buffer(ST_MakePoint(55.5, -21.0), 0.001), 4326), CAST(:a AS jsonb))"),
        {"a": json.dumps({"niveau": "moyen", "classe": "tres_eleve", "degre": "TRES_ELEVE"})})
    reclassifier_alea_niveau(db_session, log_fn=lambda *_: None)
    # rejouer ne change plus rien : le second passage ne touche AUCUNE des zones de test
    res = reclassifier_alea_niveau(db_session, log_fn=lambda *_: None)
    touche = db_session.execute(text(
        "SELECT attrs->>'niveau' FROM spatial_layers WHERE name='__r21_alea_idem__'")).scalar()
    assert touche == "fort"
    assert "__r21_alea_idem__" not in json.dumps(res)  # pas dans le rapport du 2e passage
    db_session.execute(text("DELETE FROM spatial_layers WHERE name = '__r21_alea_idem__'"))
