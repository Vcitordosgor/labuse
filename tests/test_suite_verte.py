"""TESTS-1 lot 3 — la porte de la suite (suite_verte) : l'arbitrage pur, testé sans récursion."""
from __future__ import annotations

from datetime import date

import pytest

from labuse import suite_verte as sv

AUJOURDHUI = date(2026, 9, 14)


def _tol(test="tests/test_x.py::test_y", raison="parce que", depuis="2026-09-14",
         echeance="2026-09-21"):
    return sv.Tolerance(test, raison, date.fromisoformat(depuis), date.fromisoformat(echeance))


def test_echec_sans_ligne_refuse():
    v = sv.confronter(["tests/test_a.py::test_b"], [], aujourd_hui=AUJOURDHUI)
    assert not v.ok and "SANS ligne" in v.refus[0] and "tests/test_a.py::test_b" in v.refus[0]


def test_echec_tolere_passe_avec_avertissement():
    v = sv.confronter(["tests/test_x.py::test_y"], [_tol()], aujourd_hui=AUJOURDHUI)
    assert v.ok and not v.refus
    assert any("toléré jusqu'au 2026-09-21" in a for a in v.avertissements)


def test_tolerance_echue_refuse():
    v = sv.confronter(["tests/test_x.py::test_y"], [_tol(echeance="2026-09-13")],
                      aujourd_hui=AUJOURDHUI)
    assert not v.ok and "ÉCHUE" in v.refus[0]


def test_tolerance_morte_signalee_jamais_refusee():
    v = sv.confronter([], [_tol()], aujourd_hui=AUJOURDHUI)
    assert v.ok and any("MORTE" in a for a in v.avertissements)


def test_charger_tolerances_tableau_et_malformee(tmp_path):
    f = tmp_path / "TESTS-TOLERES.md"
    f.write_text(
        "# titre\nblabla libre\n\n| test | raison | depuis | échéance |\n|---|---|---|---|\n"
        "| tests/test_x.py::test_y | une raison | 2026-09-14 | 2026-09-21 |\n",
        encoding="utf-8")
    (tol,) = sv.charger_tolerances(f)
    assert tol.test == "tests/test_x.py::test_y" and tol.echeance == date(2026, 9, 21)
    f.write_text("| tests/test_x.py::test_y | sans dates |\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformée"):
        sv.charger_tolerances(f)
    assert sv.charger_tolerances(tmp_path / "absent.md") == []


def test_fichier_committe_se_charge():
    """Le VRAI docs/TESTS-TOLERES.md se parse — une ligne malformée committée casserait ici,
    pas au moment du déploiement."""
    from pathlib import Path
    racine = Path(__file__).resolve().parents[1]
    for t in sv.charger_tolerances(racine / sv.FICHIER_TOLERES):
        assert t.test.startswith("tests/") and t.raison.strip() and t.depuis <= t.echeance
