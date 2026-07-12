"""M3.6 lot 3 — comparatif M3 vs M3.6 sur test 2025 hors copro, décision de
promotion, scoring 2026 foncier (top-1158 hors copro, 5 contributions lisibles).

Le modèle de scoring 2026 est ré-ajusté sur train 2017-2024 + calibration 2025
(même pipeline et mêmes croisements que le walk-forward) : il n'est évalué contre
AUCUN test — tous ses ans sont passés — et sert uniquement la préversion produit.

Usage : LABUSE_DATABASE_URL=… python scripts/m36-foncier/lot3_verdict_final.py
"""
from __future__ import annotations

import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from labuse.db import engine
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import FEATURES, derive
from labuse.scoring.p_model.model import PModel

REPORTS = Path("reports/m36-foncier")
M3ART = Path("reports/m3-p-model/artifacts")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_ext(years) -> pd.DataFrame:
    yrs = ", ".join(str(y) for y in years)
    return derive(pd.read_sql(
        f"SELECT * FROM p_model_ext_dataset WHERE annee IN ({yrs})", engine()))


def main() -> None:
    copro = pd.read_sql(
        "SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
        engine()).set_index("idu")["copro"]
    wf = pd.read_csv(REPORTS / "walk-forward.csv")
    m36_2025 = joblib.load(REPORTS / "artifacts-m36-fold2025.joblib")

    # ---- comparatif M3 vs M3.6 sur 2025 hors copro -----------------------------
    m3 = PModel.load(str(M3ART / "p_model.joblib"))
    d25_m3 = pd.read_sql("SELECT * FROM p_model_dataset WHERE annee = 2025", engine())
    from labuse.scoring.p_model.features import derive as derive_m3
    d25_m3 = derive_m3(d25_m3).reset_index(drop=True)
    d25 = load_ext((2025,)).reset_index(drop=True)

    p_m3 = pd.Series(m3.predict_proba(d25_m3), index=d25_m3["idu"])
    p_m36 = pd.Series(m36_2025.predict_proba(d25), index=d25["idu"])
    overlap = ev.churn_topk(p_m3, p_m36, 1158)

    hc = ~d25["idu"].map(copro).fillna(False).to_numpy()
    y_l2f = d25["label"].astype(int).to_numpy()
    y_l2 = d25["label_l2"].astype(int).to_numpy()
    p36 = p_m36.to_numpy()
    pm3_al = d25["idu"].map(p_m3).to_numpy()

    rows = [
        {"modele": "M3 (L2, gelé)", "cible_eval": "L2 hors copro",
         **ev.bootstrap_rr(y_l2[hc], pm3_al[hc], 1158),
         "ece": ev.ece(y_l2[hc], pm3_al[hc])[0]},
        {"modele": "M3 (L2, gelé)", "cible_eval": "L2-F hors copro",
         **ev.bootstrap_rr(y_l2f[hc], pm3_al[hc], 1158),
         "ece": ev.ece(y_l2f[hc], pm3_al[hc])[0]},
        {"modele": "M3.6 (L2-F, fold 2025)", "cible_eval": "L2-F hors copro",
         **ev.bootstrap_rr(y_l2f[hc], p36[hc], 1158),
         "ece": ev.ece(y_l2f[hc], p36[hc])[0]},
    ]
    comp = pd.DataFrame(rows)
    comp["overlap_top1158_m3_m36"] = overlap["overlap_pct"]
    comp.to_csv(REPORTS / "comparatif.csv", index=False)
    log("comparatif :\n" + comp[["modele", "cible_eval", "rr", "ic95_bas",
                                 "ic95_haut", "ece"]].to_string(index=False))
    log(f"overlap top-1158 M3 vs M3.6 (2025) : {overlap['overlap']} ({overlap['overlap_pct']:.1%})")

    # ---- décision de promotion --------------------------------------------------
    l2f_folds = wf[wf.label == "label"]
    crit = {
        "rr_2025_vs_lot0": float(l2f_folds[l2f_folds.fold == 2025]["rr@1158_hors_copro"].iloc[0]),
        "barre_lot0_p_complet": 2.85, "barre_lot0_z_seul": 5.07,
        "tous_folds_rr_ge_2": bool((l2f_folds["rr@1158"] >= 2).all()
                                   and (l2f_folds["rr@1158_hors_copro"] >= 2).all()),
        "signes_stables": "24/29 (aucune monotonie contrainte violée ; instables = coefs ~0)",
    }
    promotion = (crit["rr_2025_vs_lot0"] > crit["barre_lot0_z_seul"]
                 and crit["tous_folds_rr_ge_2"])
    crit["PROMOTION_M36"] = bool(promotion)
    pd.DataFrame([crit]).to_csv(REPORTS / "decision-promotion.csv", index=False)
    log(f"PROMOTION M3.6 : {promotion} ({crit})")

    # ---- modèle de scoring 2026 (train ≤2024, calibration 2025) ------------------
    df = load_ext(tuple(range(2017, 2027)))
    train = df[(df.annee >= 2017) & (df.annee <= 2024)].reset_index(drop=True)
    cal = df[df.annee == 2025].reset_index(drop=True)
    sc26 = df[df.annee == 2026].reset_index(drop=True)
    final = PModel(feature_names=[f.name for f in FEATURES])
    final.year_dummies = sorted(train.annee.unique())[:-1]
    final.interactions = m36_2025.interactions
    final.fit(train, train["label"].astype(int), C=5.0)
    final.calibrate(cal, cal["label"].astype(int))
    joblib.dump(final, REPORTS / "artifacts-m36-scoring2026.joblib")

    p26 = final.predict_proba(sc26)
    assert len(p26) == len(sc26) and not np.isnan(p26).any()
    sc26 = sc26.assign(p=p26, copro=sc26["idu"].map(copro).fillna(False))
    fonc = sc26[~sc26["copro"]].reset_index(drop=True)
    log(f"scoring 2026 : {len(sc26)} parcelles, univers foncier {len(fonc)}")

    contrib = final.contributions(fonc)
    top_mask = ev._ranked_top_mask(fonc["p"].to_numpy(), 1158,
                                   np.random.RandomState(974))
    top = fonc[top_mask].reset_index(drop=True)
    ctop = contrib[top_mask].reset_index(drop=True)
    feat_cols = [c for c in ctop.columns if not c.startswith("contrib_")]

    def lisible(i: int) -> list[str]:
        vals = ctop.loc[i, feat_cols].astype(float)
        best = vals.abs().sort_values(ascending=False).head(5).index
        out = []
        for f in best:
            base = f.split("*")[0] if "*" in f else f
            bf = final.encoder.binned.get(base)
            lab = ""
            if bf is not None and "*" not in f:
                bi = int(bf.bin_index(top.loc[[i], f])[0])
                lab = f" [{bf.bin_label(bi)}]"
            out.append(f"{f}{lab}: {vals[f]:+.3f}")
        return out

    cols5 = pd.DataFrame([lisible(i) for i in range(len(top))],
                         columns=[f"contribution_{j}" for j in range(1, 6)])
    export = pd.concat([
        pd.DataFrame({"parcelle_id": top["idu"], "commune": top["commune"],
                      "p_mutation_fonciere_12m": np.round(top["p"], 6),
                      "contrib_z": np.round(ctop["contrib_Z"], 4),
                      "contrib_d": np.round(ctop["contrib_D"], 4)}),
        cols5], axis=1).sort_values("p_mutation_fonciere_12m", ascending=False)
    export.to_csv(REPORTS / "top-1158-2026-foncier.csv", index=False)
    log(f"top-1158-2026-foncier.csv écrit ({len(export)} lignes)")


if __name__ == "__main__":
    main()
