#!/usr/bin/env python
"""M39-BIS A0.1 — LE PARADOXE DU PERMIS (lecture seule).

Question : le RR mesure-t-il une PRÉDICTION de mutation, ou la persistance d'un permis déjà
déposé ? On mesure le RR des têtes SANS permis sur la parcelle vs AVEC, sur le harnais gelé
(fold 2025, scores out-of-sample, hors copro, ties seedés 974) — MÊME protocole qu'algo1_rr_commune.

Constat préalable (model-card) : la prémisse « permis < 2 ans pèse +1,30 » est FAUSSE. Coefs réels :
permis_bin (permis SUR la parcelle) coef 0.045 / IV 0.045 ; permis_24m_norm (densité permis secteur)
coef 0.283 / IV 0.023. Feature dominante = tenure_bin (IV 0.209). Le permis n'est PAS le moteur du
modèle — mais la CORRÉLATION têtes↔permis (M42 : 97,5 % des brûlantes) peut porter le lift. On teste.

Sortie : qa/audit-rr/a0_1_permis.csv (+ print). Aucune écriture DB.
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
SEED, K = 974, 1158


def rr_katz(a: int, n1: int, c: int, n0: int) -> tuple[float, float, float]:
    """RR = (a/n1)/(c/n0) + IC95 Katz-log. a=mutés top, n1=n top, c=mutés base, n0=n base."""
    if not (a and c and n1 and n0):
        return (float("nan"),) * 3
    rr = (a / n1) / (c / n0)
    se = math.sqrt(1 / a - 1 / n1 + 1 / c - 1 / n0)
    return (rr, rr * math.exp(-1.96 * se), rr * math.exp(1.96 * se))


def top_rr(df: pd.DataFrame, k: int) -> dict:
    """RR@k SEEDÉ sur les ex æquo (jamais l'ordre de table) — comme p_model.evaluate."""
    rng = np.random.default_rng(SEED)
    d = df.assign(_j=rng.random(len(df))).sort_values(["p_l2f", "_j"], ascending=[False, False])
    top = d.head(k)
    a, n1 = int(top["label"].sum()), len(top)
    c, n0 = int(d["label"].sum()), len(d)
    rr, lo, hi = rr_katz(a, n1, c, n0)
    return {"k": k, "mutes_top": a, "taux_top": a / n1, "taux_base": c / n0,
            "rr": rr, "ic_bas": lo, "ic_haut": hi}


def main() -> None:
    eng = create_engine(DB)
    lab = pd.read_sql(text(
        "SELECT idu, label, commune, permis_bin FROM p_model_ext_dataset "
        "WHERE annee = 2025 AND label IS NOT NULL"), eng)
    cop = set(pd.read_sql(text(
        "SELECT idu FROM p_model_ext_copro WHERE copro_rnic OR copro_dvf"), eng)["idu"])
    sc = pd.read_csv(SCORES)
    df = lab.merge(sc, on="idu", how="inner")
    df = df[~df["idu"].isin(cop)].reset_index(drop=True)
    df["label"] = df["label"].astype(int)
    df["avec_permis"] = df["permis_bin"].fillna("jamais") != "jamais"

    rows = []
    # 1) contrôle île
    ile = top_rr(df, K)
    ile["univers"] = "ÎLE (contrôle)"
    rows.append(ile)
    print(f"contrôle île RR@{K} = {ile['rr']:.2f} [{ile['ic_bas']:.2f};{ile['ic_haut']:.2f}] "
          f"(gelé ~6,73) · base {ile['taux_base']*100:.2f}%")

    # 2) part des têtes qui portent un permis (M42 : 97,5 % des brûlantes)
    rng = np.random.default_rng(SEED)
    tete = df.assign(_j=rng.random(len(df))).sort_values(["p_l2f", "_j"], ascending=[False, False]).head(K)
    pct_permis_tete = tete["avec_permis"].mean()
    pct_permis_all = df["avec_permis"].mean()
    print(f"\npart AVEC permis : têtes {pct_permis_tete*100:.1f}% vs parc entier {pct_permis_all*100:.1f}%")

    # 3) RR intra-univers : sans permis vs avec permis (k proportionnel à la taille de l'univers)
    for nom, sub in [("SANS permis", df[~df["avec_permis"]]), ("AVEC permis", df[df["avec_permis"]])]:
        k = max(5, round(K * len(sub) / len(df)))
        r = top_rr(sub.reset_index(drop=True), k)
        r["univers"] = nom
        r["n_univers"] = len(sub)
        rows.append(r)
        conc = "" if r["mutes_top"] >= 5 else " ⚠ <5 mutés (non concluant)"
        print(f"  {nom:12s} n={len(sub):>6} base {r['taux_base']*100:.2f}% · "
              f"RR@{k} = {r['rr']:.2f} [{r['ic_bas']:.2f};{r['ic_haut']:.2f}]{conc}")

    out = pd.DataFrame(rows)[["univers", "k", "n_univers", "mutes_top", "taux_top", "taux_base",
                              "rr", "ic_bas", "ic_haut"] if "n_univers" in pd.DataFrame(rows).columns
                             else ["univers", "k", "mutes_top", "taux_top", "taux_base", "rr", "ic_bas", "ic_haut"]]
    dest = os.path.join(os.path.dirname(__file__), "a0_1_permis.csv")
    out.to_csv(dest, index=False)
    print(f"\n✓ {dest}")


if __name__ == "__main__":
    main()
