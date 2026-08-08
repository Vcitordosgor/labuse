"""M-A — vérification déterminisme + atomicité du build V (parcel_v_score) sur la base réelle.

Validation #1 : deux builds successifs → diff vide (hors computed_at).
Validation #2 : une erreur injectée APRÈS le DELETE, AVANT le COPY, laisse la table intacte
                (jamais vide ni partielle) — grâce au DELETE+COPY en une seule transaction.

Usage : PYTHONPATH=src python reports/m-a-atomicite/verif_build_v.py
(nécessite la base labuse peuplée ; ~20 s par build).
"""
from __future__ import annotations

from unittest import mock

from sqlalchemy import text

from labuse.db import session_scope
from labuse.scoring import score_v

_COLS = ("parcelle_id, v_score, v_band, v_coverage, v_confidence, "
         "owner_type, owner_siren, owner_denomination, signals")


def _state():
    with session_scope() as s:
        n = s.execute(text("SELECT count(*) FROM parcel_v_score")).scalar()
        chk = s.execute(text(
            "SELECT md5(string_agg(parcelle_id||coalesce(v_score::text,'')||"
            "coalesce(signals::text,''), '|' ORDER BY parcelle_id)) FROM parcel_v_score")).scalar()
    return n, chk


def _build():
    with session_scope() as s:
        score_v.compute_all(s, log=lambda *a: None)


def determinisme():
    _build()
    with session_scope() as s:
        s.execute(text("DROP TABLE IF EXISTS tmp_va"))
        s.execute(text("CREATE TABLE tmp_va AS SELECT * FROM parcel_v_score"))
        s.commit()
    _build()
    with session_scope() as s:
        a = s.execute(text(f"SELECT count(*) FROM (SELECT {_COLS} FROM tmp_va "
                           f"EXCEPT SELECT {_COLS} FROM parcel_v_score) x")).scalar()
        b = s.execute(text(f"SELECT count(*) FROM (SELECT {_COLS} FROM parcel_v_score "
                           f"EXCEPT SELECT {_COLS} FROM tmp_va) x")).scalar()
        s.execute(text("DROP TABLE IF EXISTS tmp_va")); s.commit()
    print(f"[#1 DÉTERMINISME] build1\\build2={a} build2\\build1={b} -> "
          f"{'DIFF VIDE ✔' if a == b == 0 else 'DIFF NON VIDE ✗'}")


def atomicite():
    before = _state()

    class Boom(RuntimeError):
        pass

    class FakeDT:   # datetime.now() est appelé APRÈS le DELETE, AVANT le COPY
        @staticmethod
        def now(*a, **k):
            raise Boom("panne injectée entre DELETE et COPY")

    raised = False
    try:
        with mock.patch.object(score_v, "datetime", FakeDT):
            with session_scope() as s:
                score_v.compute_all(s, log=lambda *a: None)
    except Boom:
        raised = True
    after = _state()
    ok = raised and after == before and after[0] > 0
    print(f"[#2 ATOMICITÉ] avant={before[0]} après={after[0]} checksum_identique="
          f"{after[1] == before[1]} -> {'TABLE INTACTE ✔' if ok else '✗'}")


if __name__ == "__main__":
    determinisme()
    atomicite()
