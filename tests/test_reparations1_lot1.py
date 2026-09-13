"""REPARATIONS-1 lot 1 — LE CANDIDAT ASSUMÉ : V3a distingue une génération en trop NON
déclarée (rouge, le vrai danger) d'un candidat DÉCLARÉ et assumé (vert, nommé dans la
preuve). Le geste est journalisé et réversible ; le run reste en base."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import circuit_candidat, circuit_verrous, runs

pytestmark = pytest.mark.db


def _poser_tuiles(db, label: str) -> None:
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS mvt_meta (key text PRIMARY KEY, value text, updated_at timestamptz)"))
    db.execute(text("DELETE FROM mvt_meta WHERE key = 'run_label'"))
    db.execute(text("INSERT INTO mvt_meta (key, value) VALUES ('run_label', :v)"), {"v": label})


def _nettoyer(db) -> None:
    circuit_candidat.ensure(db)
    db.execute(text("DELETE FROM circuit_candidat_assume WHERE run_label LIKE 'q_test%'"))


def test_candidat_non_declare_reste_rouge(db_session, monkeypatch):
    _nettoyer(db_session)
    _poser_tuiles(db_session, "q_test_candidat")
    monkeypatch.setattr(runs, "current", lambda: "q_test_servi")
    r = circuit_verrous.verrou_versions_generations(db_session)
    assert r.verdict == "casse"
    assert any("NON déclaré" in d for d in r.details)


def test_candidat_declare_et_assume_passe_vert_et_nomme(db_session, monkeypatch):
    _nettoyer(db_session)
    _poser_tuiles(db_session, "q_test_candidat")
    monkeypatch.setattr(runs, "current", lambda: "q_test_servi")
    circuit_candidat.declarer(db_session, "q_test_candidat", "test",
                              "refonte en cours, gardé en comparaison")
    r = circuit_verrous.verrou_versions_generations(db_session)
    assert r.verdict == "ok"
    assert "q_test_candidat" in r.preuve and "DÉCLARÉ" in r.preuve, \
        "le verrou vert NOMME le candidat assumé dans sa preuve"


def test_declaration_autre_run_ne_couvre_pas(db_session, monkeypatch):
    """Assumer q_v14 ne blanchit pas des tuiles q_v15 : la déclaration est PAR run."""
    _nettoyer(db_session)
    _poser_tuiles(db_session, "q_test_autre")
    monkeypatch.setattr(runs, "current", lambda: "q_test_servi")
    circuit_candidat.declarer(db_session, "q_test_candidat", "test", "motif")
    r = circuit_verrous.verrou_versions_generations(db_session)
    assert r.verdict == "casse"


def test_geste_journalise_et_reversible(db_session, monkeypatch):
    _nettoyer(db_session)
    _poser_tuiles(db_session, "q_test_candidat")
    monkeypatch.setattr(runs, "current", lambda: "q_test_servi")
    circuit_candidat.declarer(db_session, "q_test_candidat", "test", "motif écrit")
    ligne = db_session.execute(text(
        "SELECT resultat, details FROM circuit_journal WHERE geste = 'candidat' "
        "AND cible = 'q_test_candidat' ORDER BY id DESC LIMIT 1")).first()
    assert ligne is not None and ligne.resultat == "ok"
    # réversible : retirer ne supprime rien, il tamponne — et V3a redevient rouge
    r = circuit_candidat.retirer(db_session, "q_test_candidat", "test")
    assert r["retirees"] == 1
    assert circuit_candidat.actif(db_session) is None
    h = circuit_candidat.historique(db_session)
    assert any(x["run_label"] == "q_test_candidat" and x["retire_le"] is not None for x in h), \
        "l'historique garde la déclaration retirée (rien n'est effacé)"
    assert circuit_verrous.verrou_versions_generations(db_session).verdict == "casse"
    # re-déclarer = le geste inverse du retrait
    circuit_candidat.declarer(db_session, "q_test_candidat", "test", "motif")
    assert circuit_verrous.verrou_versions_generations(db_session).verdict == "ok"
