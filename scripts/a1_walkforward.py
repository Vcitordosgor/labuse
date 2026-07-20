#!/usr/bin/env python
"""PHASE A-1 étape 2 — VOLET 1 : le JUGE (walk-forward poolé, LECTURE SEULE).

Doctrine (réserve §7, devenue règle) : un signal à horizon FORWARD ne se juge pas au ΔRR de l'arène
(label ~2025, orthogonal à une fenêtre 2026-2028) mais par un walk-forward dédié. Ce script EST ce juge.

Protocole, folds N = 2021…2025, AS-OF STRICT (rien de postérieur au 1er janvier N ne sert à établir l'état) :
  - Ensemble à risque au 1/1/N = parcelle MONO (copro_rnic=copro_dvf=false) portant une acquisition NEUF
    (VEFA, ou Vente logement ≤ 3 ans après achèvement PC) d'année Y ≤ N-3 (au-delà de la grâce 2 ans qui
    neutralise l'acte de livraison VEFA), ENCORE DÉTENUE au 1/1/N (aucune revente logement dans
    (acq + 2 ans, 1/1/N)).
  - elapsed = N - Y.  « en fenêtre » = elapsed ∈ {6..11} (+6/+8 ou +9/+11).
    « hors fenêtre » (contrôle apparié : même nature « logement neuf détenu », hors pic) = elapsed ∈ {3,4,5,12,13,14}.
  - Issue = au moins une mutation logement (Vente/VEFA) de la parcelle DANS l'année N.
Mesure : P(mutation année N | en fenêtre) vs P(… | hors fenêtre), folds AGRÉGÉS, lift + odds ratio,
IC95 bootstrap **cluster par parcelle** (le même bien apparaît sur plusieurs folds — dépendance de panel),
seed 974. Contexte secondaire : taux de base « toutes mono ».

Critère mécanique (décision Vic) : **IC95 exclut 1 → la composante V est validée ; sinon badge seul.**

Usage: python scripts/a1_walkforward.py   → reports/a1-defisc/walkforward.json + table imprimée
"""
from __future__ import annotations
import json, os, sys
from collections import defaultdict
from datetime import date
import numpy as np
import psycopg

SEED = 974
GRACE_DAYS = 2 * 365
FOLDS = [2021, 2022, 2023, 2024, 2025]
IN_WINDOW = {6, 7, 8, 9, 10, 11}
OFF_WINDOW = {3, 4, 5, 12, 13, 14}
VEFA = "Vente en l'état futur d'achèvement"
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "a1-defisc")

PULL = """
WITH muts AS (
  SELECT id_parcelle AS idu, date_mutation::date AS dt, nature_mutation AS nat, type_local AS tl
  FROM dvf_mutations_histo WHERE nature_mutation IN ('Vente', %(v)s)
  UNION ALL
  SELECT id_parcelle, date_mutation::date, nature_mutation, type_local
  FROM dvf_mutations_parcelle WHERE nature_mutation IN ('Vente', %(v)s)
),
ach AS (
  SELECT pmp.idu, min(md.date_achevement) AS ach FROM p_model_permits pmp
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type='PC' AND md.date_achevement IS NOT NULL GROUP BY pmp.idu
)
SELECT m.idu, m.dt, (m.nat = %(v)s) AS vefa, m.tl, a.ach
FROM muts m
JOIN p_model_ext_copro c ON c.idu = m.idu
LEFT JOIN ach a ON a.idu = m.idu
WHERE NOT (COALESCE(c.copro_rnic,false) OR COALESCE(c.copro_dvf,false))   -- MONO uniquement
ORDER BY m.idu, m.dt;
"""
DWELLING = {"Maison", "Appartement"}


def load():
    conn = psycopg.connect("dbname=labuse user=openclaw")
    with conn.cursor() as cur:
        cur.execute(PULL, {"v": VEFA})
        rows = cur.fetchall()
    # base « toutes mono » : nb de parcelles mono distinctes, et mutations logement par année
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM p_model_ext_copro WHERE NOT (COALESCE(copro_rnic,false) OR COALESCE(copro_dvf,false))")
        n_mono_total = cur.fetchone()[0]
    conn.close()
    par = defaultdict(lambda: {"ach": None, "events": []})   # events: (date, vefa, dwelling)
    for idu, dt, vefa, tl, ach in rows:
        p = par[idu]
        p["ach"] = ach
        p["events"].append((dt, bool(vefa), tl in DWELLING))
    for p in par.values():
        p["events"].sort(key=lambda e: e[0])
    return par, n_mono_total


def is_neuf(dt, vefa, dwelling, ach):
    if vefa:
        return True
    if dwelling and ach is not None and 0 <= (dt - ach).days <= 3 * 365:
        return True
    return False


def build_panel(par):
    """Retourne rows = liste de dicts {idu, N, elapsed, in_window(bool), mutated(bool)}."""
    rows = []
    for idu, p in par.items():
        ach = p["ach"]
        evs = p["events"]
        neuf_acqs = [(dt, vefa) for (dt, vefa, dw) in evs if is_neuf(dt, vefa, dw, ach)]
        if not neuf_acqs:
            continue
        dwell_dates = [dt for (dt, vefa, dw) in evs if dw]
        for N in FOLDS:
            Ncut = date(N, 1, 1)
            cand = [dt for (dt, vefa) in neuf_acqs if dt < Ncut]
            if not cand:
                continue
            A = max(cand)                          # dernière acquisition neuf avant 1/1/N
            elapsed = N - A.year
            if elapsed < 3:
                continue
            if elapsed not in IN_WINDOW and elapsed not in OFF_WINDOW:
                continue
            # détenue ? aucune revente logement au-delà de la grâce et avant 1/1/N (as-of strict)
            grace_end = date(A.year, A.month, A.day)
            resold = any((dt - A).days > GRACE_DAYS and dt < Ncut for dt in dwell_dates)
            if resold:
                continue
            # issue : mutation logement dans l'année N (postérieure, hors grâce car elapsed>=3)
            mutated = any(dt.year == N for dt in dwell_dates if dt >= Ncut)
            rows.append({"idu": idu, "N": N, "elapsed": elapsed,
                         "in_window": elapsed in IN_WINDOW, "mutated": mutated})
    return rows


