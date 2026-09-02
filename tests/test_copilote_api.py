"""SUITE-1 S9 — API des MISSIONS LOURDES du Copilote (v2) : runs, SSE (reconnexion after_seq),
quota UNIFIÉ ACTIF, cloison. Endpoints sous `/api/copilote-v2/runs*` (les URL v1 `/api/copilote/*`
n'existent plus).

Le quota est testé HORS dev mode : quota atteint → 429 honnête, AUCUN run créé, AUCUN moteur appelé —
le chemin quota est exercé tel qu'en prod. Le plafond v1 distinct (kind 'agent', `copilote_quota_jour`)
a DISPARU : le run compte sur le MÊME compteur que `/ask` (`quota_du_compte` + `QUOTA_COPILOTE_KIND`,
kind 'copilote' ; bucket pilote → défaut `nl_quota_jour`). L'exécuteur est neutralisé (demarrer_run
mocké) : on teste l'API et l'event log, pas les moteurs (couverts par test_copilote_executeur).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from labuse import config
from labuse.copilote import events as ev


@pytest.fixture
def client(engine, monkeypatch):
    from labuse.api import copilote as api_cop
    from labuse.api.app import app
    from labuse.api.protection import ensure_tables as _prot_ens
    _prot_ens(engine)                                 # usage_compteurs (quota UNIFIÉ kind='copilote')
    lances: list[str] = []
    monkeypatch.setattr(api_cop, "demarrer_run", lambda rid: lances.append(rid))
    c = TestClient(app)
    c.lances = lances
    try:
        yield c
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM agent_runs WHERE brief_raw LIKE 'test-api%'"))


def _session(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)()


# ───────────────────────── création / listing / détail ─────────────────────────

@pytest.mark.db
def test_post_run_cree_run_started_et_plan_fige(client, engine):
    r = client.post("/api/copilote-v2/runs",
                    json={"mission": "instruire", "brief_raw": "test-api 6 logements"})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    assert client.lances == [run_id]                  # l'exécuteur est bien sollicité
    s = _session(engine)
    try:
        evts = ev.events_after(s, run_id, 0)
        assert [e["kind"] for e in evts] == ["run_started"]
        assert evts[0]["payload"]["plan"][0] == {"moteur": "criblage", "bloquant": True}
        versions = s.execute(text(
            "SELECT engine_versions FROM agent_runs WHERE id = CAST(:r AS uuid)"),
            {"r": run_id}).scalar()
        # §7-J : le run servi épinglé est gravé pour la reproductibilité (GO Q3).
        assert versions["run_servi"] and versions["rules_version"]
        assert versions["prompt_interpreteur"]
    finally:
        s.close()


@pytest.mark.db
def test_mission_inconnue_422(client):
    r = client.post("/api/copilote-v2/runs",
                    json={"mission": "dominer", "brief_raw": "test-api x"})
    assert r.status_code == 422 and "instruire" in r.json()["detail"]


@pytest.mark.db
def test_liste_et_detail_derives_de_l_event_log(client, engine):
    run_id = client.post("/api/copilote-v2/runs", json={
        "mission": "shortlist", "brief_raw": "test-api shortlist"}).json()["run_id"]
    s = _session(engine)
    try:
        ev.emit(s, run_id, "brief_parsed", {"brief_json": {}})
        ev.emit(s, run_id, "run_completed", {"n_retenues": 0, "n_ecartees": 0})
    finally:
        s.close()
    liste = client.get("/api/copilote-v2/runs").json()["runs"]
    assert any(x["run_id"] == run_id and x["status"] == "done" for x in liste)
    detail = client.get(f"/api/copilote-v2/runs/{run_id}").json()
    assert detail["status"] == "done"
    assert detail["recap"]["n_retenues"] == 0
    assert detail["n_events"] == 3


# ───────────────────────── SSE : rejeu + reconnexion after_seq ─────────────────────────

@pytest.mark.db
def test_sse_rejoue_puis_reconnecte_sans_doublon_ni_trou(client, engine):
    run_id = client.post("/api/copilote-v2/runs", json={
        "mission": "instruire", "brief_raw": "test-api sse"}).json()["run_id"]
    s = _session(engine)
    try:
        ev.emit(s, run_id, "brief_parsed", {"brief_json": {}})
        ev.emit(s, run_id, "step_started", {"moteur": "criblage"})
        ev.emit(s, run_id, "run_completed", {"n_retenues": 0, "n_ecartees": 0})
    finally:
        s.close()

    def _lire(url):
        seqs, kinds = [], []
        with client.stream("GET", url) as r:
            assert r.headers["content-type"].startswith("text/event-stream")
            data = "".join(r.iter_text())
        for bloc in data.strip().split("\n\n"):
            champs = dict(ligne.split(": ", 1) for ligne in bloc.splitlines() if ": " in ligne)
            if champs.get("event") == "fin":
                continue
            seqs.append(int(champs["id"]))
            kinds.append(champs["event"])
        return seqs, kinds, data

    # Rejeu complet (after_seq=0) : run terminal → le flux se ferme après le rejeu.
    seqs, kinds, _ = _lire(f"/api/copilote-v2/runs/{run_id}/events")
    assert seqs == [1, 2, 3, 4]                     # ni doublon ni trou
    assert kinds == ["run_started", "brief_parsed", "step_started", "run_completed"]

    # Reconnexion en plein milieu : exactement la suite, jamais l'avant.
    seqs2, kinds2, brut = _lire(f"/api/copilote-v2/runs/{run_id}/events?after_seq=2")
    assert seqs2 == [3, 4] and kinds2 == ["step_started", "run_completed"]
    assert "run_started" not in kinds2
    assert '"status": "done"' in brut               # événement de fin explicite


# ───────────────────────── quota ACTIF (hors dev mode — exigence GO) ────────────────────

@pytest.mark.db
def test_quota_actif_429_honnete_aucun_run_aucun_moteur(client, engine, monkeypatch):
    s = config.get_settings()
    monkeypatch.setattr(s, "dev_mode", False)
    monkeypatch.setattr(s, "nl_quota_jour", 1)        # bucket pilote → défaut nl_quota_jour (quota UNIFIÉ)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM usage_compteurs WHERE kind = 'copilote'"))
    avant_runs = client.lances[:]

    ok = client.post("/api/copilote-v2/runs",
                     json={"mission": "instruire", "brief_raw": "test-api quota 1"})
    assert ok.status_code == 200                     # 1er run du jour : passe

    refus = client.post("/api/copilote-v2/runs",
                        json={"mission": "instruire", "brief_raw": "test-api quota 2"})
    assert refus.status_code == 429
    corps = refus.json()
    assert corps["quota"] == 1 and corps["gel_jusqua"] == "minuit"
    assert "Quota Copilote atteint" in corps["detail"]

    with engine.connect() as conn:
        n_runs = conn.execute(text(
            "SELECT count(*) FROM agent_runs WHERE brief_raw = 'test-api quota 2'")).scalar()
        assert n_runs == 0                           # AUCUN run créé (donc pas de run_started)
    assert len(client.lances) == len(avant_runs) + 1  # AUCUN moteur lancé pour le refus


@pytest.mark.db
def test_quota_compte_sur_le_scope_du_run(client, engine, monkeypatch):
    # S9 : le quota est compté sur le MÊME scope que la propriété du run — en mode
    # pilote (compte NULL), sujet session/IP ; le kind UNIFIÉ est 'copilote' (le même que /ask).
    s = config.get_settings()
    monkeypatch.setattr(s, "dev_mode", False)
    monkeypatch.setattr(s, "nl_quota_jour", 10)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM usage_compteurs WHERE kind = 'copilote'"))
    client.post("/api/copilote-v2/runs",
                json={"mission": "instruire", "brief_raw": "test-api scope"})
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT sujet, n FROM usage_compteurs WHERE kind = 'copilote'")).all()
    assert len(rows) == 1 and rows[0][1] == 1


# ───────────────────────── clarification / annulation / cloison ─────────────────────────

@pytest.mark.db
def test_answer_reprend_un_run_awaiting_user(client, engine):
    run_id = client.post("/api/copilote-v2/runs", json={
        "mission": "instruire", "brief_raw": "test-api clarif"}).json()["run_id"]
    s = _session(engine)
    try:
        ev.emit(s, run_id, "clarification_requested",
                {"question": "Quelle commune ?", "champ_manquant": "communes"})
    finally:
        s.close()
    detail = client.get(f"/api/copilote-v2/runs/{run_id}").json()
    assert detail["status"] == "awaiting_user"
    assert detail["clarification"]["champ_manquant"] == "communes"

    n_avant = len(client.lances)
    r = client.post(f"/api/copilote-v2/runs/{run_id}/answer", json={"reponse": "Saint-Paul"})
    assert r.status_code == 200
    assert len(client.lances) == n_avant + 1        # l'exécuteur repart
    s = _session(engine)
    try:
        evts = ev.events_after(s, run_id, 0)
        assert evts[-1]["kind"] == "clarification_answered"
        assert evts[-1]["payload"]["reponse"] == "Saint-Paul"
    finally:
        s.close()


@pytest.mark.db
def test_answer_refuse_si_pas_awaiting(client):
    run_id = client.post("/api/copilote-v2/runs", json={
        "mission": "instruire", "brief_raw": "test-api pas-attente"}).json()["run_id"]
    r = client.post(f"/api/copilote-v2/runs/{run_id}/answer", json={"reponse": "x"})
    assert r.status_code == 409


@pytest.mark.db
def test_cancel_emet_run_cancelled(client, engine):
    run_id = client.post("/api/copilote-v2/runs", json={
        "mission": "instruire", "brief_raw": "test-api cancel"}).json()["run_id"]
    r = client.post(f"/api/copilote-v2/runs/{run_id}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    s = _session(engine)
    try:
        assert ev.run_status(s, run_id) == "cancelled"
    finally:
        s.close()
    # Un second cancel → 409 (déjà terminal), jamais un double événement.
    assert client.post(f"/api/copilote-v2/runs/{run_id}/cancel").status_code == 409


@pytest.mark.db
def test_cloison_aucun_acces_croise(client, engine):
    # Un run appartenant à un AUTRE compte est invisible (404, jamais 403 bavard).
    s = _session(engine)
    try:
        cid = s.execute(text("SELECT id FROM comptes WHERE nom = 'c-test' LIMIT 1")).scalar()
        if cid is None:
            cid = s.execute(text("INSERT INTO comptes (nom, plan, statut) VALUES "
                                 "('c-test', 'integral', 'actif') RETURNING id")).scalar()
        autre = s.execute(text(
            "INSERT INTO agent_runs (compte_id, mission, brief_raw) "
            "VALUES (:c, 'instruire', 'test-api prive') RETURNING id::text"),
            {"c": cid}).scalar_one()
        s.commit()
    finally:
        s.close()
    # Le client de test n'a pas de session compte → cid NULL ≠ compte du run.
    assert client.get(f"/api/copilote-v2/runs/{autre}").status_code == 404
    assert client.post(f"/api/copilote-v2/runs/{autre}/cancel").status_code == 404
    ids = [x["run_id"] for x in client.get("/api/copilote-v2/runs").json()["runs"]]
    assert autre not in ids
