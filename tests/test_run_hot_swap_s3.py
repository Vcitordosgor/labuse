"""SUITE-1 · S3 — le run servi est relu À LA REQUÊTE (bascule à chaud, sans redémarrage).

Ces tests prouvent que `labuse.runs.current()` reflète un changement de
`config/served_run.txt` APRÈS `runs.invalidate()`, SANS réimport du module (c'est
tout l'enjeu : avant S3, `Q_A_RUN_LABEL` était figé à l'import). Aucune base de
données requise — on ne touche qu'au pointeur fichier + au cache mémoire.
"""
from __future__ import annotations

import pytest

from labuse import runs


@pytest.fixture(autouse=True)
def _isole_le_cache(monkeypatch, tmp_path):
    """Chaque test part d'un cache vierge et d'un fichier `served_run.txt` temporaire,
    et SANS override d'environnement (sinon il primerait et masquerait le fichier)."""
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    served = tmp_path / "served_run.txt"
    monkeypatch.setattr(runs, "_SERVED_FILE", served)
    runs.invalidate()
    yield
    runs.invalidate()


def _ecrire(path, valeur: str) -> None:
    path.write_text(f"# pointeur du run servi (test)\n{valeur}\n", encoding="utf-8")


def test_bascule_a_chaud_apres_invalidate(monkeypatch, tmp_path):
    """A → invalidate → B, SANS réimport : current() suit le fichier."""
    served = runs._SERVED_FILE
    _ecrire(served, "q_run_A")
    assert runs.current() == "q_run_A"

    # On réécrit le pointeur (ce que fait golden_ops.promote). Le cache court PEUT
    # encore renvoyer l'ancienne valeur tant qu'on n'a pas invalidé…
    _ecrire(served, "q_run_B")
    # …mais après invalidate(), la lecture suivante voit le nouveau run.
    runs.invalidate()
    assert runs.current() == "q_run_B"


def test_cache_court_evite_de_marteler_le_disque(monkeypatch):
    """Sans invalidate, une 2ᵉ lecture immédiate ne relit PAS le fichier (cache TTL)."""
    served = runs._SERVED_FILE
    _ecrire(served, "q_run_A")
    assert runs.current() == "q_run_A"

    appels = {"n": 0}
    vrai_lire = runs._lire_fichier

    def _compteur():
        appels["n"] += 1
        return vrai_lire()

    monkeypatch.setattr(runs, "_lire_fichier", _compteur)
    # Deux lectures rapprochées → 0 relecture disque (cache encore chaud).
    runs.current()
    runs.current()
    assert appels["n"] == 0


def test_env_override_prioritaire(monkeypatch):
    """`LABUSE_SERVED_RUN` prime sur le fichier ET n'est pas caché (dev/test)."""
    served = runs._SERVED_FILE
    _ecrire(served, "q_run_fichier")
    monkeypatch.setenv("LABUSE_SERVED_RUN", "q_run_override")
    assert runs.current() == "q_run_override"

    # Retirer l'override → on retombe sur le fichier (après invalidate, cache propre).
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    runs.invalidate()
    assert runs.current() == "q_run_fichier"


def test_getattr_constant_reflete_le_run_courant(monkeypatch):
    """Le filet PEP 562 de score_v_constants renvoie bien le run courant (pas figé)."""
    from labuse.scoring import score_v_constants as C

    served = runs._SERVED_FILE
    _ecrire(served, "q_run_A")
    assert C.Q_A_RUN_LABEL == "q_run_A"

    _ecrire(served, "q_run_B")
    runs.invalidate()
    assert C.Q_A_RUN_LABEL == "q_run_B"
