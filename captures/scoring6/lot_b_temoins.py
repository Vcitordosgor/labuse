#!/usr/bin/env python3
"""SCORING-6 lot B — reproduction des 30 témoins (base `labuse`, lecture seule, jetable).

Vérifie que `score_batch` reproduit EXACTEMENT les scores de reports/scoring-5/TEMOINS.csv
(résiduel servi run_seq 2 pré-calibrage + accès du run cascade q_v13_sources1).

    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
    PYTHONPATH=src <venv>/python captures/scoring6/lot_b_temoins.py
"""
import csv
from pathlib import Path

from sqlalchemy import text

from labuse.db import session_scope
from labuse.scoring.score_labuse import charger_bareme, score_batch

TEMOINS = Path("/Users/openclaw/Desktop/labuse-scoring5/reports/scoring-5/TEMOINS.csv")


def main() -> None:
    ref = {r["idu"]: r for r in csv.DictReader(TEMOINS.open())}
    bareme, version = charger_bareme()
    print("score_version :", version)
    with session_scope() as s:
        idmap = {r.idu: r.id for r in s.execute(
            text("SELECT id, idu FROM parcels WHERE idu = ANY(:x)"), {"x": list(ref)})}
        pids = [idmap[i] for i in ref if i in idmap]
        res = {r.parcel_id: r for r in score_batch(
            s, pids, "scoring6-dryrun", cascade_label="q_v13_sources1",
            bareme=bareme, version=version)}
    ok = diff = 0
    for idu, exp in ref.items():
        r = res.get(idmap.get(idu))
        exp_score = None if exp["non_calculable"] == "oui" else int(exp["score"] or 0)
        if r and r.score == exp_score and r.non_calculable == (exp["non_calculable"] == "oui"):
            ok += 1
        else:
            diff += 1
            print(f"  DIFF {idu}: attendu {exp_score} / obtenu {r.score if r else '—'}")
    print(f"== {ok}/{len(ref)} témoins reproduits, {diff} écart(s) ==")


if __name__ == "__main__":
    main()
