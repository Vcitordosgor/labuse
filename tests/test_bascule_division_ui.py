"""BASCULE-DIVISION-UI — le bouton Basculer propose de garder la division d'or sur le run servi
tant que la découpe du candidat est incomplète.

Côté backend : (1) `BasculeIn` accepte `division_run` (passé tel quel à `basculer`) ; (2)
`division_incomplete()` signale quand la découpe du candidat couvre MOINS de communes que la
division servie. Logique testée sur une fausse session (aucune DB) — on ne vise que la décision.
"""
from __future__ import annotations

import labuse.bascule_flux as bf


class _Exec:
    """Rend .scalar() successifs dans l'ordre d'une file."""
    def __init__(self, file): self._f = file
    def scalar(self): return self._f.pop(0)


class _FakeDB:
    """execute() renvoie des .scalar() scriptés : [table_existe?, n_run, table_existe?, n_servi]."""
    def __init__(self, vals): self._f = list(vals)
    def execute(self, *a, **k): return _Exec(self._f)


def _patch_manifeste(monkeypatch, division_servi):
    import labuse.manifeste as man
    monkeypatch.setattr(man, "existe", lambda: True)
    monkeypatch.setattr(man, "division_run", lambda: division_servi)


def test_incomplete_quand_candidat_moins_couvert(monkeypatch):
    _patch_manifeste(monkeypatch, "q_v19")
    # table présente ; candidat q_v20 couvre 3 communes, division servie q_v19 en couvre 24
    db = _FakeDB(["division_or_candidates", 3, "division_or_candidates", 24])
    r = bf.division_incomplete(db, "q_v20")
    assert r["incomplete"] is True
    assert r["division_run_a_garder"] == "q_v19"
    assert r["communes_decoupe_run"] == 3 and r["communes_decoupe_servies"] == 24


def test_pas_incomplete_quand_couverture_egale(monkeypatch):
    _patch_manifeste(monkeypatch, "q_v19")
    db = _FakeDB(["division_or_candidates", 24, "division_or_candidates", 24])
    assert bf.division_incomplete(db, "q_v20")["incomplete"] is False


def test_pas_incomplete_si_candidat_est_la_division_servie(monkeypatch):
    _patch_manifeste(monkeypatch, "q_v20")   # division servie == candidat
    db = _FakeDB(["division_or_candidates", 3, "division_or_candidates", 3])
    assert bf.division_incomplete(db, "q_v20")["incomplete"] is False


def test_pas_incomplete_sans_manifeste(monkeypatch):
    import labuse.manifeste as man
    monkeypatch.setattr(man, "existe", lambda: False)
    db = _FakeDB(["division_or_candidates", 0, "division_or_candidates", 0])
    assert bf.division_incomplete(db, "q_v20")["incomplete"] is False


def test_bascule_in_accepte_division_run():
    from labuse.api.dashboard import BasculeIn
    assert BasculeIn(run="q_v20", division_run="q_v19").division_run == "q_v19"
    assert BasculeIn(run="q_v20").division_run is None   # défaut : la division suit le nouveau run
