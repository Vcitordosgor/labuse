"""DONNEES-2 (B2/B3) — l'état & la progression d'un run lancé (fichier lu par l'API).

Sans base : on exerce le cycle de vie (démarrage → progression → terminé / abandonné), l'arrêt propre,
et surtout la RÉCONCILIATION au chargement — un run « en cours » dont le processus a disparu passe
« abandonné », et un vieux log orphelin (run tué avant ce mécanisme) est récupéré « abandonné » (D3).
"""
from __future__ import annotations

import os

import pytest

from labuse import run_progress as rp


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_STATE_DIR", str(tmp_path))
    return tmp_path


def test_cycle_de_vie_start_progress_finish():
    rp.start("q_x", pid=os.getpid(), kind="run", recette="m36", total=25)
    st = rp.read("q_x")
    assert st["statut"] == rp.STATUT_EN_COURS and st["pct"] == 0 and st["recette"] == "m36"
    rp.progress("q_x", phase="cascade", commune="Saint-Paul", done=10, total=25, pct=40)
    assert rp.read("q_x")["pct"] == 40 and rp.read("q_x")["commune"] == "Saint-Paul"
    rp.finish("q_x", n_parcelles=431663)
    st = rp.read("q_x")
    assert st["statut"] == rp.STATUT_TERMINE and st["pct"] == 100 and st["n_parcelles"] == 431663


def test_pid_alive():
    assert rp.pid_alive(os.getpid()) is True
    assert rp.pid_alive(2_000_000_000) is False
    assert rp.pid_alive(None) is False


def test_en_cours_ignore_les_process_morts():
    # un run « en cours » avec un pid mort ne doit PAS être vu comme en cours
    rp.start("q_dead", pid=2_000_000_000, kind="run")
    assert rp.en_cours() is None
    # un run avec NOTRE pid (vivant) l'est
    rp.start("q_live", pid=os.getpid(), kind="run")
    assert (rp.en_cours() or {}).get("label") == "q_live"


def test_reconcile_marque_abandonne_un_en_cours_mort():
    rp.start("q_dead", pid=2_000_000_000, kind="run")
    rp.reconcile(complete_labels=set())
    assert rp.read("q_dead")["statut"] == rp.STATUT_ABANDONNE


def test_reconcile_marque_termine_si_devenu_complet():
    rp.start("q_done", pid=2_000_000_000, kind="run")
    rp.reconcile(complete_labels={"q_done"})
    assert rp.read("q_done")["statut"] == rp.STATUT_TERMINE


def test_reconcile_recupere_les_logs_orphelins(tmp_path):
    # un run tué AVANT ce mécanisme n'a qu'un log /tmp vide → récupéré « abandonné »
    (tmp_path / "labuse-flux-run-q_ancien_tue.log").write_text("", encoding="utf-8")
    assert rp.read("q_ancien_tue") is None
    rp.reconcile(complete_labels=set())
    st = rp.read("q_ancien_tue")
    assert st is not None and st["statut"] == rp.STATUT_ABANDONNE
    # un log dont le run EST complet n'est pas ressuscité en abandonné
    (tmp_path / "labuse-flux-run-q_complet.log").write_text("", encoding="utf-8")
    rp.reconcile(complete_labels={"q_complet"})
    assert rp.read("q_complet") is None


def test_stop_marque_abandonne():
    # stop sur un run dont le pid n'existe pas : idempotent, marque abandonné, tue=False
    rp.start("q_stop", pid=2_000_000_000, kind="run")
    res = rp.stop("q_stop")
    assert res["ok"] is True and res["tue"] is False
    assert rp.read("q_stop")["statut"] == rp.STATUT_ABANDONNE
    # stop sur un run inconnu → refus explicite
    assert rp.stop("inexistant")["ok"] is False
