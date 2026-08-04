"""6ᵉ garde (Vic 04/08) : toute bascule régénère le golden dans le même geste — sans DB."""
from __future__ import annotations

import json

import pytest

from labuse.bascule_gardes import GoldenPerimeError, check_golden_regenere


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
