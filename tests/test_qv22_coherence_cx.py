"""QV22-1 (mandat Vic) — la connexion `Cx` du banc des invariants (vague 2) est en AUTOCOMMIT.

Régression du blocage coherence-banc du 08/11 04:08 : `banc2.executer` garde UNE SEULE `Cx` ouverte
sur toute la boucle des familles. Sans autocommit, psycopg ouvre une transaction au premier SELECT et
la tient ; en mode `--tout` (dimanche) les familles cadencées laissent la connexion IDLE IN
TRANSACTION > `idle_in_transaction_session_timeout` (défaut serveur 120 s pour une connexion psycopg
brute) → le serveur la tue → `IdleInTransactionSessionTimeout`. Le correctif pose `autocommit=True`
(comme la soeur `coherence.lib.Contexte`) : chaque SELECT est sa propre micro-transaction, rien ne
reste idle pendant le calcul Python. Test SANS base : on intercepte `psycopg.connect`.
"""
from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))


class _FauxConn:
    """Minuscule double de la connexion psycopg : n'enregistre que ce que `Cx` lui pose."""

    def __init__(self):
        self.autocommit = False      # défaut psycopg : transaction ouverte au 1er SELECT
        self.read_only = False
        self.closed = False

    def close(self):
        self.closed = True


def test_cx_est_en_autocommit(monkeypatch):
    from scripts.coherence import chasse_invariants as ci

    faux = _FauxConn()
    monkeypatch.setattr(ci.psycopg, "connect", lambda *a, **k: faux)

    cx = ci.Cx("postgresql://peu-importe")

    # Le coeur du correctif : aucune transaction tenue pendant la longue boucle des familles.
    assert faux.autocommit is True, (
        "Cx doit être en autocommit : sinon la connexion reste IDLE IN TRANSACTION pendant les "
        "familles cadencées du mode --tout et le serveur la tue (blocage du 08/11 04:08)."
    )
    assert faux.read_only is True   # lecture seule conservée (le banc n'écrit jamais)
    assert cx.conn is faux


def test_coherence_banc_s_abstient_pendant_un_calcul(monkeypatch):
    """QV22-1 (alerte Vic) — OOM du 08/11 : le banc en-process + les workers de cascade ont saturé la RAM
    (0 swap). Le banc doit S'ABSTENIR si un calcul tourne, sans monter le TestClient (donc sans OOM)."""
    from types import SimpleNamespace
    from labuse import jobs_impl, run_progress

    # un flux-run est EN COURS → le banc doit s'abstenir AVANT tout import/montage lourd.
    monkeypatch.setattr(run_progress, "en_cours", lambda: {"label": "q_v22", "pid": 4242})

    def _interdit(*a, **k):
        raise AssertionError("le banc ne doit PAS monter le TestClient pendant un calcul (risque OOM)")
    # si l'abstention échoue, l'import du banc ou _run_banc serait atteint — on le rend explosif.
    monkeypatch.setattr(jobs_impl, "_run_sous_process_nice", _interdit, raising=False)

    compteurs: dict = {}
    ctx = SimpleNamespace(compte=lambda **kw: compteurs.update(kw))
    jobs_impl.coherence_banc(ctx)   # ne doit PAS lever

    assert compteurs.get("banc_saute") is True
    assert "calcul est en cours" in compteurs.get("abstention", "")
