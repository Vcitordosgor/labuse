"""SCORING-3 · L2 — le feature store ne perd plus les zéros du résiduel.

Bug K3 (SCORING-2) : `p_model_static` n'était reconstruite qu'aux
rafraîchissements PLU/bâti — les zéros M125 de `parcel_residuel` (0 = réponse
du moteur, cause explicite) n'atteignaient jamais le dataset et ressortaient
« inconnus » (NULL). Le correctif L2 : `refresh_static_residuel`, appelé à
CHAQUE rebuild de features (pipeline.rebuild_features).

Ces tests ÉCHOUENT si une parcelle avec résiduel = 0 ressort « inconnue ».
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.scoring.p_model.sql import refresh_static_residuel


@pytest.fixture
def parc_residuel(db_session):
    """Trois parcelles : résiduel 0 (cause explicite), résiduel > 0, hors_plu
    (NULL, réellement inconnaissable) — et un feature store PÉRIMÉ (NULL partout)."""
    suffixe = uuid.uuid4().hex[:6].upper()
    idus = [f"97411000ZZ{i}{suffixe[:3]}" for i in range(3)]
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS p_model_static ("
        " idu varchar(14) PRIMARY KEY, pct_potentiel integer,"
        " sous_densite boolean, sdp_residuelle_m2 integer)"))
    db_session.execute(text(
        "CREATE TABLE IF NOT EXISTS parcel_residuel ("
        " parcel_id integer PRIMARY KEY REFERENCES parcels(id) ON DELETE CASCADE,"
        " taux_emprise_pct integer, pct_potentiel integer, sous_densite boolean,"
        " sdp_residuelle_m2 integer, capacite_estimee boolean,"
        " computed_at timestamptz NOT NULL DEFAULT now(), cause text)"))
    pids = []
    for idu in idus:
        pid = db_session.execute(text(
            "INSERT INTO parcels (idu, commune, geom, created_at, updated_at) "
            "VALUES (:idu, 'Saint-Paul', ST_GeomFromText('POINT(55.5 -21.1)', 4326), "
            "now(), now()) RETURNING id"), {"idu": idu}).scalar()
        pids.append(pid)
    donnees = [
        (pids[0], 0, False, "zone_non_constructible:N"),   # 0 = réponse du moteur
        (pids[1], 320, True, None),                        # calculée
        (pids[2], None, None, "hors_plu"),                 # réellement inconnaissable
    ]
    for pid, sdp, sd, cause in donnees:
        db_session.execute(text(
            "INSERT INTO parcel_residuel (parcel_id, sdp_residuelle_m2, sous_densite, cause) "
            "VALUES (:p, :s, :d, :c)"), {"p": pid, "s": sdp, "d": sd, "c": cause})
        # le feature store PÉRIMÉ : la parcelle y est, mais tout est NULL (le bug)
    for idu in idus:
        db_session.execute(text(
            "INSERT INTO p_model_static (idu, pct_potentiel, sous_densite, sdp_residuelle_m2) "
            "VALUES (:i, NULL, NULL, NULL) ON CONFLICT (idu) DO UPDATE "
            "SET pct_potentiel = NULL, sous_densite = NULL, sdp_residuelle_m2 = NULL"),
            {"i": idu})
    return idus


def _store(db_session, idu: str):
    return db_session.execute(text(
        "SELECT sdp_residuelle_m2, sous_densite FROM p_model_static WHERE idu = :i"),
        {"i": idu}).first()


def test_residuel_zero_ne_ressort_jamais_inconnu(db_session, parc_residuel):
    """LE test du mandat : résiduel = 0 → le store dit 0, JAMAIS « inconnue »."""
    idus = parc_residuel
    # avant correctif : le store est NULL (le bug reproduit)
    assert _store(db_session, idus[0])[0] is None
    n = refresh_static_residuel(db_session)
    assert n >= 2, f"rafraîchissement attendu sur au moins 2 lignes, obtenu {n}"
    # 0 = réponse du moteur — porté au store
    sdp0, sd0 = _store(db_session, idus[0])
    assert sdp0 == 0 and sd0 is False, "résiduel 0 ressort « inconnue » — bug K3 de retour"
    # > 0 porté aussi
    sdp1, sd1 = _store(db_session, idus[1])
    assert sdp1 == 320 and sd1 is True
    # hors_plu : NULL LÉGITIME (réellement inconnaissable) — pas un faux zéro
    assert _store(db_session, idus[2])[0] is None


def test_refresh_idempotent(db_session, parc_residuel):
    refresh_static_residuel(db_session)
    assert refresh_static_residuel(db_session) == 0, \
        "un second passage ne doit rien réécrire (UPDATE ciblé sur les écarts)"


def test_refresh_sans_tables_ne_casse_pas(db_session):
    """Bases de test sans feature store : no-op silencieux (0), jamais une erreur."""
    db_session.execute(text("DROP TABLE IF EXISTS p_model_static"))
    assert refresh_static_residuel(db_session) == 0
