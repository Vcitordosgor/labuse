"""CIRCUIT-1 lot 8 — les horloges honnêtes : un seul jeu de crons (wrapper), healthz depuis
le REGISTRE des jobs (jamais une table à la main), trace circuit_journal des jobs qui
touchent l'eau, état « à vérifier » par cadence attendue."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.db


def test_81_registre_bodacc_entre_bdnb_sorti():
    from labuse.jobs import JOBS, TOUCHE_EAU
    assert "ingest-bodacc" in JOBS and JOBS["ingest-bodacc"].cadence == "quotidien"
    assert "ingest-bdnb" not in JOBS, "retiré : l'amont BDNB ne couvre pas le 974"
    assert "ingest-bodacc" in TOUCHE_EAU and "coherence-robinets" in TOUCHE_EAU


def test_81_crontab_wrapper_complet():
    """Le crontab versionné pose TOUS les jobs du registre (plus aucun « enregistré mais
    jamais posé » — constat CIRCUIT-0) et ne pose rien d'inconnu."""
    from pathlib import Path
    from labuse.jobs import JOBS
    lignes = Path("deploy/cron.d-labuse").read_text(encoding="utf-8")
    poses = set()
    for l in lignes.splitlines():
        if "jobs run" in l and not l.strip().startswith("#"):
            poses.add(l.split("jobs run ")[1].split("'")[0].strip())
    # agents-sources : EXISTE au registre mais reste DÉSACTIVÉ (jamais posé — décision Vic n° 8)
    attendu = set(JOBS) - {"agents-sources"}
    assert poses == attendu, f"écart crontab/registre : {poses ^ attendu}"


def test_82_healthz_cadences_du_registre():
    from labuse.api import ops
    from labuse.jobs import JOBS
    # une entrée par job qui touche l'eau (+ backup), attendu dérivé de la cadence — jamais à la main
    assert "ingest-bodacc" in ops.CRONS and ops.CRONS["ingest-bodacc"]["attendu_jours"] == 2
    assert ops.CRONS["ingest-dpe"]["attendu_jours"] == 35, "DPE = mensuel (plus le mensonge hebdo)"
    for nom in ops.CRONS:
        assert nom in JOBS, f"{nom} n'existe pas au registre des jobs"


def test_83_trace_jobs_eau(db_session, monkeypatch, tmp_path):
    """Un job qui touche l'eau laisse sa ligne circuit_journal (quoi, quand, résultat)."""
    from sqlalchemy import text
    from labuse import circuit_journal
    circuit_journal.journaliser(db_session, "job", "sources-fraicheur", "cron", "ok",
                                {"duree_s": 1.2, "compteurs": {"maj": 3}})
    row = db_session.execute(text(
        "SELECT par, resultat, details FROM circuit_journal WHERE geste='job' "
        "AND cible='sources-fraicheur' ORDER BY id DESC LIMIT 1")).mappings().first()
    assert row["par"] == "cron" and row["resultat"] == "ok"
    assert row["details"]["compteurs"]["maj"] == 3


def test_84_a_verifier_cadence_depassee(db_session, engine):
    """8.4 — une source dont le dernier contrôle est plus vieux que sa cadence attendue passe
    « à vérifier » sur la page Circuit."""
    import uuid
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from labuse.api.app import app
    from labuse.api.dashboard import router
    if not any(getattr(r, "path", "") == "/admin/circuit" for r in app.routes):
        app.include_router(router)
    nom = f"Source cadence {uuid.uuid4().hex[:6]}"
    with engine.begin() as c:
        c.execute(text(
            "INSERT INTO data_sources (name, status, mode_remplissage, cadence_attendue_jours,"
            " cadence_statut, last_sync_at) VALUES (:n, 'connecte', 'one_shot', 30, 'proposee',"
            " now() - interval '90 days')"), {"n": nom})
    try:
        d = TestClient(app).get("/admin/circuit").json()
        r = next(x for x in d["reservoirs"] if x["nom"] == nom)
        assert r["a_verifier"] is True
        assert d["compteurs"]["a_verifier"] >= 1
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM data_sources WHERE name = :n"), {"n": nom})
