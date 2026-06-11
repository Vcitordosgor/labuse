"""Tests industrialisation : auto-réconciliation du schéma, readiness, doctor, prepare-pilot.

Verrouille la distinction des 4 niveaux (app / schéma / données / démo) et le fait
qu'aucune commande ne masque un état dégradé (exit codes fiables + actions affichées).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from typer.testing import CliRunner

pytestmark = pytest.mark.db


# ───────────────────────── Schéma : auto-réconciliation ─────────────────────────

def test_ensure_schema_repare_colonne_trigger_index(engine):
    """Simule un recyclage (colonne/trigger/index perdus) → ensure_schema répare en s."""
    from labuse import models

    with engine.begin() as c:
        c.execute(text("ALTER TABLE pipeline_entries DROP COLUMN IF EXISTS prospection"))
        c.execute(text("DROP TRIGGER IF EXISTS trg_parcels_geom_2975 ON parcels"))
        c.execute(text("DROP INDEX IF EXISTS idx_dvf_geom_2975"))
    models.ensure_schema(engine)          # léger : aucune donnée recalculée
    with engine.connect() as c:
        assert c.execute(text(
            "SELECT count(*) FROM information_schema.columns "
            "WHERE table_name='pipeline_entries' AND column_name='prospection'")).scalar() == 1
        assert c.execute(text(
            "SELECT count(*) FROM pg_trigger WHERE tgname='trg_parcels_geom_2975'")).scalar() == 1
        assert c.execute(text(
            "SELECT count(*) FROM pg_indexes WHERE indexname='idx_dvf_geom_2975'")).scalar() == 1
    models.ensure_schema(engine)          # idempotent (rejouable sans erreur)


def test_schema_status_detecte_manque(engine, db_session):
    from labuse import state

    assert state.schema_status(db_session)["ok"] is True
    # un manque est détecté PRÉCISÉMENT (sans réparer : lecture seule)
    with engine.begin() as c:
        c.execute(text("DROP INDEX IF EXISTS idx_dvf_geom_2975"))
    try:
        missing = state.schema_status(db_session)["missing"]
        assert "index idx_dvf_geom_2975" in missing
    finally:
        from labuse import models
        models.ensure_schema(engine)      # remet l'état propre pour les tests suivants


# ───────────────────────── Données : readiness précis ─────────────────────────

def test_readiness_liste_precisement_ce_qui_manque(db_session):
    """Commune avec parcelles mais sans couches : chaque manque est nommé + action."""
    from labuse import state

    wkt = "POLYGON((55.30 -21.00,55.31 -21.00,55.31 -20.99,55.30 -20.99,55.30 -21.00))"
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom, surface_m2, centroid) VALUES "
        "('RD0000000000X1','Readyville', ST_GeomFromText(:w,4326), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)))"), {"w": wkt})
    st = state.readiness(db_session, "Readyville")
    assert st["ready"] is False
    for attendu in ("SAR", "PPR / aléas", "DVF geo-dvf", "OSM faux positifs", "évaluations (cascade)"):
        assert attendu in st["data"]["missing"], f"manque non détecté : {attendu}"
    assert any("rebuild-demo" in a for a in st["actions"])
    # commune inexistante → « parcelles » manquantes, pas un crash
    st2 = state.readiness(db_session, "CommuneFantome")
    assert st2["ready"] is False and any("parcelles" in m for m in st2["data"]["missing"])


# ───────────────────────── Endpoints santé/readiness ─────────────────────────

@pytest.fixture(scope="module")
def client(engine):
    from fastapi.testclient import TestClient
    from sqlalchemy import select

    from labuse import models
    from labuse.ai import StubProvider
    from labuse.api.app import app
    from labuse.cascade import evaluate_parcels
    from labuse.db import session_scope
    from labuse.ingestion import demo_saint_paul, seed_sources

    with session_scope() as s:
        seed_sources.seed(s)
        demo_saint_paul.seed_demo(s)
        ids = [r[0] for r in s.execute(select(models.Parcel.id)).all()]
        evaluate_parcels(ids, s, persist=True, ai_provider=StubProvider())
    try:
        yield TestClient(app)
    finally:
        with session_scope() as s:
            demo_saint_paul.reset_demo(s)


def test_healthz_sans_db(client):
    # Niveau 1 : le process répond — ne présume RIEN des données.
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_readyz_pret_sur_jeu_de_demo(client):
    # Le seed de démo fournit parcelles + SAR + PPR + OSM + DVF + évaluations → prêt.
    r = client.get("/readyz")
    assert r.status_code == 200
    js = r.json()
    assert js["ready"] is True and js["schema"]["ok"] is True and js["data"]["missing"] == []


def test_readyz_503_si_couche_critique_absente(client):
    from labuse.db import session_scope

    with session_scope() as s:   # retire le SAR (commit hors transaction de test)
        rows = s.execute(text(
            "SELECT id, kind, subtype, name, ST_AsText(geom), commune FROM spatial_layers "
            "WHERE kind='sar'")).all()
        s.execute(text("DELETE FROM spatial_layers WHERE kind='sar'"))
    try:
        r = client.get("/readyz")
        assert r.status_code == 503
        js = r.json()
        assert js["ready"] is False and "SAR" in js["data"]["missing"]
        assert any("rebuild-demo" in a for a in js["actions"])
    finally:
        with session_scope() as s:
            for _id, kind, subtype, name, wkt, commune in rows:
                s.execute(text(
                    "INSERT INTO spatial_layers (kind, subtype, name, geom, commune) VALUES "
                    "(:k,:st,:n, ST_GeomFromText(:w,4326), :c)"),
                    {"k": kind, "st": subtype, "n": name, "w": wkt, "c": commune})
    assert client.get("/readyz").status_code == 200      # état restauré


def test_demo_status_indique_ce_qui_manque(client):
    # Les parcelles de DÉMO réelles (BP0571…) n'existent pas sur le jeu synthétique →
    # demo-status doit le dire précisément, avec l'action à lancer (jamais masqué).
    r = client.get("/demo-status")
    assert r.status_code == 200
    js = r.json()
    assert {"healthcheck", "demo", "warm", "ready_for_demo", "actions", "checked_at"} <= set(js)
    assert js["demo"]["all_conform"] is False
    assert js["ready_for_demo"] is False
    assert any("rebuild-demo" in a for a in js["actions"])
    names = {c["name"] for c in js["healthcheck"]["checks"]}
    assert {"PPR", "SAR", "DVF geo-dvf", "Top 20 sans faux positif évident"} <= names


# ───────────────────────── CLI : doctor / warm-demo / prepare-pilot ─────────────────────────

def test_doctor_degrade_exit_1_avec_actions(engine):
    from labuse.cli import app as cli_app

    res = CliRunner().invoke(cli_app, ["doctor", "--commune", "CommuneFantome"])
    assert res.exit_code == 1
    assert "NON PRÊT" in res.output and "rebuild-demo" in res.output
    assert "Schéma réconcilié" in res.output            # le schéma, lui, est réparé (léger)


def test_warm_demo_echoue_si_parcelles_absentes(engine):
    from labuse.cli import app as cli_app

    res = CliRunner().invoke(cli_app, ["warm-demo", "--no-seed-pipeline"])
    assert res.exit_code == 1
    assert "ABSENTE" in res.output and "rebuild-demo" in res.output


def test_prepare_pilot_ne_passe_pas_si_healthcheck_echoue(engine):
    from labuse.cli import app as cli_app

    res = CliRunner().invoke(cli_app, ["prepare-pilot", "--skip-rebuild", "--commune", "97499"])
    assert res.exit_code == 1
    assert "rebuild-demo" in res.output                 # dit QUOI lancer, sans le faire en douce
