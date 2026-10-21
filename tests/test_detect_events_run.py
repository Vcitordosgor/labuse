"""FIX detect-events — l'import mort `from .api.tiles import RUN` (la constante `RUN` a été
retirée de `api.tiles` lors du refactor vers `runs.current()`) faisait planter le wrapper CLI en
`ImportError` à l'invocation. Régression : la commande doit s'exécuter, et le run servi doit être
lu via `runs.current()`. Test unitaire PUR (la couche DB est monkeypatchée — on ne vise que le
câblage/l'import, pas le calcul d'événements)."""
from __future__ import annotations

import sqlalchemy.orm
from typer.testing import CliRunner

runner = CliRunner()


class _DummySession:
    """Remplace sqlalchemy.orm.Session : `with Session(engine()) as s: … s.commit()` no-op."""
    def __init__(self, *a, **k): ...
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def commit(self): ...


def _patch_db(monkeypatch, detect, *, prev="q_prev"):
    from labuse import runs
    from labuse.api import events
    monkeypatch.setattr(sqlalchemy.orm, "Session", _DummySession)
    monkeypatch.setattr("labuse.db.engine", lambda: object())
    monkeypatch.setattr(events, "ensure_tables", lambda *a, **k: None)
    monkeypatch.setattr(events, "run_precedent_servi", lambda *a, **k: prev)
    monkeypatch.setattr(events, "detect_events", detect)
    monkeypatch.setattr(runs, "current", lambda: "q_served")


def test_detect_events_ne_plante_plus_sur_import_mort(monkeypatch):
    from labuse import cli
    cap = {}
    def detect(s, run_from, run_to, demo=False, rattrapage=False):
        cap.update(run_from=run_from, run_to=run_to, demo=demo, rattrapage=rattrapage)
        return {"bascule": 0, "bodacc": 0, "permis": 0, "reprises": 0}
    _patch_db(monkeypatch, detect)

    res = runner.invoke(cli.app, ["detect-events", "--run-to", "q_cible"])
    assert res.exit_code == 0, (res.output + repr(res.exception))
    # run_from par défaut = run servi (ex-constante RUN) lu via runs.current()
    assert cap["run_from"] == "q_served"
    assert cap["run_to"] == "q_cible"
    assert cap["rattrapage"] is False


def test_detect_events_rattrapage_lit_le_run_servi(monkeypatch):
    from labuse import cli
    cap = {}
    def detect(s, run_from, run_to, demo=False, rattrapage=False):
        cap.update(run_from=run_from, run_to=run_to, rattrapage=rattrapage)
        return {"bascule": 0}
    _patch_db(monkeypatch, detect, prev="q_prev")

    res = runner.invoke(cli.app, ["detect-events", "--rattrapage"])
    assert res.exit_code == 0, (res.output + repr(res.exception))
    # rattrapage : run_from = précédent (table), run_to = run servi (runs.current())
    assert cap["run_from"] == "q_prev"
    assert cap["run_to"] == "q_served"
    assert cap["rattrapage"] is True


def test_tiles_n_exporte_plus_RUN():
    """Garde-fou : si quelqu'un réintroduit `RUN` dans api.tiles, le refactor a régressé."""
    from labuse.api import tiles
    assert not hasattr(tiles, "RUN"), "api.tiles.RUN est censé avoir disparu (refactor runs.current())"
