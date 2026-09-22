#!/usr/bin/env python3
"""SCORING-6 RUN 5 dry-run — MÊME protocole que SCORING-6-DRYRUN (dryrun_r3.py), mais cette fois
le résiduel servi = run 5 (assiette RÉELLEMENT clippée, fix bâti 13d8fefd) et l'AVANT = run 3
(tout-ou-rien, déjà persisté). Ce dry-run mesure enfin l'effet de l'ASSIETTE, pas du calibrage.

  AVANT (run 3) : score_labuse run_label 'dryrun_r3' (SP) / 'dryrun_r3_temoins' / 'dryrun_r3_an3112'.
  APRÈS (run 5) : 'dryrun_r5' (SP, déjà scoré par le CLI) + 'dryrun_r5_temoins' + 'dryrun_r5_an3112'.

q_v11_m137 reste le run SERVI du scoring (candidat) ; ici on ne touche qu'au résiduel servi (run 5,
bascule faite par Vic). Aucun run île. Bandes = seuils moteur (l.bande du combiner)."""
import csv
import json
import re
import time
from collections import Counter
from pathlib import Path

from sqlalchemy import text

from labuse.db import engine, session_scope
from labuse.scoring.score_labuse import charger_bareme
from labuse.scoring.score_labuse_combine import combiner, ensure_schema, persister

TEMOINS_CSV = Path("/Users/openclaw/Desktop/labuse-scoring5/reports/scoring-5/TEMOINS.csv")
OUT = Path(__file__).resolve().parent
CASCADE = "q_v13_sources1"
SIGNAL = "q_v14"
_PCT = re.compile(r"recouvrement\s+(\d+(?:[.,]\d+)?)\s*%")
BANDES = ("A", "B", "C", "D", "NC")


def sp_bandes_transitions():
    """Saint-Paul : bandes AVANT (dryrun_r3) vs APRÈS (dryrun_r5) + matrice de transition + histo."""
    with session_scope() as s:
        av = {r.parcel_id: (r.bande, r.score) for r in s.execute(text(
            "SELECT parcel_id, bande, score FROM score_labuse WHERE run_label='dryrun_r3'"))}
        ap = {r.parcel_id: (r.bande, r.score) for r in s.execute(text(
            "SELECT parcel_id, bande, score FROM score_labuse WHERE run_label='dryrun_r5'"))}
    assert av and ap, "dryrun_r3 / dryrun_r5 manquants"
    cav, cap = Counter(b for b, _ in av.values()), Counter(b for b, _ in ap.values())
    trans, histo = Counter(), Counter()
    anomalies = []
    for pid, (bap, sap) in ap.items():
        bav, sav = av.get(pid, ("?", None))
        trans[(bav, bap)] += 1
        histo[sap if sap is not None else 0] += 1
        # anomalies : A<->NC (bascule de côté) ou saut > 2 bandes
        oi = {"A": 0, "B": 1, "C": 2, "D": 3, "NC": 4}
        if (bav in ("A", "NC")) and (bap in ("A", "NC")) and bav != bap:
            anomalies.append((pid, bav, sav, bap, sap, f"{bav}->{bap}"))
        elif bav in oi and bap in oi and bav != "NC" and bap != "NC" and abs(oi[bav] - oi[bap]) > 2:
            anomalies.append((pid, bav, sav, bap, sap, f"{bav}->{bap} (>2)"))
    return cav, cap, trans, histo, anomalies, len(ap)


