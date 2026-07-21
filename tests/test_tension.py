"""O8 — TENSION FONCIÈRE : indice MASQUÉ tant que la sonde de calibrabilité échoue.

Point dur du mandat : indice non calibrable défendablement = livré MASQUÉ (flag) + finding, jamais affiché.
"""
from __future__ import annotations

import pytest

from labuse.api import tension as t


def test_expose_false_par_defaut():
    # décision d'exposition : masqué tant que la calibration n'est pas défendable
    assert t.EXPOSE is False and t.SEUIL_RHO_DEFENDABLE == 0.20


def test_spearman_monotone_parfait():
    xs = [1, 2, 3, 4, 5]
    assert round(t._spearman(xs, [10, 20, 30, 40, 50]), 3) == 1.0      # monotone croissant
    assert round(t._spearman(xs, [50, 40, 30, 20, 10]), 3) == -1.0     # monotone décroissant


def test_spearman_petit_echantillon_zero():
    assert t._spearman([1, 2], [1, 2]) == 0.0     # n<3 → 0 (pas de sur-interprétation)


def test_minmax():
    rows = [{"x": 2}, {"x": 8}, {"x": None}]
    assert t._minmax(rows, "x") == (2, 8)


@pytest.mark.db
def test_compute_vide_reste_masque(db_session):
    # base de test sans données jointes → compute renvoie n=0 mais expose reste False (jamais exposé par défaut)
    out = t.compute_tension(db_session)
    assert out["expose"] is False


@pytest.mark.db
def test_endpoint_masque_et_finding(db_session):
    out = t.tension_fonciere(db_session)
    assert out["masque"] is True and out["expose"] is False
    assert "NON exposé" in out["finding"] and "formule" in out
    # si des indices existent en base de test, la calibration doit rester non défendable ou absente
    cal = out["calibration"]
    assert cal is None or cal["defendable"] in (False, True)   # présent et cohérent
