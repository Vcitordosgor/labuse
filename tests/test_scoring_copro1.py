"""SCORING-COPRO-1 — gardes des trois corrections du run q_v21.

- NU-E-010 (copropriété hors palier actionnable) : testé dans test_paliers1.py (fonction pure).
- NU-E-011 (fraction/×N jamais servis pour une copro) : testé dans test_p_v2_api.py (service).
- NU-E-015 (étage 0 servi == étage 0 du classement) : la garde `check_etage0_aligne` (ci-dessous).
- PPR (code `i` + toutes les zones rouges reconnus par la cascade) : test `reel` ci-dessous +
  parité de classification couverte par test_ppr_unique.py.
"""
from __future__ import annotations

import contextlib
import os

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db


def _seed_run(session, run_id: str, etage0_run: str | None):
    import json
    params = {"recette": "q_v15"}
    if etage0_run is not None:
        params["etage0_run"] = etage0_run
    session.execute(text(
        "INSERT INTO p_score_v2_runs (run_id, model_version, model_sha256, params, n_parcelles) "
        "VALUES (:r, 'q_v15', 'sha', :p, 1)"), {"r": run_id, "p": json.dumps(params)})
    session.flush()


def test_etage0_aligne_ok(db_session, monkeypatch):
    """NU-E-015 — cascade servie == cascade sur laquelle le run a été scoré → OK."""
    from labuse import bascule_gardes, runs
    _seed_run(db_session, "q_v21", etage0_run="q_v21_sources")
    monkeypatch.setattr(runs, "current", lambda: "q_v21")
    monkeypatch.setattr(runs, "cascade", lambda: "q_v21_sources")
    out = bascule_gardes.check_etage0_aligne(session=db_session)
    assert out["statut"] == "OK"


def test_etage0_desaligne_crie(db_session, monkeypatch):
    """NU-E-015 — le run servi a été scoré sur une AUTRE cascade que celle servie → DÉSALIGNÉ
    (le désalignement q_v20 : scoré sur q_v19_sources, servi sous un autre pointeur)."""
    from labuse import bascule_gardes, runs
    _seed_run(db_session, "q_v20", etage0_run="q_v19_sources")
    monkeypatch.setattr(runs, "current", lambda: "q_v20")
    monkeypatch.setattr(runs, "cascade", lambda: "q_v21_sources")
    out = bascule_gardes.check_etage0_aligne(session=db_session)
    assert out["statut"] == "DESALIGNE"
    assert out["etage0_score"] == "q_v19_sources"


# ───────────────────────────── PPR : code `i` reconnu par la CASCADE (reel) ─────────────────────
@contextlib.contextmanager
def _app_session():
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine
    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    try:
        yield s
    finally:
        s.close()
        eng.dispose()


@pytest.mark.reel
def test_cascade_exclut_zone_i_100pct_rouge():
    """NU-D-001 / SCORING-COPRO-1 — une parcelle 100 % en zone PPR code `i` (Saint-Philippe) est
    désormais ÉCARTÉE par la cascade (PPR rouge, inconstructible), via la lecture unique
    `labuse.ppr`. Avant : le `i` tombait en « périmètre, zonage inconnu, jamais d'exclusion ».
    Témoin PPR-UNIQUE-1 : 97417000AH0053."""
    from labuse.cascade import evaluate_parcels
    with _app_session() as s:
        row = s.execute(text("SELECT id FROM parcels WHERE idu='97417000AH0053'")).first()
        if not row:
            pytest.skip("témoin 97417000AH0053 absent de la base applicative")
        out = evaluate_parcels([row[0]], s, persist=False)[0]
        status = out.status.value if hasattr(out.status, "value") else out.status
        ppr = [v for v in out.verdicts if v.layer_name == "risques" and v.exclude_kind]
        assert status == "exclue"
        assert ppr and "rouge" in ppr[0].detail.lower()
