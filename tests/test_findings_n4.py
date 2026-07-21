"""NUIT N4 — finding F7 : le commit() est sorti des builders ext (délégué à l'appelant).

Testabilité gagnée : `build_copro_flags` / `build_ext_union` / `build_ext_mutations` /
`build_ext_dataset` ne committent plus — l'appelant (`rebuild_features`) commite à la frontière.
Les tests J1 existants (`test_p_model_ext_sql.py`) passent sans modification.
"""
from __future__ import annotations

import inspect

from labuse.scoring.p_model import ext_sql
from labuse.scoring.p_v2 import pipeline


def test_f7_builders_ext_ne_committent_plus():
    for fn in (ext_sql.build_copro_flags, ext_sql.build_ext_union,
               ext_sql.build_ext_mutations, ext_sql.build_ext_dataset):
        assert "session.commit()" not in inspect.getsource(fn), f"{fn.__name__} committe encore"


def test_f7_commit_a_la_frontiere():
    # l'appelant commite désormais explicitement à la frontière.
    assert "session.commit()" in inspect.getsource(pipeline.rebuild_features)
