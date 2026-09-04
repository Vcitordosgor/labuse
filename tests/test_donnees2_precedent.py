"""DONNEES-2 (B4) — le run PRÉCÉDENT (retour arrière) est lu VIVANT de config/run_precedent.txt,
plus jamais figé dans une constante de module. La page Flux étiquetait le mauvais « ancien run servi »
juste après une bascule parce que `RUN_PRECEDENT` datait de l'import du process."""
from __future__ import annotations

import pytest

from labuse import runs


@pytest.fixture
def _prec_file(tmp_path, monkeypatch):
    f = tmp_path / "run_precedent.txt"
    f.write_text("# entête\nrunA\n", encoding="utf-8")
    monkeypatch.setattr(runs, "_PRECEDENT_FILE", f)
    monkeypatch.delenv("LABUSE_RUN_PRECEDENT", raising=False)
    runs.invalidate()
    return f


def test_precedent_relu_vivant_apres_reecriture(_prec_file):
    assert runs.precedent() == "runA"
    # une bascule réécrit le fichier ; après invalidate() la lecture suivante voit la nouvelle valeur
    _prec_file.write_text("# entête\nrunB\n", encoding="utf-8")
    runs.invalidate()
    assert runs.precedent() == "runB"


def test_precedent_override_dev(_prec_file, monkeypatch):
    monkeypatch.setenv("LABUSE_RUN_PRECEDENT", "runOverride")
    assert runs.precedent() == "runOverride"


def test_run_precedent_constante_est_dynamique(_prec_file):
    # score_v_constants.RUN_PRECEDENT (accès par ATTRIBUT) délègue au pointeur vivant runs.precedent()
    from labuse.scoring import score_v_constants as sc
    assert sc.RUN_PRECEDENT == "runA"
    _prec_file.write_text("# entête\nrunZ\n", encoding="utf-8")
    runs.invalidate()
    assert sc.RUN_PRECEDENT == "runZ"
