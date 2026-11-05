"""NU4-FIX-1 — Lot E (charge). Reproductions des trouvailles du rapport
`docs/audit-2026-11/nu-4/E/RAPPORT.md` au niveau des MÉCANISMES corrigés à la source (le banc
50 clients iso-prod reste une activité de banc, hors environnement de test unitaire).

- R1 : le rendu PDF tourne HORS-PROCESS → un crash natif / OOM / hang tue l'ENFANT, jamais le worker.
- R3 : `ai.core` libère la connexion DB AVANT l'appel réseau au modèle (plus d'« idle in transaction »).
- R2 : le pool est configuré LIFO + `pool_timeout` borné (hygiène sous charge).
"""
from __future__ import annotations

import inspect
import os
import time

import pytest

from labuse.ai import core
from labuse.exports import rendu


# ───────────────────────── R1 — le rendu PDF hors-process ne peut plus tuer le serveur ─────────────────────────

def test_r1_crash_du_rendu_ne_tue_pas_le_worker():
    """Un process de rendu qui MEURT (SIGSEGV/os._exit, comme weasyprint/Cairo sous charge) remonte en
    `RenderError` — le process appelant (le worker) SURVIT — et le pool se rétablit pour le rendu suivant."""
    with pytest.raises(rendu.RenderError):
        rendu._execute_isole(os._exit, 1, timeout=10)      # l'enfant se tue → BrokenProcessPool
    # le pool est reparti propre : un « rendu » suivant aboutit (preuve que le worker est vivant)
    assert rendu._execute_isole(abs, -7, timeout=10) == 7


def test_r1_rendu_trop_long_abandonne_proprement():
    """Un rendu qui dépasse le délai est ABANDONNÉ en `RenderError`, pas laissé pendre indéfiniment."""
    with pytest.raises(rendu.RenderError):
        rendu._execute_isole(time.sleep, 30, timeout=0.5)


def test_r1_render_pdf_hors_process_produit_un_pdf():
    """Bout en bout : `render_pdf` (mode isolé par défaut) rend un vrai PDF dans un process enfant."""
    try:
        import weasyprint  # noqa: F401
    except Exception:  # noqa: BLE001 — pango/weasyprint absent de l'env : mécanisme déjà prouvé ci-dessus
        pytest.skip("weasyprint/pango indisponible")
    html = "<!doctype html><html><head><meta charset='utf-8'></head><body><h1>NU4-FIX-1</h1></body></html>"
    out = rendu.render_pdf(html)
    assert isinstance(out, bytes) and out[:4] == b"%PDF"


# ───────────────────────── R3 — la connexion DB est libérée avant l'appel modèle ─────────────────────────

def test_r3_liberer_connexion_commit():
    class _DB:
        def __init__(self):
            self.commits = 0

        def commit(self):
            self.commits += 1

    db = _DB()
    core._liberer_connexion(db)
    assert db.commits == 1
    core._liberer_connexion(None)        # None toléré (certains appelants n'ont pas de session)


def test_r3_liberer_connexion_rollback_si_commit_casse():
    class _DB:
        def __init__(self):
            self.rolled = 0

        def commit(self):
            raise RuntimeError("commit cassé")

        def rollback(self):
            self.rolled += 1

    db = _DB()
    core._liberer_connexion(db)          # ne lève jamais (best-effort)
    assert db.rolled == 1


def test_r3_complete_libere_avant_lappel_reseau():
    """La libération précède bien l'appel réseau dans le code servi (ordre garanti)."""
    src = inspect.getsource(core.complete)
    i_lib = src.index("_liberer_connexion(db)")
    i_net = src.index("client.messages.create")
    assert i_lib < i_net, "la connexion doit être libérée AVANT l'appel au modèle"


@pytest.mark.db
def test_r3_session_reelle_liberee(db_session):
    """Sur une VRAIE session : une lecture ouvre une transaction ; après libération, plus de tx ouverte
    (la connexion est rendue au pool pendant l'appel modèle)."""
    from sqlalchemy import text
    db_session.execute(text("SELECT 1"))
    assert db_session.in_transaction() is True
    core._liberer_connexion(db_session)
    assert db_session.in_transaction() is False


# ───────────────────────── R2 — hygiène du pool (LIFO + pool_timeout borné) ─────────────────────────

def test_r2_pool_lifo_et_timeout():
    from labuse.config import get_settings
    from labuse.db import make_engine
    eng = make_engine()
    try:
        # SQLAlchemy 2.0 porte le drapeau LIFO sur la file interne du QueuePool.
        assert getattr(eng.pool._pool, "use_lifo", False) is True
        assert float(getattr(eng.pool, "_timeout")) == float(get_settings().db_pool_timeout_s)
    finally:
        eng.dispose()
