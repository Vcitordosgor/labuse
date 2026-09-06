"""6ᵉ garde (Vic 04/08) : toute bascule régénère le golden dans le même geste — sans DB.
CIRCUIT-5b lot 4 : 3ᵉ garde réécrite — rollback par le manifeste, plus par une photo pré-v8."""
from __future__ import annotations

import json

import pytest

from labuse import bascule_gardes as G
from labuse.bascule_gardes import (GoldenPerimeError, RollbackImpossibleError,
                                   check_golden_regenere, verify_rollback_manifeste)


def _ref(tmp_path, run):
    p = tmp_path / "golden.json"
    p.write_text(json.dumps({"meta": {"run_v2_servi": run, "n_parcelles": 116}, "parcelles": {}}),
                 encoding="utf-8")
    return p


def test_golden_a_jour_passe(tmp_path):
    rep = check_golden_regenere("q_v8_calibre", _ref(tmp_path, "q_v8_calibre"))
    assert rep["ok"] and rep["n_parcelles"] == 116


def test_golden_perime_refuse(tmp_path):
    # le cas RÉEL de la bascule v8 : référence restée sur q_v7_defisc → refus BRUYANT
    with pytest.raises(GoldenPerimeError, match="PÉRIMÉ"):
        check_golden_regenere("q_v8_calibre", _ref(tmp_path, "q_v7_defisc"))


def test_golden_absent_refuse(tmp_path):
    with pytest.raises(GoldenPerimeError, match="ABSENT"):
        check_golden_regenere("q_v8_calibre", tmp_path / "inexistant.json")


# ── CIRCUIT-5b lot 4 — la 3ᵉ garde compare au MANIFESTE, jamais à une photo pré-v8 ──────────

def test_ecart_pct_pur():
    assert G._ecart_pct(120, 100) == 20.0
    assert G._ecart_pct(80, 100) == 20.0
    assert G._ecart_pct(0, 100) is None        # candidat vide → non mesurable ici
    assert G._ecart_pct(100, 0) is None        # référence nulle → non mesurable


class _Res:
    def __init__(self, rows=None, scalar=None):
        self._rows, self._scalar = rows or [], scalar

    def scalar(self):
        return self._scalar

    def __iter__(self):
        return iter(self._rows)


class _FakeConn:
    """Session factice pilotée par le SQL — aucune table-photo n'est jamais lue (le test le prouve
    en NE fournissant AUCUNE réponse pour `*_pre_v8` : une lecture y lèverait KeyError)."""
    def __init__(self, *, existe=True, resid_runs=2, score_runs=(), counts=None):
        self.existe, self.resid_runs = existe, resid_runs
        self.score_runs, self.counts = list(score_runs), counts or {}
        self.vus = []

    def execute(self, stmt, params=None):
        s, p = str(stmt), params or {}
        self.vus.append(s)
        assert "pre_v8" not in s, f"la garde ne doit JAMAIS lire une photo pré-v8 : {s}"
        if "to_regclass" in s:
            return _Res(scalar=("x" if self.existe else None))
        if "count(*) FROM residuel_runs" in s:
            return _Res(scalar=self.resid_runs)
        if "run_id FROM p_score_v2_runs" in s:
            return _Res(rows=[(r,) for r in self.score_runs])
        if "FROM parcel_p_score_v2 WHERE run_id" in s:
            return _Res(scalar=self.counts.get(p.get("r"), 0))
        raise AssertionError(f"SQL inattendu : {s}")


@pytest.fixture
def _manifeste(monkeypatch):
    from labuse import runs
    monkeypatch.setattr(runs, "current", lambda: "servi")
    monkeypatch.setattr(runs, "precedent", lambda: "precedent")


def test_rollback_indetermine_si_manifeste_absent(_manifeste):
    rep = verify_rollback_manifeste(session=_FakeConn(existe=False))
    assert rep["statut"] == "INDETERMINE"


def test_rollback_ok_sans_candidat(_manifeste):
    conn = _FakeConn(score_runs=("servi", "precedent"), counts={"servi": 1000, "precedent": 990})
    rep = verify_rollback_manifeste(session=conn)
    assert rep["statut"] == "OK" and rep["n_servi"] == 1000 and rep["n_precedent"] == 990


def test_rollback_impossible_sans_precedent(_manifeste):
    """Un seul run au manifeste (ou précédent absent des scores) → RollbackImpossibleError."""
    with pytest.raises(RollbackImpossibleError, match="ROLLBACK IMPOSSIBLE"):
        verify_rollback_manifeste(session=_FakeConn(resid_runs=1, score_runs=("servi",)))


def test_candidat_vide_bloque(_manifeste):
    conn = _FakeConn(score_runs=("servi", "precedent"),
                     counts={"servi": 1000, "precedent": 990, "cand": 0})
    with pytest.raises(RollbackImpossibleError, match="CANDIDAT VIDE"):
        verify_rollback_manifeste(candidate="cand", session=conn)


def test_candidat_ecart_alerte_non_bloquant(_manifeste):
    conn = _FakeConn(score_runs=("servi", "precedent"),
                     counts={"servi": 1000, "precedent": 990, "cand": 500})   # −50 % → écart
    rep = verify_rollback_manifeste(candidate="cand", session=conn)
    assert rep["statut"] == "ECART" and rep["ecart_servi_pct"] == 50.0


def test_candidat_coherent_ok(_manifeste):
    conn = _FakeConn(score_runs=("servi", "precedent"),
                     counts={"servi": 1000, "precedent": 990, "cand": 1010})  # +1 % → cohérent
    rep = verify_rollback_manifeste(candidate="cand", session=conn)
    assert rep["statut"] == "OK" and rep["n_candidate"] == 1010
