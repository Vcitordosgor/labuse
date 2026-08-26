"""DASHBOARD-V1 — Tour de contrôle. D1 : capteurs (usage, retours, ia par compte, quota licence)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse import config
    from labuse.api import dashboard
    from labuse.api.app import app
    dashboard.ensure_tables(engine)
    with engine.begin() as c:
        c.execute(text("DELETE FROM usage_events"))
        c.execute(text("DELETE FROM retours"))
    config.get_settings.cache_clear()
    yield TestClient(app, base_url="https://testserver")
    config.get_settings.cache_clear()


def test_usage_event_compte_et_agregat(client, engine):
    """D1 — capteur d'usage : l'ouverture d'outil s'enregistre ; un kind inconnu → 422 (contrat)."""
    r = client.post("/usage/event", json={"kind": "outil", "outil": "courrier"})
    assert r.status_code == 200 and r.json()["ok"] is True
    r = client.post("/usage/event", json={"kind": "heartbeat"})
    assert r.status_code == 200
    with engine.begin() as c:
        rows = c.execute(text("SELECT kind, outil FROM usage_events ORDER BY id")).all()
    assert [tuple(x) for x in rows] == [("outil", "courrier"), ("heartbeat", None)]
    assert client.post("/usage/event", json={"kind": "n_importe_quoi"}).status_code == 422


def test_retour_signaler(client, engine):
    """D1 — bouton « Signaler » : le retour s'enregistre statut 'nouveau' ; type invalide → 422."""
    r = client.post("/retours", json={"type": "bug", "message": "L'export CSV est lent."})
    assert r.status_code == 200 and r.json()["ok"] is True
    with engine.begin() as c:
        row = c.execute(text("SELECT type, message, statut FROM retours")).one()
    assert tuple(row) == ("bug", "L'export CSV est lent.", "nouveau")
    assert client.post("/retours", json={"type": "troll", "message": "xxx"}).status_code == 422
    assert client.post("/retours", json={"type": "bug", "message": "x"}).status_code == 422


def test_ia_log_attribue_au_compte(client, engine):
    """D1 — ia_budget : le coût IA est attribué au compte posé par la garde d'auth (ContextVar)."""
    from labuse.ai import core
    from labuse.db import session_scope
    with engine.begin() as c:
        c.execute(text("DELETE FROM ia_log"))
    core.poser_compte(4242)
    try:
        with session_scope() as s:
            core._log_cost(s, kind="test_d1", model=core.MODEL_FACTUAL, stub=False, tin=1000, tout=100)
    finally:
        core.poser_compte(None)
    with engine.begin() as c:
        row = c.execute(text("SELECT compte_id, cout_eur FROM ia_log WHERE kind = 'test_d1'")).one()
    assert row[0] == 4242 and float(row[1]) > 0


def test_stripe_lecture_non_configure(client, monkeypatch):
    """D2 — sans clé restreinte : mode « non configuré » PROPRE (aucun crash, raison servie)."""
    from labuse import config, stripe_lecture
    monkeypatch.delenv("LABUSE_STRIPE_RESTRICTED_KEY", raising=False)
    monkeypatch.delenv("STRIPE_RESTRICTED_KEY", raising=False)
    config.get_settings.cache_clear()
    stripe_lecture.vider_cache()
    r = client.get("/admin/stripe")
    assert r.status_code == 200
    d = r.json()
    assert d["configure"] is False and "restreinte" in d["raison"].lower() or "LABUSE_STRIPE" in d["raison"]


def test_admin_stripe_exige_session_hors_local(client, monkeypatch):
    """D2 — hors mode local, /admin/stripe sans session → 401 (le gate admin est actif)."""
    monkeypatch.setenv("LABUSE_ENV", "pilot")
    monkeypatch.setenv("LABUSE_AUTH_PASSWORD", "sha256:" + "0" * 64)
    from labuse import config
    config.get_settings.cache_clear()
    try:
        assert client.get("/admin/stripe").status_code == 401
    finally:
        config.get_settings.cache_clear()


def test_quota_copilote_par_licence(client, engine):
    """D1 — quota Copilote PAR LICENCE : override du compte sinon défaut config (80/jour)."""
    from labuse.api.dashboard import quota_nl_du_compte
    from labuse.comptes import ensure_tables as comptes_ens
    from labuse.db import session_scope
    with session_scope() as s:
        comptes_ens(s)
    with engine.begin() as c:
        cid = c.execute(text(
            "INSERT INTO comptes (nom, plan, statut) VALUES ('Test D1', 'integral', 'actif') RETURNING id"
        )).scalar_one()
        c.execute(text("UPDATE comptes SET copilote_quota_jour = 5 WHERE id = :c"), {"c": cid})
    try:
        assert quota_nl_du_compte(cid) == 5                       # override licence
        with engine.begin() as c:
            c.execute(text("UPDATE comptes SET copilote_quota_jour = NULL WHERE id = :c"), {"c": cid})
        assert quota_nl_du_compte(cid) == 80                      # défaut config (mandat)
        assert quota_nl_du_compte(None) is None                   # pilote/anonyme → quota historique
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM comptes WHERE id = :c"), {"c": cid})
