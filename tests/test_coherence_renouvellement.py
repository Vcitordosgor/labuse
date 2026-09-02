"""M47 — garde de cohérence du segment Renouvellement (classification des statuts, sans DB).

`check_coherence_renouvellement` oppose le(s) run_label présent(s) dans `parcel_renouvellement`
au run SERVI. On teste les 4 issues (OK / PÉRIMÉE / MÉLANGÉE / ABSENTE) avec une session factice —
la garde est bruyante mais JAMAIS bloquante (elle ne lève pas), donc `ok=False` sans exception.
"""
from __future__ import annotations

import pytest

from labuse import bascule_gardes as bg

_SERVI = "q_v8_calibre"


class _FakeResult:
    def __init__(self, scalar=None, rows=None):
        self._s, self._r = scalar, rows or []

    def scalar(self):
        return self._s

    def all(self):
        return self._r


class _FakeSession:
    """Renvoie `exists` pour le to_regclass, `rows` pour le GROUP BY run_label."""
    def __init__(self, exists, rows):
        self.exists, self.rows = exists, rows

    def execute(self, clause, *a, **k):
        return _FakeResult(scalar=self.exists) if "to_regclass" in str(clause) \
            else _FakeResult(rows=self.rows)


@pytest.fixture(autouse=True)
def _fixe_run_servi(monkeypatch):
    # SUITE-1 S3 — la garde lit le run servi via runs.current() (plus de constante d'import) : on l'injecte là.
    monkeypatch.setattr("labuse.runs.current", lambda: _SERVI)


def test_statut_ok_quand_table_sur_le_run_servi():
    r = bg.check_coherence_renouvellement(session=_FakeSession(True, [(_SERVI, 67258)]))
    assert r["ok"] is True and r["statut"] == "OK"
    assert r["servi"] == _SERVI and r["runs"] == {_SERVI: 67258}


def test_statut_perimee_quand_run_different():
    r = bg.check_coherence_renouvellement(session=_FakeSession(True, [("q_v7_defisc", 68000)]))
    assert r["ok"] is False and r["statut"] == "PÉRIMÉE"


def test_statut_melangee_quand_plusieurs_runs():
    r = bg.check_coherence_renouvellement(
        session=_FakeSession(True, [(_SERVI, 1), ("q_v7_defisc", 2)]))
    assert r["ok"] is False and r["statut"] == "MÉLANGÉE"


def test_statut_absente_quand_table_manque():
    r = bg.check_coherence_renouvellement(session=_FakeSession(False, []))
    assert r["ok"] is False and r["statut"] == "ABSENTE" and r["runs"] == {}


def test_garde_ne_leve_jamais():
    # régime check_fraicheur : bruyante, NON bloquante — aucune issue ne doit lever.
    for fs in (_FakeSession(True, [("q_v7_defisc", 5)]), _FakeSession(False, [])):
        bg.check_coherence_renouvellement(session=fs)  # ne lève pas
