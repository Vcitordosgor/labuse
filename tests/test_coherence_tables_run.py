"""M50 (Lot B) — garde de cohérence des tables servies run-scopées (assertion « aucune table
servie silencieusement périmée »). Classification par table, sans DB."""
from __future__ import annotations

import re

from labuse import bascule_gardes as bg

_SERVI = "q_v8_calibre"


class _Res:
    def __init__(self, scalar=None, rows=None):
        self._s, self._r = scalar, rows or []
    def scalar(self):
        return self._s
    def all(self):
        return self._r


class _FakeConn:
    """table_runs: {table: {run: count}}  · None (clé absente) = table ABSENTE."""
    def __init__(self, table_runs):
        self.table_runs = table_runs
    def execute(self, clause, *a, **k):
        sql = str(clause)
        if "to_regclass" in sql:
            tbl = re.search(r"to_regclass\('(\w+)'\)", sql).group(1)
            return _Res(scalar=self.table_runs.get(tbl) is not None)
        tbl = re.search(r"FROM (\w+) GROUP BY", sql).group(1)
        return _Res(rows=list((self.table_runs.get(tbl) or {}).items()))


def _all(runs):
    return {"parcel_renouvellement": runs, "score_e": runs, "parcel_flags": runs,
            "division_or_candidates": runs}


def _check(monkeypatch, table_runs):
    # SUITE-1 S3 — le run servi se lit via runs.current() (plus de constante d'import) : on l'injecte là.
    monkeypatch.setattr("labuse.runs.current", lambda: _SERVI)
    return bg.check_coherence_tables_run_scopees(session=_FakeConn(table_runs))


def test_tout_ok_quand_toutes_sur_le_run_servi(monkeypatch):
    out = _check(monkeypatch, _all({_SERVI: 100}))
    assert set(out.values()) == {"OK"}


def test_score_e_perimee_flaggee(monkeypatch):
    tr = _all({_SERVI: 100}); tr["score_e"] = {"q_v7_defisc": 77308}
    out = _check(monkeypatch, tr)
    assert out["score_e"] == "PÉRIMÉE" and out["parcel_renouvellement"] == "OK"


def test_division_or_perimee_toleree_mais_flaggee(monkeypatch):
    tr = _all({_SERVI: 100}); tr["division_or_candidates"] = {"q_v7_defisc": 35}
    out = _check(monkeypatch, tr)
    assert out["division_or_candidates"] == "PÉRIMÉE"   # tolérée mais VISIBLE (jamais silencieuse)


def test_melangee_quand_deux_runs(monkeypatch):
    tr = _all({_SERVI: 100}); tr["parcel_flags"] = {_SERVI: 50, "q_v7_defisc": 10}
    out = _check(monkeypatch, tr)
    assert out["parcel_flags"] == "MÉLANGÉE"


def test_absente_quand_table_manque(monkeypatch):
    tr = _all({_SERVI: 100}); tr["score_e"] = None
    out = _check(monkeypatch, tr)
    assert out["score_e"] == "ABSENTE"


def test_garde_ne_leve_jamais(monkeypatch):
    _check(monkeypatch, _all({"q_v7_defisc": 5}))   # tout périmé → aucune exception
