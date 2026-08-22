"""M135 — garde-fous du versionnement de parcel_residuel (le run servi est immuable)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.faisabilite import residuel_runs as rr


def _reset(engine):
    with engine.begin() as c:
        rr.ensure_runs_schema(c)
        c.execute(text("DELETE FROM residuel_runs"))
        c.execute(text("INSERT INTO residuel_runs (run_seq, label, is_served) "
                       "VALUES (1, 'servi', true), (2, 'neuf', false)"))


def test_ecriture_run_servi_refusee(engine):
    """Contrôle M135 : écrire dans le run SERVI est une ERREUR (pas un warning)."""
    _reset(engine)
    with engine.connect() as c:
        with pytest.raises(rr.ServedRunWriteError):
            rr.assert_writable(c, 1)          # run 1 = servi → refusé
        rr.assert_writable(c, 2)              # run 2 = neuf → autorisé (ne lève pas)


def test_bascule_reversible(engine):
    """Bascule + RETOUR : le service pointe le run désigné, réversible en un geste symétrique."""
    _reset(engine)
    with engine.begin() as c:
        rr.set_served(c, 2)
    with engine.connect() as c:
        assert rr.served_run_seq(c) == 2
    with engine.begin() as c:
        rr.set_served(c, 1)                   # retour
    with engine.connect() as c:
        assert rr.served_run_seq(c) == 1


def test_purge_run_servi_refusee(engine):
    _reset(engine)
    with pytest.raises(rr.ServedRunWriteError):
        with engine.begin() as c:
            rr.purge_run(c, 1)                # run servi → refusé


def test_purge_run_epingle_refusee(engine):
    _reset(engine)
    with engine.begin() as c:
        c.execute(text("UPDATE residuel_runs SET is_pinned=true WHERE run_seq=2"))
    with pytest.raises(RuntimeError):
        with engine.begin() as c:
            rr.purge_run(c, 2)               # run épinglé → refusé


def test_run_seq_entier_monotone(engine):
    """Désignation par entier monotone — jamais un tri lexical (dette §8 : q_v9 > q_v10)."""
    _reset(engine)
    with engine.begin() as c:
        seq = rr.next_run_seq(c)
    assert seq == 3 and isinstance(seq, int)
