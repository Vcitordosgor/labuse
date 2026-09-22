#!/usr/bin/env python3
"""SCORING-6-DRYRUN — rejeu du moteur sur le résiduel post-calibrage (run 3, assiette clippée).

Même protocole que SCORING-6 §3, mais le résiduel servi est désormais le run 3
(`--assiette-clippee`, île entière). q_v11_m137 reste servi ; aucun run île, aucune bascule.

  - 30 témoins       → persistés `dryrun_r3_temoins` (comparés à TEMOINS.csv = avant/run 2)
  - Saint-Paul       → déjà persisté `dryrun_r3` par le CLI score-labuse (mandat) ; ce script
                       n'y touche pas — il calcule seulement le temps témoins + monotonicité + 3112
  - 3 112 A/N 90-99% → persistés `dryrun_r3_an3112` (île), question « combien score > 0 après »

    LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
    PYTHONPATH=src <venv>/python reports/scoring-6/dryrun_post_residuel/dryrun_r3.py
"""
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
SIGNAL = "q_v14"                 # stand-in du Signal (le fit q_v15 est un geste de Vic)
_PCT = re.compile(r"recouvrement\s+(\d+(?:[.,]\d+)?)\s*%")


def temoins():
    """30 témoins sur run 3, comparés à TEMOINS.csv (= avant, run 2 — reproduit 30/30 en SCORING-6)."""
    ref = {r["idu"]: r for r in csv.DictReader(TEMOINS_CSV.open())}
    with session_scope() as s:
        idmap = {r.idu: r.id for r in s.execute(
            text("SELECT id, idu FROM parcels WHERE idu = ANY(:x)"), {"x": list(ref)})}
        pids = [idmap[i] for i in ref if i in idmap]
        with engine().begin() as c:
            ensure_schema(c)
        t0 = time.time()
        lignes = combiner(s, pids, "dryrun_r3_temoins", cascade_label=CASCADE,
                          signal_run_id=SIGNAL, signal_recette="q_v15")
        dt = time.time() - t0
        persister(s, "dryrun_r3_temoins", lignes, cascade_label=CASCADE,
                  signal_run_id=SIGNAL, communes="temoins")
    by = {l.parcel_id: l for l in lignes}
    rows = []
    changed = []
    for idu, exp in ref.items():
        l = by.get(idmap.get(idu))
        av_s = None if exp["non_calculable"] == "oui" else int(exp["score"] or 0)
        av_nc = exp["non_calculable"] == "oui"
        ap_s = None if (l and l.non_calculable) else (l.score if l else None)
        ap_nc = bool(l and l.non_calculable)
        av_b = _bande(av_s, av_nc)
        ap_b = l.bande if l else "?"
        row = dict(idu=idu, commune=exp["commune"], cat=exp["categorie"],
                   av_score=av_s, av_bande=av_b, ap_score=ap_s, ap_bande=ap_b,
                   signal=(l.signal_niveau if l else None),
                   change=(av_s != ap_s or av_nc != ap_nc))
        rows.append(row)
        if row["change"]:
            changed.append(row)
    (OUT / "temoins_avant_apres.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(f"\n== 30 TÉMOINS (avant run2 = TEMOINS.csv → après run3) · {1000*dt/max(1,len(pids)):.2f} ms/parcelle ==")
    print(f"{'idu':<16}{'cat':<10}{'av_s':>5}{'av_b':>5}{'ap_s':>6}{'ap_b':>5}{'sig':>7}  chg")
    for r in rows:
        print(f"{r['idu']:<16}{r['cat']:<10}{str(r['av_score']):>5}{r['av_bande']:>5}"
              f"{str(r['ap_score']):>6}{r['ap_bande']:>5}{str(r['signal']):>7}  {'★' if r['change'] else ''}")
    print(f"→ {len(changed)}/{len(rows)} témoins changent (score ou NC)")
    return rows, changed


def monotonicite(rows):
    """Le test des témoins reste vert : dans chaque catégorie, l'ordre bonne ≥ limite ≥ mauvaise
    tient sur les scores APRÈS (les NC exclues). Vérifie aussi qu'aucune « bonne » ne tombe < une
    « mauvaise » (croisement = rupture de monotonicité)."""
    cat = {"bonne": [], "limite": [], "mauvaise": []}
    for r in rows:
        if r["ap_score"] is not None and r["cat"] in cat:
            cat[r["cat"]].append(r["ap_score"])
    bonne_min = min(cat["bonne"]) if cat["bonne"] else None
    mauvaise_max = max(cat["mauvaise"]) if cat["mauvaise"] else None
    ok = (bonne_min is not None and mauvaise_max is not None and bonne_min >= mauvaise_max)
    print("\n== MONOTONICITÉ (après run3) ==")
    print(f"  bonnes    : min={bonne_min}  (n={len(cat['bonne'])})")
    print(f"  limites   : {sorted(cat['limite'])}")
    print(f"  mauvaises : max={mauvaise_max}  (n={len(cat['mauvaise'])})")
    print(f"  → bonne_min ({bonne_min}) ≥ mauvaise_max ({mauvaise_max}) : {'VERT' if ok else 'ROUGE'}")
    return ok


def set_an_3112(s):
    """Les 3 112 parcelles A/N dont l'exclusion zonage a un recouvrement 90-99 % (île)."""
    rows = s.execute(text("""SELECT parcel_id, detail FROM dryrun_cascade_results
        WHERE run_label=:l AND layer_name='zonage_plu_gpu' AND result='HARD_EXCLUDE'"""),
        {"l": CASCADE})
    ids = []
    for r in rows:
        d = r.detail or ""
        if ("Zone A PLU" in d) or ("Zone N PLU" in d):
            m = _PCT.search(d)
            pct = float(m.group(1).replace(",", ".")) if m else None
            if pct is not None and 90 <= pct <= 99:
                ids.append(r.parcel_id)
    return ids


def an_3112():
    print("\n== 3 112 A/N 90-99 % (île) — score APRÈS run 3 ==")
    with session_scope() as s:
        ids = set_an_3112(s)
    print(f"  n = {len(ids)}")
    bandes = Counter()
    spos = 0
    CH = 2000
    ids = sorted(ids)
    with session_scope() as s2:
        for k in range(0, len(ids), CH):
            chunk = ids[k:k + CH]
            lignes = combiner(s2, chunk, "dryrun_r3_an3112", cascade_label=CASCADE,
                              signal_run_id=SIGNAL, signal_recette="q_v15")
            persister(s2, "dryrun_r3_an3112", lignes, cascade_label=CASCADE,
                      signal_run_id=SIGNAL, communes="an_3112_ile")
            for l in lignes:
                bandes[l.bande] += 1
                if not l.non_calculable and (l.score or 0) > 0:
                    spos += 1
    print(f"  score > 0 : {spos} / {len(ids)}")
    print("  bandes :", {b: bandes.get(b, 0) for b in ("A", "B", "C", "D", "NC")})
    (OUT / "an_3112_apres.json").write_text(json.dumps(
        {"n": len(ids), "score_gt0": spos, "bandes": dict(bandes)}, ensure_ascii=False, indent=2))
    return len(ids), spos, bandes


def _bande(score, nc):
    if nc or score is None:
        return "NC"
    if score >= 80:
        return "A"
    if score >= 50:
        return "B"
    if score >= 30:
        return "C"
    return "D"


def main():
    _, version = charger_bareme()
    print(f"score_version = {version}")
    rows, changed = temoins()
    ok = monotonicite(rows)
    an_3112()
    print(f"\nRÉSUMÉ : témoins changés={len(changed)} · monotonicité={'VERT' if ok else 'ROUGE'}")


if __name__ == "__main__":
    main()
