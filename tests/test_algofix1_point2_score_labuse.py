"""ALGO-FIX-1 (point 2) — `_score_labuse_run()` est LU À CHAQUE REQUÊTE, plus figé à l'import (E7).

Avant, `app.SCORE_LABUSE_RUN` était une constante évaluée une seule fois au chargement du module :
une bascule à chaud (runs.current() relit le manifeste) laissait l'Analyse et la fiche sur l'ANCIEN
run Score LABUSE jusqu'au redémarrage. Ici on prouve que la fonction suit le run servi vivant dans
le MÊME process, et que l'override admin `LABUSE_SCORE_RUN` reste prioritaire.
"""
from __future__ import annotations

from labuse.api import app as app_mod
from labuse import runs


def test_score_labuse_run_suit_le_servi_a_chaud(monkeypatch):
    """Sans override : la fonction rend runs.current() À L'APPEL — un changement en cours de process
    est vu immédiatement (aucune constante figée à l'import)."""
    monkeypatch.delenv("LABUSE_SCORE_RUN", raising=False)
    monkeypatch.setattr(runs, "current", lambda: "q_servi_A")
    assert app_mod._score_labuse_run() == "q_servi_A"
    # bascule à chaud : runs.current() change → la fonction suit SANS réimport/redémarrage.
    monkeypatch.setattr(runs, "current", lambda: "q_servi_B")
    assert app_mod._score_labuse_run() == "q_servi_B"


def test_override_admin_prioritaire(monkeypatch):
    """L'override admin `LABUSE_SCORE_RUN` reste prioritaire (contrôle admin d'un candidat)."""
    monkeypatch.setattr(runs, "current", lambda: "q_servi")
    monkeypatch.setenv("LABUSE_SCORE_RUN", "q_v15")
    assert app_mod._score_labuse_run() == "q_v15"


def test_plus_de_constante_figee():
    """Garde : `SCORE_LABUSE_RUN` (la constante figée à l'import) n'existe plus au module."""
    assert not hasattr(app_mod, "SCORE_LABUSE_RUN"), \
        "la constante figée doit avoir disparu au profit de _score_labuse_run()"
