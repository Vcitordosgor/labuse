"""CIRCUIT-1 lot 5 — la page Circuit : l'endpoint unique, la vanne étendue, les gestes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

pytestmark = pytest.mark.db


@pytest.fixture
def client(engine):
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    return TestClient(app)


def test_51_circuit_un_appel_structure_complete(client, engine):
    # les colonnes 1.7 se posent sur une connexion AUTONOME (autocommit) — un ALTER dans la
    # transaction-savepoint du fixture db_session garderait un verrou ACCESS EXCLUSIVE sur
    # data_sources et bloquerait la connexion propre de l'endpoint (timeout 600 s, constaté).
    from labuse.ingestion.seed_sources import appliquer_modes_cadences
    with engine.begin() as c:
        appliquer_modes_cadences(c)
    d = client.get("/admin/circuit").json()
    assert set(d) >= {"run_servi", "manifeste", "reservoirs", "robinets", "chiffres",
                      "aretes", "fuites", "eau_ancienne", "compteurs", "runs", "residuel"}
    c = d["compteurs"]
    assert c["robinets"] >= 120 and c["chiffres"] >= 96
    assert c["vannes"] >= 1
    # chaque réservoir DIT sa vanne (injecter / depot / aucune+motif) — décision Vic n° 6
    for r in d["reservoirs"]:
        assert r["vanne"]["type"] in ("injecter", "depot", "aucune")
        if r["vanne"]["type"] == "aucune":
            assert r["vanne"]["motif"]
    assert d["manifeste"]["scoring_run"]


def test_53_vanne_etendue_33_commandes():
    """5.3 — le YAML porte les 5 motifs historiques + l'extension (motifs exacts, labels uniques)."""
    import yaml
    d = yaml.safe_load(open("config/sources_ingestion.yaml"))
    labels = [c["label"] for c in d["commandes"]]
    assert len(labels) == len(set(labels))
    assert len(labels) >= 30
    assert "georisques_api" in labels and "cosia" in labels and "sitadel" in labels


def test_55_verifier_bouton(client):
    # CIRCUIT-P2 (lot 3.2) — le bouton lance une TÂCHE détachée : la réponse dit « lancé » (ou
    # « déjà en cours »), le résultat/verdict arrive via /admin/circuit/taches.
    d = client.post("/admin/circuit/verifier").json()
    assert d["ok"] and (d.get("lance") or d.get("deja"))
    t = client.get("/admin/circuit/taches").json()
    assert "verifier" in t


def test_54_purger_dry_run(client):
    d = client.post("/admin/circuit/purger-runs").json()
    assert "purgeables" in d and "garder" in d
    assert "Dry-run" in d["note"]


def test_54_note_version(client, monkeypatch):
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_servi_l5")
    d = client.get("/admin/circuit/note-version?candidat=q_cand_l5").json()
    assert d["candidat"] == "q_cand_l5" and "chiffres_recalcules" in d
