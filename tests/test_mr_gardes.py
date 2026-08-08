"""M-R — gardes qui ne mesurent rien : check_fraicheur honnête, verify_completude sur tier v2
(plus la matrice morte), check_disque qui ne s'auto-désarme plus. Tests PURS (fausse connexion)."""
from __future__ import annotations

import datetime

import pytest

from labuse import bascule_gardes as G


# ── fausse connexion : execute(sql).all()/.scalar() pilotés par le contenu du SQL ──
class _Res:
    def __init__(self, rows=None, scalar=None):
        self._rows, self._scalar = rows or [], scalar

    def all(self):
        return self._rows

    def scalar(self):
        return self._scalar

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    def __init__(self, handler):
        self._h = handler

    def execute(self, stmt, params=None):
        return self._h(str(stmt), params or {})


# ── 1) check_fraicheur : N/total évaluées, « horizon inconnu » ≠ retard ──
def test_check_fraicheur_mesure_et_distingue():
    from labuse.ingestion.fraicheur import DS_NAMES, SOURCES
    vieux = datetime.date(2000, 1, 1)          # très ancien → retard
    recent = datetime.date.today()
    rows = [(DS_NAMES["sitadel"][0], vieux),   # bornable + horizon ancien → RETARD
            (DS_NAMES["dvf"][0], recent),       # bornable + horizon récent → évalué, pas de retard
            (DS_NAMES["dpe"][0], None),          # bornable + horizon NULL → « horizon inconnu »
            (DS_NAMES["ban"][0], recent)]        # bornable récent → évalué

    def handler(sql, params):
        return _Res(rows=rows)                   # unique requête : SELECT name, source_horizon_at …

    r = G.check_fraicheur(session=_FakeConn(handler))
    assert r["total"] == len(SOURCES)            # dénominateur HONNÊTE (10 couches fraîcheur)
    assert "sitadel" in [x["source"] for x in r["retards"]]
    assert "dpe" in r["horizon_inconnu"] and "dpe" not in [x["source"] for x in r["retards"]]
    # gpu_plu/georisques (M-O : horizon NULL, cadence irrégulière) ne sont JAMAIS un retard
    assert "gpu_plu" in r["non_bornable"] and "georisques" in r["non_bornable"]
    assert r["evaluees"] >= 2                     # dvf + ban au moins (pas 1/10 « tout va bien »)


# ── 2) verify_completude : tier v2 exigé, matrice_statut NON exigé ──
def _counts_handler(scores, cascade, tier, status, runs=1, snap=None, cres=1):
    snap = scores if snap is None else snap

    def handler(sql, params):
        if "tier IS NOT NULL" in sql:
            return _Res(scalar=tier)
        if "status IS NOT NULL" in sql:
            return _Res(scalar=status)
        if "matrice_statut" in sql:
            return _Res(scalar=0)                # si jamais interrogé : 0 (prouve qu'il ne bloque pas)
        if "parcel_p_score_v2 WHERE run_id" in sql:
            return _Res(scalar=scores)
        if "dryrun_parcel_evaluations WHERE run_label" in sql:
            return _Res(scalar=cascade)
        if "dryrun_cascade_results WHERE run_label" in sql:
            return _Res(scalar=cres)
        if "p_score_v2_runs" in sql:
            return _Res(scalar=runs)
        if "score_snapshot_parcelles" in sql:
            return _Res(scalar=snap)
        return _Res(scalar=0)
    return handler


def test_verify_completude_servable_sans_matrice():
    """Validation #2a : un run COMPLET (tier + étage 0) est servable même si matrice_statut = 0."""
    N = 100
    G.verify_completude("q_test", N, N, session=_FakeConn(
        _counts_handler(scores=N, cascade=N, tier=N, status=N)))   # ne lève pas


def test_verify_completude_bloque_si_tier_manquant():
    """Validation #2b : un run sans tier v2 n'est PAS servable (échec bruyant)."""
    N = 100
    with pytest.raises(G.RunIncompletError, match="tier"):
        G.verify_completude("q_test", N, N, session=_FakeConn(
            _counts_handler(scores=N, cascade=N, tier=N - 1, status=N)))


def test_verify_completude_ne_reference_plus_la_matrice():
    import inspect
    src = inspect.getsource(G.verify_completude)
    assert "tier_non_null" in src
    assert "matrice_statut" not in src.split('"""', 2)[-1] or "PLUS sur" in src  # plus dans un check bloquant


# ── 3) check_disque : échoue bruyamment si aucun run de référence (ne se désarme plus) ──
def test_check_disque_echoue_sans_run_de_reference():
    """Validation #3 : après purge du run de référence (aucun run mesurable), la garde REFUSE de
    démarrer (échec bruyant) au lieu de passer aveuglément — « une garde qui ne sait pas mesurer
    doit le dire, pas approuver »."""
    def handler(sql, params):
        return _Res(scalar=None)                 # tout vide : _biggest None, n_runs 0

    with pytest.raises(G.DisqueInsuffisantError, match="INOPÉRANTE|aucun run"):
        G.check_disque("q_v8_calibre", session=_FakeConn(handler))


def test_check_disque_mesure_avec_un_autre_run():
    """La purge de q_v7_defisc ne désarme PAS la garde : un autre run sert de référence (max/run)."""
    def handler(sql, params):
        if "max(c)" in sql:
            return _Res(scalar=100)              # un run de référence existe (q_v8)
        if "count(DISTINCT run_id)" in sql:
            return _Res(scalar=1)
        if "pg_total_relation_size" in sql:
            return _Res(scalar=1_000.0)           # besoin non nul
        if "pg_extension" in sql:
            return _Res(scalar=None)              # pas de FSM
        return _Res(scalar=0)                     # already=0, dead=0

    rep = G.check_disque("q_v8_calibre", session=_FakeConn(handler))
    assert rep["besoin_reste_go"] >= 0 and "ok" in rep    # a MESURÉ (pas d'auto-désarmement)
