#!/usr/bin/env python
"""M39-BIS C.1 — MONOTONIE du RR par tier (le test le plus important du mandat, lecture seule).

Si le RR n'est pas monotone (brûlante > chaude > à-creuser > 1), la hiérarchie des tiers ne tient
pas. On mesure DEUX façons, les deux rapportées :
  A. TIERS SERVIS (parcel_p_score_v2 du run servi) × label fold 2025 — « les tiers que le produit
     affiche prédisent-ils dans l'ordre ? » (caveat : le run servi n'est pas garanti out-of-sample
     pour 2025 ; lecture directe du produit).
  B. STRATES du score FOLD out-of-sample, taillées aux effectifs des tiers (118/1038/29978) —
     monotonie PURE hors échantillon.
Chaque taux porte son effectif + IC95 (Katz vs base). Hors copro (protocole).

Sortie : qa/audit-rr/c1_monotonie.csv. Aucune écriture DB.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
SCORES = os.path.join(os.path.dirname(__file__), "..", "..", "reports", "m36-foncier",
                      "scores-2025-fold-final.csv")
SEED = 974


def rr_katz(a, n1, c, n0):
    if not (a and c and n1 and n0):
        return (float("nan"),) * 3
    rr = (a / n1) / (c / n0)
    se = math.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0)
    return rr, rr * math.exp(-1.96 * se), rr * math.exp(1.96 * se)


def main() -> None:
    eng = create_engine(DB)
    lab = pd.read_sql(text("SELECT idu, label FROM p_model_ext_dataset "
                           "WHERE annee=2025 AND label IS NOT NULL"), eng)
    cop = set(pd.read_sql(text("SELECT idu FROM p_model_ext_copro WHERE copro_rnic OR copro_dvf"),
                          eng)["idu"])
    v2run = pd.read_sql(text("SELECT run_id FROM p_score_v2_runs WHERE run_id='q_v8_calibre'"),
                        eng)["run_id"].iloc[0]
    tiers = pd.read_sql(text("SELECT parcelle_id AS idu, tier FROM parcel_p_score_v2 WHERE run_id=:r"),
                        eng, params={"r": v2run})
    lab = lab[~lab["idu"].isin(cop)].copy()
    lab["label"] = lab["label"].astype(int)
    c, n0 = int(lab["label"].sum()), len(lab)
    base = c / n0
    rows = []

    print("=== A. TIERS SERVIS × label fold 2025 (hors copro) ===")
    d = lab.merge(tiers, on="idu", how="left")
    order = ["brulante", "chaude", "reserve_fonciere", "a_creuser"]
    prev = None
    mono = True
    for t in order:
        g = d[d["tier"] == t]
        a, n1 = int(g["label"].sum()), len(g)
        rr, lo, hi = rr_katz(a, n1, c, n0)
        rows.append({"mesure": "tiers_servis", "strate": t, "n": n1, "mutes": a,
                     "taux": a / n1 if n1 else float("nan"), "rr": rr, "ic_bas": lo, "ic_haut": hi})
        conc = "" if a >= 5 else " ⚠ <5"
        if prev is not None and not math.isnan(rr) and rr > prev:
            mono = False
        prev = rr if not math.isnan(rr) else prev
        print(f"  {t:18s} n={n1:>6} mutés={a:>4} taux={100*a/n1 if n1 else 0:.2f}% "
              f"RR={rr:.2f} [{lo:.2f};{hi:.2f}]{conc}")
    print(f"  → base {100*base:.2f}% · MONOTONE (décroissant) : {'OUI' if mono else 'NON'}")

    print("\n=== B. STRATES score FOLD out-of-sample (tailles tiers 118/1038/29978) ===")
    sc = pd.read_csv(SCORES)
    dd = lab.merge(sc, on="idu", how="inner")
    rng = np.random.default_rng(SEED)
    dd = dd.assign(_j=rng.random(len(dd))).sort_values(["p_l2f", "_j"], ascending=[False, False]).reset_index(drop=True)
    bornes = [(0, 118, "top-118 (brûlante-équiv)"), (118, 1156, "119-1156 (chaude-équiv)"),
              (1156, 31134, "1157-31134 (à-creuser-équiv)"), (31134, len(dd), "reste")]
    prev = None
    monoB = True
    for lo_i, hi_i, nom in bornes:
        g = dd.iloc[lo_i:hi_i]
        a, n1 = int(g["label"].sum()), len(g)
        rr, lo, hi = rr_katz(a, n1, c, n0)
        rows.append({"mesure": "strate_fold", "strate": nom, "n": n1, "mutes": a,
                     "taux": a / n1 if n1 else float("nan"), "rr": rr, "ic_bas": lo, "ic_haut": hi})
        if prev is not None and not math.isnan(rr) and rr > prev + 1e-9:
            monoB = False
        prev = rr if not math.isnan(rr) else prev
        print(f"  {nom:28s} n={n1:>6} mutés={a:>4} taux={100*a/n1:.2f}% RR={rr:.2f} [{lo:.2f};{hi:.2f}]")
    print(f"  → MONOTONE (décroissant) : {'OUI' if monoB else 'NON'}")

    pd.DataFrame(rows).to_csv(os.path.join(os.path.dirname(__file__), "c1_monotonie.csv"), index=False)


if __name__ == "__main__":
    main()
