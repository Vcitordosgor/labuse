"""M26-A — event log : réduction (pur), émission append-only (DB), filtre boussole."""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from labuse.copilote import events as ev
from labuse.copilote.boussole import MARQUEUR, filtrer_payload

# ───────────────────────── reduce_run (fonction pure) ─────────────────────────

@pytest.mark.parametrize("kinds, attendu", [
    ([], "interpreting"),
    (["run_started"], "interpreting"),
    (["run_started", "brief_parsed"], "running"),
    (["run_started", "clarification_requested"], "awaiting_user"),
    (["run_started", "clarification_requested", "clarification_answered"], "interpreting"),
    (["run_started", "clarification_requested", "clarification_answered", "brief_parsed"],
     "running"),
    (["run_started", "brief_parsed", "step_started"], "running"),
    (["run_started", "brief_parsed", "step_started", "step_failed"], "running"),
    (["run_started", "brief_parsed", "run_paused"], "paused"),
    (["run_started", "brief_parsed", "run_paused", "run_resumed"], "running"),
    (["run_started", "brief_parsed", "step_started", "step_completed", "run_completed"],
     "done"),
    (["run_started", "brief_parsed", "step_started", "run_failed"], "failed"),
    (["run_started", "run_cancelled"], "cancelled"),
])
def test_reduce_run(kinds, attendu):
    assert ev.reduce_run(kinds) == attendu


def test_reduce_terminal_absorbant():
    # Un état terminal ne « ressuscite » jamais, quels que soient les événements suivants.
    assert ev.reduce_run(["run_started", "run_completed", "step_started"]) == "done"
    assert ev.reduce_run(["run_started", "run_failed", "run_completed"]) == "failed"
    assert ev.reduce_run(["run_started", "run_cancelled", "brief_parsed"]) == "cancelled"


def test_reduce_refuse_hors_taxonomie():
    with pytest.raises(ValueError, match="taxonomie"):
        ev.reduce_run(["run_started", "evenement_invente"])


# ───────────────────────── filtre boussole (pur) ─────────────────────────

def test_boussole_bloque_personne_physique():
    clean, n = filtrer_payload({"proprietaire_nom": "Jean Payet", "surface_m2": 800})
    assert clean["proprietaire_nom"] == MARQUEUR and n == 1
    assert clean["surface_m2"] == 800


def test_boussole_laisse_personne_morale():
    clean, n = filtrer_payload({"owner_type": "sci", "denomination": "SCI SOLEIL"})
    assert clean["denomination"] == "SCI SOLEIL" and n == 0


def test_boussole_prenom_et_dirigeant_toujours_bloques():
    clean, n = filtrer_payload({"owner_type": "societe", "denomination": "SAS RUN",
                                "dirigeant": "Paul Hoarau", "prenom": "Paul"})
    assert clean["dirigeant"] == MARQUEUR and clean["prenom"] == MARQUEUR and n == 2
    assert clean["denomination"] == "SAS RUN"


def test_boussole_profondeur_listes():
    payload = {"resultats": [{"idu": "97415000AB0001",
                              "contact_nom": "M. Untel", "tier": "chaude"}]}
    clean, n = filtrer_payload(payload)
    assert clean["resultats"][0]["contact_nom"] == MARQUEUR and n == 1
    assert clean["resultats"][0]["idu"] == "97415000AB0001"


# ───────────────────────── émission (DB, append-only) ─────────────────────────

@pytest.fixture
def run_db(engine):
    """Session autonome (emit committe) + run jetable, nettoyé par cascade."""
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    run_id = s.execute(text(
        "INSERT INTO agent_runs (mission, brief_raw) VALUES ('instruire', 'test') "
        "RETURNING id::text")).scalar_one()
    s.commit()
    try:
        yield s, run_id
    finally:
        s.rollback()
        s.execute(text("DELETE FROM agent_runs WHERE id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
        s.close()


@pytest.mark.db
def test_emit_seq_croissant_et_statut_cache(run_db):
    s, run_id = run_db
    assert ev.emit(s, run_id, "run_started", {"mission": "instruire"}) == 1
    assert ev.emit(s, run_id, "brief_parsed", {"brief_json": {}}) == 2
    assert ev.emit(s, run_id, "step_started", {"moteur": "criblage"}) == 3
    statut = s.execute(text("SELECT status FROM agent_runs WHERE id = CAST(:r AS uuid)"),
                       {"r": run_id}).scalar()
    assert statut == "running" == ev.run_status(s, run_id)


@pytest.mark.db
def test_emit_refuse_hors_taxonomie_et_apres_terminal(run_db):
    s, run_id = run_db
    with pytest.raises(ValueError, match="taxonomie"):
        ev.emit(s, run_id, "evenement_invente", {})
    ev.emit(s, run_id, "run_started", {})
    ev.emit(s, run_id, "run_completed", {"n_retenues": 0, "n_ecartees": 0})
    with pytest.raises(RuntimeError, match="terminal"):
        ev.emit(s, run_id, "step_started", {"moteur": "criblage"})


@pytest.mark.db
def test_emit_filtre_boussole_sur_payload(run_db):
    # Exigence mandat §6 : nom de personne physique dans un résultat moteur mocké → bloqué.
    s, run_id = run_db
    ev.emit(s, run_id, "run_started", {})
    ev.emit(s, run_id, "step_completed",
            {"moteur": "criblage", "resultat": {"proprietaire_nom": "Jean Payet",
                                                "n_candidats": 3}})
    payload = s.execute(text(
        "SELECT payload FROM agent_events WHERE run_id = CAST(:r AS uuid) AND seq = 2"),
        {"r": run_id}).scalar()
    assert payload["resultat"]["proprietaire_nom"] == MARQUEUR
    assert payload["resultat"]["n_candidats"] == 3
    assert payload["_boussole_filtre"] == 1
    assert "Jean Payet" not in str(payload)


@pytest.mark.db
def test_update_evenement_refuse_par_trigger(run_db):
    s, run_id = run_db
    ev.emit(s, run_id, "run_started", {})
    with pytest.raises(Exception, match="append-only"):
        s.execute(text("UPDATE agent_events SET kind = 'run_failed' "
                       "WHERE run_id = CAST(:r AS uuid)"), {"r": run_id})
        s.commit()
    s.rollback()


@pytest.mark.db
def test_events_after_sans_doublon_ni_trou(run_db):
    s, run_id = run_db
    ev.emit(s, run_id, "run_started", {})
    ev.emit(s, run_id, "brief_parsed", {})
    ev.emit(s, run_id, "step_started", {"moteur": "criblage"})
    tout = ev.events_after(s, run_id, 0)
    assert [e["seq"] for e in tout] == [1, 2, 3]
    reprise = ev.events_after(s, run_id, 2)
    assert [e["seq"] for e in reprise] == [3]
