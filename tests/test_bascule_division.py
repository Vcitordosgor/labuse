"""BASCULE-DIVISION — `basculer(..., division_run=...)` garde la division d'or sur un run
ANTÉRIEUR pendant que scoring/mvt passent au neuf (cas q_v20 : découpe division-or pas finie →
on bascule le Score mais on laisse `division_run` sur q_v19).

Même dispositif que test_bascule1 : on ne bascule JAMAIS pour de vrai (pointeurs redirigés sur un
dossier temporaire, collaborateurs lourds neutralisés) ; seul l'écrit du manifeste est vérifié.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse import (bascule_flux, circuit_journal, coherence_flux, golden_ops,
                    manifeste, runs)

pytestmark = pytest.mark.db

_JOURNAL_DDL = (
    "CREATE TABLE IF NOT EXISTS run_bascule_journal ("
    " id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),"
    " ancien varchar(64), nouveau varchar(64) NOT NULL,"
    " par varchar(120), sens varchar(12) NOT NULL DEFAULT 'avant',"
    " caches_purges jsonb NOT NULL DEFAULT '[]'::jsonb, coherence jsonb)")


@pytest.fixture
def bascule_tmp(tmp_path, monkeypatch):
    """Pointeurs sur un dossier temporaire + collaborateurs lourds neutralisés.
    État de départ : servi = q_old (division q_old), précédent = q_older."""
    monkeypatch.setattr(manifeste, "_FICHIER", tmp_path / "served_manifest.json")
    monkeypatch.setattr(runs, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.setattr(runs, "_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(bascule_flux, "_RUN_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(golden_ops, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    monkeypatch.delenv("LABUSE_RUN_PRECEDENT", raising=False)

    monkeypatch.setattr(bascule_flux, "_run_complet", lambda db, run: (True, "test : complet"))
    monkeypatch.setattr(bascule_flux, "purger_caches_run", lambda: [])
    monkeypatch.setattr(coherence_flux, "verifier", lambda db, run: {"ok": True})
    monkeypatch.setattr(circuit_journal, "journaliser", lambda *a, **k: None)

    def _fake_promote(run: str) -> dict:
        ancien = runs.current()
        (tmp_path / "served_run.txt").write_text(run + "\n", encoding="utf-8")
        runs.invalidate()
        return {"ok": True, "ancien": ancien, "nouveau": run}
    monkeypatch.setattr(golden_ops, "promote", _fake_promote)

    manifeste.ecrire({"scoring_run": "q_old", "residuel_run_seq": None, "mvt_run": "q_old",
                      "division_run": "q_old", "promoted_at": None, "par": "test",
                      "cascade_run": "q_old",
                      "precedent": {"scoring_run": "q_older", "residuel_run_seq": None,
                                    "mvt_run": "q_older", "division_run": "q_older"}})
    (tmp_path / "served_run.txt").write_text("q_old\n", encoding="utf-8")
    (tmp_path / "run_precedent.txt").write_text("q_older\n", encoding="utf-8")
    runs.invalidate()
    yield tmp_path
    runs.invalidate()


def _manifeste_ecrit(tmp) -> dict:
    return json.loads((tmp / "served_manifest.json").read_text())


def test_division_run_garde_un_run_anterieur(db_session, bascule_tmp):
    """bascule q_new en gardant division sur q_keep : scoring/mvt → q_new, division → q_keep."""
    db_session.execute(text(_JOURNAL_DDL))
    res = bascule_flux.basculer(db_session, "q_new", par="test", division_run="q_keep")

    assert res["ok"] is True and res["verifie"] is True
    m = _manifeste_ecrit(bascule_tmp)
    assert m["scoring_run"] == "q_new"
    assert m["mvt_run"] == "q_new"
    assert m["division_run"] == "q_keep", "division d'or GARDÉE sur le run antérieur"
    # le précédent capture bien l'état d'avant (division q_old)
    assert m["precedent"]["division_run"] == "q_old"


def test_sans_override_division_suit_le_nouveau_run(db_session, bascule_tmp):
    """Défaut inchangé (rétro-compat) : sans `division_run`, les 3 pointeurs bougent ensemble."""
    db_session.execute(text(_JOURNAL_DDL))
    res = bascule_flux.basculer(db_session, "q_new", par="test")

    assert res["ok"] is True
    m = _manifeste_ecrit(bascule_tmp)
    assert m["scoring_run"] == m["mvt_run"] == m["division_run"] == "q_new"


def test_override_none_equivaut_au_defaut(db_session, bascule_tmp):
    """`division_run=None` explicite == défaut (division suit nouveau_run)."""
    db_session.execute(text(_JOURNAL_DDL))
    bascule_flux.basculer(db_session, "q_new", par="test", division_run=None)
    assert _manifeste_ecrit(bascule_tmp)["division_run"] == "q_new"