def cluster_bootstrap_or(rows, n_boot=2000):
    """OR et lift P(mut|fenêtre)/P(mut|hors), IC95 bootstrap CLUSTER par parcelle (seed 974)."""
    by_idu = defaultdict(list)
    for r in rows:
        by_idu[r["idu"]].append((r["in_window"], r["mutated"]))
    idus = list(by_idu.keys())

    def stats(sample_rows):
        win = [m for (w, m) in sample_rows if w]
        off = [m for (w, m) in sample_rows if not w]
        if not win or not off:
            return None
        pw, po = np.mean(win), np.mean(off)
        return pw, po

    all_rows = [wm for lst in by_idu.values() for wm in lst]
    base = stats(all_rows)
    pw, po = base
    lift = pw / po if po > 0 else float("inf")
    ow = min(max(pw, 1e-9), 1 - 1e-9); oo = min(max(po, 1e-9), 1 - 1e-9)
    OR = (ow / (1 - ow)) / (oo / (1 - oo))
    rng = np.random.RandomState(SEED)
    lifts, ors = [], []
    idx_arr = np.arange(len(idus))
    for _ in range(n_boot):
        pick = rng.choice(idx_arr, len(idus), replace=True)
        samp = [wm for j in pick for wm in by_idu[idus[j]]]
        st = stats(samp)
        if st is None:
            continue
        a, b = st
        if b <= 0:
            continue
        lifts.append(a / b)
        aa = min(max(a, 1e-9), 1 - 1e-9); bb = min(max(b, 1e-9), 1 - 1e-9)
        ors.append((aa / (1 - aa)) / (bb / (1 - bb)))
    return {
        "p_window": float(pw), "p_off": float(po), "lift": float(lift), "odds_ratio": float(OR),
        "lift_ic95": [float(np.percentile(lifts, 2.5)), float(np.percentile(lifts, 97.5))],
        "or_ic95": [float(np.percentile(ors, 2.5)), float(np.percentile(ors, 97.5))],
        "n_window_rows": int(sum(1 for r in rows if r["in_window"])),
        "n_off_rows": int(sum(1 for r in rows if not r["in_window"])),
        "n_parcelles": len(idus),
    }


def per_fold(rows):
    out = []
    for N in FOLDS:
        rw = [r for r in rows if r["N"] == N]
        win = [r["mutated"] for r in rw if r["in_window"]]
        off = [r["mutated"] for r in rw if not r["in_window"]]
        out.append({
            "N": N,
            "n_win": len(win), "mut_win": int(sum(win)), "rate_win": (np.mean(win) if win else None),
            "n_off": len(off), "mut_off": int(sum(off)), "rate_off": (np.mean(off) if off else None),
        })
    return out


def main():
    print("chargement mono 2014-2025 ...", file=sys.stderr)
    par, n_mono_total = load()
    rows = build_panel(par)
    print(f"{len(par)} parcelles mono, {len(rows)} observations parcelle-année", file=sys.stderr)

    res = cluster_bootstrap_or(rows)
    folds = per_fold(rows)
    res["par_fold"] = folds
    res["n_mono_total"] = n_mono_total
    res["criterion_pass"] = res["lift_ic95"][0] > 1.0 and res["or_ic95"][0] > 1.0

    os.makedirs(OUT, exist_ok=True)
    json.dump(res, open(os.path.join(OUT, "walkforward.json"), "w"), indent=2, default=str)

    print("\n=== WALK-FORWARD POOLÉ — mutation dans l'année N ===")
    print(f"  {'N':>4} | {'n_fenêtre':>9} {'mut':>4} {'taux':>7} | {'n_hors':>7} {'mut':>4} {'taux':>7}")
    for f in folds:
        rw = f"{f['rate_win']:.4f}" if f["rate_win"] is not None else "   —  "
        ro = f"{f['rate_off']:.4f}" if f["rate_off"] is not None else "   —  "
        print(f"  {f['N']:>4} | {f['n_win']:>9} {f['mut_win']:>4} {rw:>7} | {f['n_off']:>7} {f['mut_off']:>4} {ro:>7}")
    print(f"\n  POOLÉ : P(mut|fenêtre)={res['p_window']:.4f} (n={res['n_window_rows']})  "
          f"P(mut|hors)={res['p_off']:.4f} (n={res['n_off_rows']})")
    print(f"  LIFT = {res['lift']:.2f}  IC95[{res['lift_ic95'][0]:.2f}, {res['lift_ic95'][1]:.2f}]")
    print(f"  OR   = {res['odds_ratio']:.2f}  IC95[{res['or_ic95'][0]:.2f}, {res['or_ic95'][1]:.2f}]  "
          f"(cluster/parcelle, seed 974, {res['n_parcelles']} parcelles)")
    print(f"\n  >>> CRITÈRE (IC exclut 1) : {'✅ PASSÉ — composante V validée' if res['criterion_pass'] else '❌ NON PASSÉ — badge seul'}")
    print(f"\nJSON -> {os.path.join(OUT, 'walkforward.json')}")


if __name__ == "__main__":
    main()
