"""M48 — garde de péremption des tuiles (classification, sans DB).

Attrape le trou constaté M48 : une bascule qui re-score le run servi SANS rejouer `build-mvt`
laisse `mvt_parcels` en arrière → la carte sert des tiers/SDP périmés. La garde compare la date
de build des tuiles au dernier calcul amont (score/résiduel) ; bruyante, JAMAIS bloquante.
"""
from __future__ import annotations

import datetime

from labuse import bascule_gardes as bg


class _Res:
    def __init__(self, first=None, scalar=None):
        self._first, self._scalar = first, scalar
    def first(self):
        return self._first
    def scalar(self):
        return self._scalar


class _Row:
    def __init__(self, run, updated_at):
        self.run, self.updated_at = run, updated_at


class _FakeConn:
    """Répond aux 3 requêtes de la garde selon le SQL (mvt_meta / p_score_v2 / parcel_residuel)."""
    def __init__(self, mvt_at, score_at, resid_at, run="q_v8_calibre"):
        self.mvt_at, self.score_at, self.resid_at, self.run = mvt_at, score_at, resid_at, run
    def execute(self, clause, *a, **k):
        sql = str(clause)
        if "mvt_meta" in sql and "updated_at" in sql:
            return _Res(first=_Row(self.run, self.mvt_at) if self.mvt_at else None)
        if "parcel_p_score_v2" in sql:
            return _Res(scalar=self.score_at)
        if "parcel_residuel" in sql:
            return _Res(scalar=self.resid_at)
        return _Res()


_T0 = datetime.datetime(2026, 8, 5, 23, 29, tzinfo=datetime.timezone.utc)
_T1 = datetime.datetime(2026, 8, 7, 0, 17, tzinfo=datetime.timezone.utc)


def test_ok_quand_tuiles_posterieures_a_l_amont():
    r = bg.check_peremption_tuiles(session=_FakeConn(mvt_at=_T1, score_at=_T0, resid_at=_T0))
    assert r["ok"] is True and r["retard_min"] is not None and r["retard_min"] <= 0


def test_perimees_quand_re_score_posterieur_au_build():
    # exactement le cas M39 : tuiles 05/08, re-score 07/08
    r = bg.check_peremption_tuiles(session=_FakeConn(mvt_at=_T0, score_at=_T1, resid_at=_T0))
    assert r["ok"] is False and r["retard_min"] > 0


def test_perimees_via_residuel_seul():
    r = bg.check_peremption_tuiles(session=_FakeConn(mvt_at=_T0, score_at=_T0, resid_at=_T1))
    assert r["ok"] is False


def test_absentes_quand_pas_de_mvt_meta():
    r = bg.check_peremption_tuiles(session=_FakeConn(mvt_at=None, score_at=_T1, resid_at=_T1))
    assert r["ok"] is False and r["mvt_at"] is None


def test_garde_ne_leve_jamais():
    for fc in (_FakeConn(_T0, _T1, _T1), _FakeConn(None, _T1, None), _FakeConn(_T1, None, None)):
        bg.check_peremption_tuiles(session=fc)  # ne lève pas
