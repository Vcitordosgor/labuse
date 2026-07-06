"""Dry-run scoring (étages 1+2) — ABF→UNKNOWN, traçabilité base+Σ=score, isolation du live.

Tests unitaires ne nécessitant PAS de géométrie (pyproj) : couche ABF via ctx factice, writer
dry-run via verdicts synthétiques. (Les tests cascade géométriques complets sont bloqués par la
dette pyproj connue — hors périmètre.)
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.cascade.base import positive, soft_flag, unknown
from labuse.cascade.layers.phase1 import AbfLayer
from labuse.cascade.pipeline import _persist_dryrun
from labuse.enums import CascadeVerdict, Severity
from labuse.scoring import OpportunityResult, compute_opportunity

# ───────────────────────── ABF → UNKNOWN (config-driven) ─────────────────────────

class _Ctx:
    """EvalContext factice : présence + intersections paramétrables, source_id neutre."""

    def __init__(self, present=True, covers=True):
        self._present, self._covers = present, covers

    def kind_present(self, kind):
        return self._present

    def intersections(self, pid, kind):
        class _I:
            coverage = 1.0 if self._covers else 0.0
        return [_I()] if self._covers else []

    def source_id(self, name):
        return None


class _Parcel:
    id = 1


def test_abf_as_unknown_true():
    v = AbfLayer().evaluate(_Parcel(), _Ctx(covers=True),
                            {"spatial_kind": "abf", "as_unknown": True, "detail": "abords MH"})
    assert v.result == CascadeVerdict.UNKNOWN          # incertitude, PAS un malus
    assert "abords" in v.detail.lower()


def test_abf_as_unknown_false_reste_soft_flag():
    v = AbfLayer().evaluate(_Parcel(), _Ctx(covers=True),
                            {"spatial_kind": "abf", "as_unknown": False, "severity": "faible", "detail": "x"})
    assert v.result == CascadeVerdict.SOFT_FLAG        # bascule possible via config


def test_abf_hors_perimetre_pass():
    v = AbfLayer().evaluate(_Parcel(), _Ctx(covers=False),
                            {"spatial_kind": "abf", "as_unknown": True, "detail": "x"})
    assert v.result == CascadeVerdict.PASS


def test_unknown_ne_donne_aucun_point():
    r = compute_opportunity([unknown("abf", "abords MH")])
    assert r.weights == [0.0] and not r.hard_exclude   # UNKNOWN = 0 point d'opportunité


# ───────────────────────── writer dry-run : traçabilité + isolation (DB) ─────────────────────────

@pytest.mark.db
def test_persist_dryrun_tracabilite_et_isolation(db_session):
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom) VALUES "
        "('97415000ZZ9001','Saint-Paul', ST_SetSRID(ST_GeomFromText('POLYGON((55.2 -21,55.201 -21,55.201 -20.999,55.2 -20.999,55.2 -21))'),4326))"))
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97415000ZZ9001'")).scalar()
    live_before = db_session.execute(text("SELECT count(*) FROM cascade_results")).scalar()

    class _P:
        id = pid
    # verdicts synthétiques : 1 pénalité (soft_flag moyen) + 1 bonus (positive) → poids -6 et +8
    verdicts = [soft_flag("risques", "aléa moyen", Severity.MOYEN, source="X"),
                positive("friche", "friche avec projet", "friche", source="Cerema")]
    opp = OpportunityResult(score=52, hard_exclude=False, exclude_kind=None,
                            has_fort_flag=False, weights=[-6.0, 8.0])

    class _Comp:
        score = 40
    class _Status:
        value = "opportunite"

    _persist_dryrun(db_session, _Ctx(), "t_iso", _P(), verdicts, _Comp(), opp, _Status(), "rulesv1")
    db_session.flush()

    # 2 lignes cascade dry-run + 1 éval dry-run
    assert db_session.execute(text(
        "SELECT count(*) FROM dryrun_cascade_results WHERE run_label='t_iso' AND parcel_id=:p"), {"p": pid}).scalar() == 2
    row = db_session.execute(text(
        "SELECT opportunity_base, opportunity_score FROM dryrun_parcel_evaluations WHERE run_label='t_iso' AND parcel_id=:p"),
        {"p": pid}).first()
    somme = db_session.execute(text(
        "SELECT sum(weight_applied) FROM dryrun_cascade_results WHERE run_label='t_iso' AND parcel_id=:p"), {"p": pid}).scalar()
    assert row[0] + somme == row[1]                    # base + Σ = score (traçabilité)
    # isolation : le live cascade_results n'a pas bougé
    assert db_session.execute(text("SELECT count(*) FROM cascade_results")).scalar() == live_before


@pytest.mark.db
def test_persist_dryrun_idempotent(db_session):
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, geom) VALUES "
        "('97415000ZZ9002','Saint-Paul', ST_SetSRID(ST_GeomFromText('POLYGON((55.2 -21,55.201 -21,55.201 -20.999,55.2 -20.999,55.2 -21))'),4326))"))
    pid = db_session.execute(text("SELECT id FROM parcels WHERE idu='97415000ZZ9002'")).scalar()

    class _P:
        id = pid
    class _Comp:
        score = 40
    class _Status:
        value = "opportunite"
    opp = OpportunityResult(score=50, hard_exclude=False, exclude_kind=None, has_fort_flag=False, weights=[0.0])
    v = [soft_flag("risques", "x", Severity.FAIBLE)]
    _persist_dryrun(db_session, _Ctx(), "t_idem", _P(), v, _Comp(), opp, _Status(), "r")
    db_session.flush()   # 1er run persisté (comme un chunk committé)
    _persist_dryrun(db_session, _Ctx(), "t_idem", _P(), v, _Comp(), opp, _Status(), "r")  # re-run : DELETE-first
    db_session.flush()
    assert db_session.execute(text(
        "SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label='t_idem' AND parcel_id=:p"), {"p": pid}).scalar() == 1
