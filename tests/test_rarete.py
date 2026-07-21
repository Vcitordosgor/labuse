"""O9 — PIPELINE DE RARETÉ : horizon = reste ZAN / rythme conso, projection Estimé à caveat large.

Rythme nul → non projetable (None) ; reste ≤ 0 → budget dépassé (0) ; jamais un horizon inventé.
"""
from __future__ import annotations

from labuse.api import rarete as r


def test_horizon_normal():
    assert r._horizon(30.0, 10.0) == 3.0     # 30 ha restants / 10 ha/an = 3 ans


def test_horizon_rythme_nul_non_projetable():
    assert r._horizon(30.0, 0) is None
    assert r._horizon(30.0, None) is None


def test_horizon_budget_depasse():
    assert r._horizon(-5.0, 10.0) == 0.0     # reste négatif → déjà dépassé


def test_horizon_reste_absent():
    assert r._horizon(None, 10.0) is None


def test_caveat_large_present():
    assert "Estimé" in r.CAVEAT and "rythme supposé constant" in r.CAVEAT
    assert "date couperet" in r.CAVEAT       # ne prétend pas fixer une date


def test_compute_vide_si_table_absente(db_session):
    # base de test sans commune_conso_enaf → liste vide, jamais un crash
    out = r.compute_rarete(db_session)
    assert isinstance(out, list)
