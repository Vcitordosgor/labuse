"""BASCULE-1 (Lot B) — UNE COMMANDE QUI NE PEUT PLUS MENTIR.

Le bug d'origine : `golden promote` réécrivait la VUE DÉRIVÉE `served_run.txt` et annonçait
« ✓ Run servi = X » — mais depuis CIRCUIT, `runs.current()` lit le MANIFESTE en premier, que
`promote` ne touchait pas. La commande était morte et se disait victorieuse.

Le filet : après avoir écrit, `basculer()` RELIT `runs.current()` et ne confirme (`ok`,
`verifie`) QUE si la valeur relue est bien le run demandé. On teste les deux issues :
 - honnête : le manifeste bouge → runs.current() suit → succès confirmé ;
 - le mensonge : si l'écrit ne prend PAS effet (manifeste inchangé), `basculer()` REFUSE de
   dire « ok » — il rend `ok=False, verifie=False` et dit ce qui a été écrit vs ce qui fait foi.

On ne bascule JAMAIS pour de vrai : tous les pointeurs sont redirigés sur un dossier temporaire
(monkeypatch), et les collaborateurs lourds (run complet, purge des caches, cohérence, journal
unifié) sont neutralisés — seul le cœur RELECTURE / CONFIRMATION est exercé.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse import bascule_flux, circuit_journal, coherence_flux, golden_ops, manifeste, runs

pytestmark = pytest.mark.db

_JOURNAL_DDL = (
    "CREATE TABLE IF NOT EXISTS run_bascule_journal ("
    " id serial PRIMARY KEY, ts timestamptz NOT NULL DEFAULT now(),"
    " ancien varchar(64), nouveau varchar(64) NOT NULL,"
    " par varchar(120), sens varchar(12) NOT NULL DEFAULT 'avant',"
    " caches_purges jsonb NOT NULL DEFAULT '[]'::jsonb, coherence jsonb)")


@pytest.fixture
def bascule_tmp(tmp_path, monkeypatch):
    """Redirige TOUS les pointeurs versionnés sur un dossier temporaire et neutralise les
    collaborateurs lourds. Pré-pose un manifeste (servi = q_old, précédent = q_older)."""
    f_manifeste = tmp_path / "served_manifest.json"
    monkeypatch.setattr(manifeste, "_FICHIER", f_manifeste)
    monkeypatch.setattr(runs, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.setattr(runs, "_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(bascule_flux, "_RUN_PRECEDENT_FILE", tmp_path / "run_precedent.txt")
    monkeypatch.setattr(golden_ops, "_SERVED_FILE", tmp_path / "served_run.txt")
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    monkeypatch.delenv("LABUSE_RUN_PRECEDENT", raising=False)

    # le run demandé est toujours « complet », les caches/cohérence/journal ne font rien.
    monkeypatch.setattr(bascule_flux, "_run_complet", lambda db, run: (True, "test : complet"))
    monkeypatch.setattr(bascule_flux, "purger_caches_run", lambda: [])
    monkeypatch.setattr(coherence_flux, "verifier", lambda db, run: {"ok": True})
    monkeypatch.setattr(circuit_journal, "journaliser", lambda *a, **k: None)

    # promote écrit la vue dérivée served_run.txt (comme en vrai) mais sans toucher la base.
    def _fake_promote(run: str) -> dict:
        ancien = runs.current()
        (tmp_path / "served_run.txt").write_text(run + "\n", encoding="utf-8")
        runs.invalidate()
        return {"ok": True, "ancien": ancien, "nouveau": run}
    monkeypatch.setattr(golden_ops, "promote", _fake_promote)

    # état de départ : servi = q_old, précédent = q_older.
    manifeste.ecrire({"scoring_run": "q_old", "residuel_run_seq": None, "mvt_run": "q_old",
                      "division_run": "q_old", "promoted_at": None, "par": "test",
                      "precedent": {"scoring_run": "q_older", "residuel_run_seq": None,
                                    "mvt_run": "q_older", "division_run": "q_older"}})
    (tmp_path / "served_run.txt").write_text("q_old\n", encoding="utf-8")
    (tmp_path / "run_precedent.txt").write_text("q_older\n", encoding="utf-8")
    runs.invalidate()
    yield tmp_path
    runs.invalidate()


def test_bascule_confirmee_quand_le_manifeste_bouge(db_session, bascule_tmp):
    """Chemin honnête : le manifeste passe à q_new → runs.current() relit q_new → succès CONFIRMÉ."""
    db_session.execute(text(_JOURNAL_DDL))
    assert runs.current() == "q_old"

    res = bascule_flux.basculer(db_session, "q_new", par="test")

    assert res["ok"] is True and res["verifie"] is True
    assert res["current_apres"] == "q_new", "runs.current() relu APRÈS l'écrit = le run demandé"
    assert res["ancien"] == "q_old" and res["nouveau"] == "q_new"
    assert res["manifeste_path"].endswith("served_manifest.json")
    # la vérité disque ET la relecture concordent.
    assert runs.current() == "q_new"
    assert json.loads((bascule_tmp / "served_manifest.json").read_text())["scoring_run"] == "q_new"


def test_bascule_refuse_de_mentir_si_runs_current_ne_change_pas(db_session, bascule_tmp, monkeypatch):
    """LE FILET : si l'écrit du manifeste ne prend PAS effet (ici neutralisé pour simuler une vue
    dérivée écrite dans le mauvais arbre / un manifeste ignoré), `basculer()` NE DIT PAS « ok ».
    Avant BASCULE-1, la commande annonçait un succès alors que runs.current() n'avait pas changé."""
    db_session.execute(text(_JOURNAL_DDL))
    # le manifeste (le point de vérité) refuse de bouger : reste q_old.
    monkeypatch.setattr(manifeste, "ecrire", lambda m: None)
    assert runs.current() == "q_old"

    res = bascule_flux.basculer(db_session, "q_new", par="test")

    assert res["ok"] is False and res["verifie"] is False, \
        "une bascule non prise en compte ne doit JAMAIS s'annoncer réussie"
    assert res["current_apres"] == "q_old", "la commande DIT la valeur qui fait toujours foi"
    assert "q_new" in res["motif"] and "q_old" in res["motif"]
    assert res["manifeste_path"].endswith("served_manifest.json"), "elle dit CE qui a été écrit"
    # et le run servi n'a effectivement pas bougé (aucun mensonge, aucun effet de bord annoncé).
    assert runs.current() == "q_old"


def test_avertissement_arbre_signale_l_ecart_worktree(tmp_path, monkeypatch):
    """BASCULE-1 (Lot C) — l'avertissement est SILENCIEUX quand le cwd est dans l'arbre d'install,
    et PARLE (⚠ ARBRE) quand on lance depuis un autre dossier / worktree git."""
    install = tmp_path / "labuse"
    (install / "config").mkdir(parents=True)
    monkeypatch.setattr(manifeste, "_FICHIER", install / "config" / "served_manifest.json")

    monkeypatch.chdir(install)                       # dans l'arbre d'installation
    assert bascule_flux.avertissement_arbre() is None

    autre = tmp_path / "labuse-worktree"
    autre.mkdir()
    monkeypatch.chdir(autre)                          # un AUTRE arbre
    avert = bascule_flux.avertissement_arbre()
    assert avert is not None and "ARBRE" in avert and str(install) in avert
