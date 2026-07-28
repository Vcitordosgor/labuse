"""M26-A — exécuteur : retry unique, bloquant/non-bloquant, budgets, zéro retenue.

Moteurs MOCKÉS (monkeypatch de moteurs.MOTEURS) — aucun moteur réel appelé ici ;
l'exécution est appelée en synchrone (pas de thread) pour des assertions déterministes.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from labuse import config
from labuse.copilote import events as ev
from labuse.copilote import executeur, moteurs

BRIEF = {"communes": ["Saint-Paul"], "programme": {"logements": 6, "sdp_cible_m2": 420.0},
         "budget_max_eur": None,
         "contraintes": {"exclure_ppr_rouge": True, "exclure_abf": False, "zones": None},
         "surface_min_m2": None}


@pytest.fixture
def run_pret(engine):
    """Run avec brief déjà validé + run_started portant un plan FIGÉ à 2 étapes mockées."""
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw, brief_json) "
        "VALUES ('instruire', 'test', CAST(:b AS jsonb)) RETURNING id::text"),
        {"b": json.dumps(BRIEF)}).scalar_one()
    s.commit()
    ev.emit(s, run_id, "run_started",
            {"mission": "instruire", "brief_raw": "test",
             "plan": [{"moteur": "etape_a", "bloquant": True},
                      {"moteur": "etape_b", "bloquant": False}]})
    try:
        yield s, run_id
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()


def _fake(fn):
    """Enrobe une fonction de test en wrapper moteur (signature (db, brief, dossier))."""
    return fn


def _kinds(s, run_id):
    return [r[0] for r in s.execute(text(
        "SELECT kind FROM agent_events WHERE run_id = CAST(:r AS uuid) ORDER BY seq"),
        {"r": run_id}).all()]


def _events(s, run_id, kind):
    return [r[0] for r in s.execute(text(
        "SELECT payload FROM agent_events WHERE run_id = CAST(:r AS uuid) AND kind = :k "
        "ORDER BY seq"), {"r": run_id, "k": kind}).all()]


@pytest.fixture
def moteurs_mockes(monkeypatch):
    """Remplace le registre des moteurs par des fakes contrôlables par test."""
    registre: dict = {}
    monkeypatch.setattr(moteurs, "MOTEURS", registre)
    monkeypatch.setattr(moteurs, "MOTEURS_AVEC_RUN_ID", set())
    return registre


@pytest.mark.db
def test_run_nominal_zero_retenue_est_done(run_pret, moteurs_mockes):
    # Zéro retenue = résultat VALIDE et premier de classe (mandat §4).
    moteurs_mockes["etape_a"] = _fake(lambda db, brief, dossier: moteurs.StepResult(
        resultat={"n_candidats": 0}, n_avant=0, n_apres=0))
    moteurs_mockes["etape_b"] = _fake(lambda db, brief, dossier: moteurs.StepResult(
        resultat={"n_retenues": 0}))
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert ev.run_status(s, run_id) == "done"
    recap = _events(s, run_id, "run_completed")[0]
    assert recap["n_retenues"] == 0 and recap["n_ecartees"] == 0
    assert "duree_totale_ms" in recap


@pytest.mark.db
def test_transitoire_retry_unique_puis_succes(run_pret, moteurs_mockes):
    appels = {"n": 0}

    def flaky(db, brief, dossier):
        appels["n"] += 1
        if appels["n"] == 1:
            raise TimeoutError("moteur lent")
        return moteurs.StepResult(resultat={"ok": True})

    moteurs_mockes["etape_a"] = flaky
    moteurs_mockes["etape_b"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert appels["n"] == 2                          # UN retry, pas plus
    assert ev.run_status(s, run_id) == "done"
    assert _events(s, run_id, "step_failed") == []   # le retry a réussi → pas d'échec journalisé


@pytest.mark.db
def test_transitoire_double_echec_step_failed_compact(run_pret, moteurs_mockes):
    def toujours_timeout(db, brief, dossier):
        raise TimeoutError("x" * 500)

    moteurs_mockes["etape_a"] = toujours_timeout
    moteurs_mockes["etape_b"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))
    s, run_id = run_pret
    executeur.executer_run(run_id)
    failed = _events(s, run_id, "step_failed")
    assert len(failed) == 1
    assert failed[0]["code_erreur"] == "transitoire"
    assert len(failed[0]["resume"]) <= 200           # erreur COMPACTÉE (Factor 9)
    assert "Traceback" not in failed[0]["resume"]
    # etape_a est bloquante → run_failed.
    assert ev.run_status(s, run_id) == "failed"


@pytest.mark.db
def test_erreur_non_transitoire_pas_de_retry(run_pret, moteurs_mockes):
    appels = {"n": 0}

    def casse(db, brief, dossier):
        appels["n"] += 1
        raise ValueError("bug de moteur")

    moteurs_mockes["etape_a"] = casse
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert appels["n"] == 1                          # JAMAIS de retry sur non-transitoire
    assert _events(s, run_id, "step_failed")[0]["code_erreur"] == "erreur_moteur"


@pytest.mark.db
def test_non_bloquant_echoue_run_continue(run_pret, moteurs_mockes):
    moteurs_mockes["etape_a"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))

    def casse(db, brief, dossier):
        raise ValueError("DVF indisponible")

    moteurs_mockes["etape_b"] = casse                # etape_b est NON-bloquante dans le plan
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert ev.run_status(s, run_id) == "done"        # le run va au bout
    assert _events(s, run_id, "step_failed")[0]["moteur"] == "etape_b"


@pytest.mark.db
def test_bloquant_echoue_run_failed(run_pret, moteurs_mockes):
    def casse(db, brief, dossier):
        raise ValueError("plus de base")

    moteurs_mockes["etape_a"] = casse                # etape_a est BLOQUANTE
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert ev.run_status(s, run_id) == "failed"
    fail = _events(s, run_id, "run_failed")[0]
    assert fail["code"] == "etape_bloquante" and "etape_a" in fail["message"]


@pytest.mark.db
def test_timeout_global_message_honnete(run_pret, moteurs_mockes, monkeypatch):
    monkeypatch.setattr(config.get_settings(), "copilote_timeout_run_s", -1.0)
    moteurs_mockes["etape_a"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))
    s, run_id = run_pret
    executeur.executer_run(run_id)
    fail = _events(s, run_id, "run_failed")[0]
    assert fail["code"] == "timeout_global" and "incomplet" in fail["message"]
    assert _events(s, run_id, "step_started") == []  # rien lancé au-delà du budget


@pytest.mark.db
def test_plafond_appels_moteurs(run_pret, moteurs_mockes, monkeypatch):
    monkeypatch.setattr(config.get_settings(), "copilote_max_appels_moteurs", 0)
    moteurs_mockes["etape_a"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))
    s, run_id = run_pret
    executeur.executer_run(run_id)
    assert _events(s, run_id, "run_failed")[0]["code"] == "plafond_appels"


@pytest.mark.db
def test_annulation_stoppe_entre_deux_etapes(run_pret, moteurs_mockes):
    s, run_id = run_pret

    def annule_puis_ok(db, brief, dossier):
        ev.emit(s, run_id, "run_cancelled", {"motif": "test"})
        return moteurs.StepResult(resultat={})

    moteurs_mockes["etape_a"] = annule_puis_ok
    moteurs_mockes["etape_b"] = _fake(lambda db, brief, dossier: moteurs.StepResult(resultat={}))
    executeur.executer_run(run_id)
    assert ev.run_status(s, run_id) == "cancelled"
    # etape_b n'a jamais démarré.
    assert all(p.get("moteur") != "etape_b" for p in _events(s, run_id, "step_started"))


@pytest.mark.db
def test_ia_indisponible_run_failed_honnete(engine, monkeypatch):
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw) VALUES ('instruire', 'six logements') "
        "RETURNING id::text")).scalar_one()
    s.commit()
    ev.emit(s, run_id, "run_started", {"plan": []})
    monkeypatch.setattr(executeur, "interpreter_brief",
                        lambda *a, **k: (_ for _ in ()).throw(
                            executeur.IAIndisponible("no_key")))
    try:
        executeur.executer_run(run_id)
        assert ev.run_status(s, run_id) == "failed"
        fail = [r[0] for r in s.execute(text(
            "SELECT payload FROM agent_events WHERE run_id = CAST(:r AS uuid) "
            "AND kind = 'run_failed'"), {"r": run_id}).all()][0]
        assert fail["code"] == "ia_indisponible"
        assert "interprété" in fail["message"]       # message honnête, jamais un brief deviné
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()


@pytest.mark.db
def test_clarification_metmet_le_run_en_awaiting_user(engine, monkeypatch):
    from labuse.copilote.interpreteur import Interpretation
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw) VALUES ('instruire', 'un terrain') "
        "RETURNING id::text")).scalar_one()
    s.commit()
    ev.emit(s, run_id, "run_started", {"plan": []})
    monkeypatch.setattr(executeur, "interpreter_brief",
                        lambda *a, **k: Interpretation(clarification={
                            "question": "Quelle commune ?", "champ_manquant": "communes"}))
    try:
        executeur.executer_run(run_id)
        assert ev.run_status(s, run_id) == "awaiting_user"
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()
