#!/usr/bin/env python
"""ALGO-1 item 1 — RR PAR COMMUNE sur le fold 2025 (MESURE, aucune modification).

Le RR@1158 « 6,73 » du walk-forward M3.6 est une moyenne île : cette mesure le ventile
par commune, avec le protocole GELÉ (label L2-F fold 2025, scores OUT-OF-SAMPLE du fold
`reports/m36-foncier/scores-2025-fold-final.csv`, univers HORS COPRO, ties seedés 974 —
réutilise `p_model.evaluate`, rien de recodé).

Deux angles complémentaires (les deux sont rapportés, ils répondent à deux questions) :
  A. VENTILATION DU TOP-1158 ÎLE (ev.ventilation) : où atterrit la réserve servie, et
     quel RR y fait-elle par commune — « qui profite du top island-wide » ;
  B. RR@k_c INTRA-COMMUNE : k_c = part proportionnelle de 1158 (n_commune/N × 1158,
     min 5), top-k_c pris DANS la commune, RR contre le taux de base DE la commune —
     « le classement discrimine-t-il aussi bien partout ».

Sortie : reports/algo1-rr-commune.md (+ CSV à côté). LECTURE SEULE.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from labuse.scoring.p_model import SEED, evaluate as ev

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
SCORES = os.path.join(os.path.dirname(__file__), "..", "reports", "m36-foncier",
                      "scores-2025-fold-final.csv")
OUT_MD = os.path.join(os.path.dirname(__file__), "..", "reports", "algo1-rr-commune.md")
OUT_CSV = os.path.join(os.path.dirname(__file__), "..", "reports", "algo1-rr-commune.csv")
K = 1158

NOMS = {  # code INSEE → nom (run_all.REUNION_COMMUNES, recopié : lecture seule du module lourd)
    "97401": "Les Avirons", "97402": "Bras-Panon", "97403": "Entre-Deux", "97404": "L'Étang-Salé",
    "97405": "Petite-Île", "97406": "La Plaine-des-Palmistes", "97407": "Le Port",
    "97408": "La Possession", "97409": "Saint-André", "97410": "Saint-Benoît",
    "97411": "Saint-Denis", "97412": "Saint-Joseph", "97413": "Saint-Leu", "97414": "Saint-Louis",
    "97415": "Saint-Paul", "97416": "Saint-Pierre", "97417": "Saint-Philippe",
    "97418": "Sainte-Marie", "97419": "Sainte-Rose", "97420": "Sainte-Suzanne",
    "97421": "Salazie", "97422": "Le Tampon", "97423": "Les Trois-Bassins", "97424": "Cilaos",
}


def main() -> int:
    eng = create_engine(DB)
    lab = pd.read_sql(text(
        "SELECT idu, label, commune FROM p_model_ext_dataset "
        "WHERE annee = 2025 AND label IS NOT NULL"), eng)
    cop = pd.read_sql(text(
        "SELECT idu FROM p_model_ext_copro WHERE copro_rnic OR copro_dvf"), eng)
    sc = pd.read_csv(SCORES)

    df = lab.merge(sc, on="idu", how="inner")
    df = df[~df["idu"].isin(set(cop["idu"]))].reset_index(drop=True)   # hors copro (protocole)
    y = df["label"].astype(int).to_numpy()
    s = df["p_l2f"].to_numpy(float)
    base_ile = float(y.mean())

    # contrôle : le RR île doit retomber sur le chiffre gelé (~6,73) — sinon STOP.
    ile = ev.rr_at_k(y, s, K, seed=SEED)
    print(f"contrôle île : RR@{K} hors copro = {ile['rr']:.2f} (gelé 6,73) · "
          f"n={len(df)} · taux base {base_ile:.4f}")

    # A. ventilation du top-1158 île par commune (harnais gelé)
    vent = ev.ventilation(df, y, s, K, col="commune", seed=SEED)

    # B. RR@k_c intra-commune, k_c proportionnel (≥ 5 pour éviter les RR à 1 parcelle)
    rows = []
    rng_check = np.random.RandomState(SEED)  # noqa: F841 — même seed doctrine que le harnais
    for com, grp in df.groupby("commune"):
        yc = grp["label"].astype(int).to_numpy()
        sc_c = grp["p_l2f"].to_numpy(float)
        k_c = max(5, int(round(K * len(grp) / len(df))))
        r = ev.rr_at_k(yc, sc_c, k_c, seed=SEED)
        rows.append({"commune": com, "nom": NOMS.get(com, com), "n_hors_copro": len(grp),
                     "taux_base_pct": 100 * r["taux_global"], "k_c": k_c,
                     "positifs_topk": r["positifs_topk"], "rr_intra": r["rr"]})
    intra = pd.DataFrame(rows).sort_values("rr_intra", ascending=False)

    out = intra.merge(
        vent.rename(columns={"n_total": "n_vent", "n_topk": "n_top1158_ile",
                             "rr_segment": "rr_dans_top_ile"})[
            ["commune", "n_top1158_ile", "rr_dans_top_ile"]],
        on="commune", how="left")
    out.to_csv(OUT_CSV, index=False)

    med = out["rr_intra"].median()
    lignes = [
        "# ALGO-1 · RR par commune — fold 2025 (mesure, out-of-sample)",
        "",
        f"Protocole GELÉ : label L2-F 2025, scores du fold walk-forward "
        f"(`scores-2025-fold-final.csv`), hors copro, ties seedés {SEED} "
        f"(`p_model.evaluate`, rien de recodé).",
        f"**Contrôle île : RR@{K} = {ile['rr']:.2f}** (référence gelée 6,73 — "
        f"{'OK' if abs(ile['rr'] - 6.73) < 0.15 else 'ÉCART, à investiguer'}) · "
        f"n = {len(df):,} hors copro · taux de base île {100 * base_ile:.2f} %.".replace(",", " "),
        "",
        "Deux lectures : **RR intra-commune** (top-k_c pris DANS la commune, k_c ∝ 1158 — "
        "le classement discrimine-t-il partout) et **présence dans le top-1158 île** "
        "(où va la réserve réellement servie).",
        "",
        "| Commune | n hors copro | taux base | k_c | RR intra [conf.] | dans top-1158 île | RR dans le top île |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in out.iterrows():
        conf = "" if r["positifs_topk"] >= 5 else " ⚠ <5 positifs"
        top_ile = "—" if pd.isna(r["n_top1158_ile"]) else f"{int(r['n_top1158_ile'])}"
        rr_ile = "—" if pd.isna(r["rr_dans_top_ile"]) else f"{r['rr_dans_top_ile']:.1f}"
        lignes.append(
            f"| {r['nom']} ({r['commune']}) | {r['n_hors_copro']:,} | {r['taux_base_pct']:.2f} % "
            f"| {r['k_c']} | **{r['rr_intra']:.1f}**{conf} | {top_ile} | {rr_ile} |".replace(",", " "))
    lignes += [
        "",
        f"Médiane des RR intra-commune : **{med:.1f}** (île : {ile['rr']:.2f}).",
        "",
        "Notes de lecture honnêtes :",
        "- un RR intra très haut sur une PETITE commune (peu de positifs dans le top-k_c) est "
        "fragile — les lignes « ⚠ <5 positifs » ne supportent aucune conclusion ;",
        "- « dans top-1158 île — » = la commune ne place AUCUNE parcelle dans la réserve servie : "
        "le classement île concentre la réserve sur les marchés actifs (c'est le comportement "
        "attendu d'un rang absolu, pas un bug — mais c'est un choix produit à connaître) ;",
        "- mesure SEULE : aucun seuil, aucun tier, aucun modèle modifié (mandat ALGO-1 item 1).",
    ]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")
    print(f"→ {OUT_MD}\n→ {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
