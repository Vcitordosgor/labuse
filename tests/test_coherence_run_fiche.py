"""FIX-FICHE F5 — garde des DEUX pointeurs de run de la fiche (cascade vs v2), sans DB.

La fiche lit la cascade (`dryrun_parcel_evaluations.run_label` = Q_A_RUN_LABEL) ET le score v2
(`p_score_v2_runs.run_id`, épinglé au même label). Si le label servi est présent en cascade mais
ABSENT côté v2, le verdict de fiche retombe SILENCIEUSEMENT sur le legacy. La garde le crie.
"""
from __future__ import annotations

from labuse import bascule_gardes as bg


class _Res:
    def __init__(self, scalar=None):
        self._s = scalar
    def scalar(self):
        return self._s


class _FakeConn:
    """casc / v2 : None = table absente ; True/False = présence du run servi dans la table."""
    def __init__(self, casc, v2):
        self.casc, self.v2 = casc, v2
    def execute(self, clause, *a, **k):
        sql = str(clause)
        if "to_regclass('dryrun_parcel_evaluations')" in sql:
            return _Res(None if self.casc is None else "dryrun_parcel_evaluations")
        if "to_regclass('p_score_v2_runs')" in sql:
            return _Res(None if self.v2 is None else "p_score_v2_runs")
        if "dryrun_parcel_evaluations" in sql and "run_label" in sql:
            return _Res(1 if self.casc else None)
        if "p_score_v2_runs" in sql and "run_id" in sql:
            return _Res(1 if self.v2 else None)
        return _Res()


def test_ok_quand_les_deux_portent_le_run():
    assert bg.check_coherence_run_fiche(session=_FakeConn(casc=True, v2=True))["statut"] == "OK"


def test_v2_absent_crie_le_repli_legacy_silencieux():
    # LE cas F5 : run servi en cascade, mais pas de run v2 → verdict de fiche en repli legacy muet.
    r = bg.check_coherence_run_fiche(session=_FakeConn(casc=True, v2=False))
    assert r["statut"] == "V2_ABSENT"


def test_cascade_absente():
    assert bg.check_coherence_run_fiche(session=_FakeConn(casc=False, v2=True))["statut"] == "CASCADE_ABSENT"


def test_les_deux_absents():
    assert bg.check_coherence_run_fiche(session=_FakeConn(casc=False, v2=False))["statut"] == "LES_DEUX_ABSENTS"


def test_indetermine_si_table_absente():
    assert bg.check_coherence_run_fiche(session=_FakeConn(casc=None, v2=None))["statut"] == "INDETERMINE"
