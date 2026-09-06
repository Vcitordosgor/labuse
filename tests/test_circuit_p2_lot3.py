"""CIRCUIT-P2 lot 3 — les commandes qui répondent. Chaque geste long prouve trois choses :
l'endpoint est appelé, une ligne circuit_journal est écrite avec « qui », et l'état d'écran change
(tâche/progression). Le bouton agents n'est jamais grisé sans mot (cas sans crédit testé)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_taches as T


# ── 3.2/3.3 — le module de tâches (progression file-based, pur) ────────────────────────────────
def test_taches_cycle(tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    T.demarrer("verifier", total=5, par="vic@test", message="Contrôle en cours…")
    assert T.en_cours("verifier")
    T.avancer("verifier", fait=3, message="Eau ancienne — 3 / 5")
    d = T.lire("verifier")
    assert d["fait"] == 3 and d["etat"] == "en_cours" and d["par"] == "vic@test"
    T.terminer("verifier", message="Contrôle terminé : 0 fuite.", resultat={"fuites_ouvertes": 0})
    d = T.lire("verifier")
    assert d["etat"] == "termine" and d["fait"] == 5 and d["resultat"]["fuites_ouvertes"] == 0
    assert not T.en_cours("verifier")


def test_reservoirs_en_route(tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    T.demarrer("agents", total=3, par="système", message="0 / 3")
    T.avancer("agents", fait=1, en_route=[7, 42], message="1 / 3 agents revenus")
    assert T.reservoirs_en_route() == {7, 42}
    T.terminer("agents", message="3 agent(s) revenu(s).")
    assert T.reservoirs_en_route() == set()      # plus aucun une fois terminé


# ── endpoints (DB) ────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


@pytest.fixture
def seed(engine):
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)


@pytest.mark.db
def test_verifier_lance_tache_et_journal(client, seed, engine, tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    from labuse.api.dashboard import _executer_controle
    # l'endpoint rend la main tout de suite (tâche détachée)
    r = client.post("/admin/circuit/verifier").json()
    assert r["ok"] and (r.get("lance") or r.get("deja"))
    # on exécute le contrôle DIRECTEMENT (déterministe) : tâche terminée + journal « contrôle » + qui
    _executer_controle("vic@test")
    d = T.lire("verifier")
    assert d["etat"] == "termine" and "Contrôle terminé" in d["message"]
    with engine.begin() as c:
        row = c.execute(text(
            "SELECT par, geste FROM circuit_journal WHERE geste = 'controle'"
            " ORDER BY id DESC LIMIT 1")).mappings().first()
    assert row and row["par"] == "vic@test"


@pytest.mark.db
def test_agents_sans_credit_message_clair(client, seed, monkeypatch):
    monkeypatch.setattr("labuse.ai.core.has_key", lambda: False)
    r = client.post("/admin/circuit/agents").json()
    assert r["ok"] is False and r["credit"] is False
    assert "Crédit API" in r["message"]          # jamais grisé sans explication


@pytest.mark.db
def test_agents_avec_credit_journalise(client, seed, engine, tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    monkeypatch.setattr("labuse.ai.core.has_key", lambda: True)
    from labuse.api.dashboard import _executer_agents
    # deux réservoirs cibles quelconques (non surveillés → l'agent journalise « sans_sonde », sans réseau)
    circ = client.get("/admin/circuit").json()
    ids = [circ["reservoirs"][0]["id"], circ["reservoirs"][1]["id"]]
    noms = {r["id"]: r["nom"] for r in circ["reservoirs"] if r["id"] in ids}
    _executer_agents("vic@test", ids, noms)
    d = T.lire("agents")
    assert d["etat"] == "termine" and d["resultat"]["n"] == 2
    with engine.begin() as c:
        n = c.execute(text(
            "SELECT count(*) FROM circuit_journal WHERE geste = 'agent' AND par = 'vic@test'"
        )).scalar()
    assert n >= 2


@pytest.mark.db
def test_agent_en_route_peint_mauve(client, seed, engine, tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    circ = client.get("/admin/circuit").json()
    cible = circ["reservoirs"][0]["id"]
    # une tâche agents en cours, ce réservoir « en route » → il passe mauve dans /admin/circuit
    T.demarrer("agents", total=1, par="système", message="0 / 1")
    T.avancer("agents", fait=0, en_route=[cible], message="0 / 1 agents revenus")
    circ2 = client.get("/admin/circuit").json()
    r = next(x for x in circ2["reservoirs"] if x["id"] == cible)
    assert r["etat"] == ["mauve", "agent en route"]
    T.terminer("agents", message="fini")
