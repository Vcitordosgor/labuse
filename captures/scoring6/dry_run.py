#!/usr/bin/env python3
"""SCORING-6 §3 — DRY-RUN (base `labuse`, lecture seule sauf table candidate score_labuse).

Pas de run île entière (mandat) : Score + Signal + cascade v2 sur (1) les 30 témoins,
(2) la commune de Saint-Paul entière. Produit les tableaux du rapport SCORING-6.

    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
    PYTHONPATH=src <venv>/python captures/scoring6/dry_run.py
"""
import csv
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import text

from labuse.db import engine, session_scope
from labuse.scoring.cascade_v2 import reclasser_batch
from labuse.scoring.score_labuse import charger_bareme, score_batch
from labuse.scoring.score_labuse_combine import (combiner, ensure_schema,
                                                 ordonner, persister)
from labuse.scoring.signal_mutation import signal_niveau

TEMOINS_CSV = Path("/Users/openclaw/Desktop/labuse-scoring5/reports/scoring-5/TEMOINS.csv")
CASCADE = "q_v13_sources1"
SIGNAL = "q_v14"                 # stand-in du Signal (le fit q_v15 est un geste de Vic)
RUN = "scoring6-dryrun"


def temoins(s, bareme, version):
    ref = {r["idu"]: r for r in csv.DictReader(TEMOINS_CSV.open())}
    idmap = {r.idu: r.id for r in s.execute(
        text("SELECT id, idu FROM parcels WHERE idu = ANY(:x)"), {"x": list(ref)})}
    pids = [idmap[i] for i in ref if i in idmap]
    lignes = {l.parcel_id: l for l in combiner(
        s, pids, RUN, cascade_label=CASCADE, signal_run_id=SIGNAL, signal_recette="q_v15")}
    ok = 0
    print("\n== 30 TÉMOINS (score, bande, signal) — reproduction TEMOINS.csv ==")
    print(f"{'idu':<16}{'cat':<10}{'attendu':>8}{'score':>7}{'bande':>6}{'signal':>8}")
    for idu, exp in ref.items():
        l = lignes.get(idmap.get(idu))
        exp_s = None if exp["non_calculable"] == "oui" else int(exp["score"] or 0)
        if l and l.score == exp_s and l.non_calculable == (exp["non_calculable"] == "oui"):
            ok += 1
        niv = l.signal_niveau if l else "—"
        print(f"{idu:<16}{exp['categorie']:<10}{str(exp_s):>8}{str(l.score if l else '—'):>7}"
              f"{(l.bande if l else '—'):>6}{str(niv):>8}")
    print(f"→ {ok}/{len(ref)} témoins reproduits exactement")


def saint_paul(s, bareme, version):
    ids = [r[0] for r in s.execute(text(
        "SELECT id FROM parcels WHERE commune='Saint-Paul' ORDER BY idu"))]
    print(f"\n== SAINT-PAUL — {len(ids)} parcelles ==")
    t0 = time.time()
    bandes, causes = Counter(), Counter()
    cls = Counter()
    excl_v2 = 0
    CH = 5000
    with engine().begin() as c:
        ensure_schema(c)
    for k in range(0, len(ids), CH):
        chunk = ids[k:k + CH]
        with session_scope() as ss:
            lignes = combiner(ss, chunk, RUN, cascade_label=CASCADE,
                              signal_run_id=SIGNAL, signal_recette="q_v15")
            persister(ss, RUN, lignes, cascade_label=CASCADE, signal_run_id=SIGNAL,
                      communes="Saint-Paul")
            for l in lignes:
                bandes[l.bande] += 1
                if l.non_calculable:
                    causes[l.cause] += 1
                if l.cascade_exclue:
                    excl_v2 += 1
            recl = reclasser_batch(ss, chunk, CASCADE)
            for r in recl.values():
                for v in r.exclusions:
                    cls["A"] += 1
                for v in r.penalites:
                    cls["B"] += 1
                for v in r.infos:
                    cls["C"] += 1
                for v in r.supprimes:
                    cls["D"] += 1
    dt = time.time() - t0
    print(f"  temps : {dt:.1f}s ({1000*dt/max(1,len(ids)):.2f} ms/parcelle)")
    print("  distribution des bandes :")
    for b in ("A", "B", "C", "D", "NC"):
        print(f"    {b}: {bandes.get(b, 0)}")
    print(f"  NC par cause : {dict(causes)}")
    # cascade v2 : effectifs de classe (verdicts) + exclusions v2 vs hard-excludes v1
    hard_v1 = s.execute(text(
        "SELECT count(DISTINCT parcel_id) FROM dryrun_cascade_results "
        "WHERE run_label=:l AND result='HARD_EXCLUDE' AND parcel_id = ANY(:ids)"),
        {"l": CASCADE, "ids": ids}).scalar()
    print(f"  cascade v2 — verdicts par classe : {dict(cls)}")
    print(f"  parcelles exclues : v1 (HARD_EXCLUDE q_v13_sources1) = {hard_v1} · "
          f"v2 (classe A seule) = {excl_v2}")
    # garde-fou : toute parcelle a une bande
    manque = s.execute(text(
        "SELECT count(*) FROM score_labuse WHERE run_label=:r AND bande IS NULL"),
        {"r": RUN}).scalar()
    print(f"  garde : parcelles sans bande = {manque} (doit être 0)")


def main():
    bareme, version = charger_bareme()
    print(f"score_version = {version}")
    with session_scope() as s:
        temoins(s, bareme, version)
    with session_scope() as s:
        saint_paul(s, bareme, version)


if __name__ == "__main__":
    main()