def temoins():
    """30 témoins — APRÈS run 5 (dryrun_r5_temoins), AVANT = dryrun_r3_temoins (persisté, run 3)."""
    ref = {r["idu"]: r for r in csv.DictReader(TEMOINS_CSV.open())}
    with session_scope() as s:
        idmap = {r.idu: r.id for r in s.execute(
            text("SELECT id, idu FROM parcels WHERE idu = ANY(:x)"), {"x": list(ref)})}
        pids = [idmap[i] for i in ref if i in idmap]
        with engine().begin() as c:
            ensure_schema(c)
        t0 = time.time()
        lignes = combiner(s, pids, "dryrun_r5_temoins", cascade_label=CASCADE,
                          signal_run_id=SIGNAL, signal_recette="q_v15")
        dt = time.time() - t0
        persister(s, "dryrun_r5_temoins", lignes, cascade_label=CASCADE,
                  signal_run_id=SIGNAL, communes="temoins")
        av = {r.parcel_id: (r.bande, r.score, r.non_calculable) for r in s.execute(text(
            "SELECT parcel_id, bande, score, non_calculable FROM score_labuse WHERE run_label='dryrun_r3_temoins'"))}
    by = {l.parcel_id: l for l in lignes}
    rows, changed = [], []
    for idu in ref:
        pid = idmap.get(idu)
        l = by.get(pid)
        bav, sav, ncav = av.get(pid, ("?", None, None))
        ap_s = None if (l and l.non_calculable) else (l.score if l else None)
        row = dict(idu=idu, cat=ref[idu]["categorie"], av_score=sav, av_bande=bav,
                   ap_score=ap_s, ap_bande=(l.bande if l else "?"),
                   signal=(l.signal_niveau if l else None),
                   change=(bav != (l.bande if l else "?") or sav != ap_s))
        rows.append(row)
        if row["change"]:
            changed.append(row)
    print(f"\n== 30 TÉMOINS (avant run3 → après run5) · {1000*dt/max(1,len(pids)):.2f} ms/parc ==")
    print(f"{'idu':<16}{'cat':<9}{'av_s':>5}{'av_b':>5}{'ap_s':>6}{'ap_b':>5}{'sig':>7} chg")
    for r in rows:
        print(f"{r['idu']:<16}{r['cat']:<9}{str(r['av_score']):>5}{r['av_bande']:>5}"
              f"{str(r['ap_score']):>6}{r['ap_bande']:>5}{str(r['signal']):>7} {'★' if r['change'] else ''}")
    print(f"→ {len(changed)}/{len(rows)} témoins changent")
    (OUT / "temoins_avant_apres.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    return rows


def monotonicite(rows):
    cat = {"bonne": [], "limite": [], "mauvaise": []}
    for r in rows:
        if r["ap_score"] is not None and r["cat"] in cat:
            cat[r["cat"]].append(r["ap_score"])
    bmin = min(cat["bonne"]) if cat["bonne"] else None
    mmax = max(cat["mauvaise"]) if cat["mauvaise"] else None
    ok = bmin is not None and mmax is not None and bmin >= mmax
    print(f"\n== MONOTONICITÉ (après run5) : bonne_min={bmin} ≥ mauvaise_max={mmax} → {'VERT' if ok else 'ROUGE'}")
    print(f"   limites={sorted(cat['limite'])}")
    return ok


def set_an_3112(s):
    ids = []
    for r in s.execute(text("""SELECT parcel_id, detail FROM dryrun_cascade_results
            WHERE run_label=:l AND layer_name='zonage_plu_gpu' AND result='HARD_EXCLUDE'"""), {"l": CASCADE}):
        d = r.detail or ""
        if ("Zone A PLU" in d) or ("Zone N PLU" in d):
            m = _PCT.search(d)
            pct = float(m.group(1).replace(",", ".")) if m else None
            if pct is not None and 90 <= pct <= 99:
                ids.append(r.parcel_id)
    return ids


def an_3112():
    with session_scope() as s:
        ids = sorted(set_an_3112(s))
    bandes = Counter()
    spos = 0
    with session_scope() as s2:
        for k in range(0, len(ids), 2000):
            chunk = ids[k:k + 2000]
            lignes = combiner(s2, chunk, "dryrun_r5_an3112", cascade_label=CASCADE,
                              signal_run_id=SIGNAL, signal_recette="q_v15")
            persister(s2, "dryrun_r5_an3112", lignes, cascade_label=CASCADE,
                      signal_run_id=SIGNAL, communes="an_3112_ile")
            for l in lignes:
                bandes[l.bande] += 1
                if not l.non_calculable and (l.score or 0) > 0:
                    spos += 1
    print(f"\n== 3 112 A/N 90-99 % (île) — APRÈS run 5 ==\n  n={len(ids)}  score>0 = {spos} (run3 : 0)")
    print("  bandes :", {b: bandes.get(b, 0) for b in BANDES})
    (OUT / "an_3112_apres.json").write_text(json.dumps(
        {"n": len(ids), "score_gt0": spos, "bandes": dict(bandes)}, ensure_ascii=False, indent=2))
    return len(ids), spos, bandes


def main():
    _, version = charger_bareme()
    print(f"score_version = {version}")
    with session_scope() as s:
        print("résiduel servi =", s.execute(text("SELECT run_seq FROM residuel_runs WHERE is_served")).scalar())
    cav, cap, trans, histo, anomalies, n = sp_bandes_transitions()
    print(f"\n== SAINT-PAUL (n={n}) — bandes avant(run3)/après(run5) ==")
    with (OUT / "bandes_saint_paul.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bande", "avant_run3", "apres_run5", "delta"])
        for b in BANDES:
            print(f"  {b}: {cav.get(b,0):>6} → {cap.get(b,0):>6}  ({cap.get(b,0)-cav.get(b,0):+d})")
            w.writerow([b, cav.get(b, 0), cap.get(b, 0), cap.get(b, 0) - cav.get(b, 0)])
    with (OUT / "transitions_saint_paul.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["avant", "apres", "n"])
        for (a, b), c in sorted(trans.items(), key=lambda kv: -kv[1]):
            w.writerow([a, b, c])
    with (OUT / "hist_scores_saint_paul_apres.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["score", "n"])
        for sc in sorted(histo):
            w.writerow([sc, histo[sc]])
    with (OUT / "anomalies.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["parcel_id", "avant_bande", "avant_score", "apres_bande", "apres_score", "type"])
        for a in anomalies:
            w.writerow(a)
    print(f"  transitions changeantes (hors diagonale) : "
          f"{sum(c for (a,b),c in trans.items() if a!=b)}  · anomalies A↔NC/>2 : {len(anomalies)}")
    rows = temoins()
    ok = monotonicite(rows)
    an_3112()
    print(f"\nRÉSUMÉ : SP bandes ci-dessus · monotonicité={'VERT' if ok else 'ROUGE'} · anomalies={len(anomalies)}")


if __name__ == "__main__":
    main()
