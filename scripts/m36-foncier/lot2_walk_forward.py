"""M3.6 lot 2 — walk-forward long 2017-2025 sur label L2-F (L2 en contrôle).

Folds (train ≤ N-2 par binning+fit, calibration isotonique sur N-1, test N) :
  2020, 2021, 2022, 2023, 2024, 2025 — soit 6 verdicts hors-échantillon.
Interactions minées UNE FOIS sur le fold le plus ancien (train 2017-18, val 2019),
réutilisées ensuite. Par fold : RR@1158 (IC bootstrap), ECE, RR hors copro
(lentille produit), signes des coefficients — stabilité exigée sur ≥5/6 folds,
« permis <2a » et « piscine » suivis explicitement au niveau bin.

Usage : LABUSE_DATABASE_URL=… python scripts/m36-foncier/lot2_walk_forward.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from labuse.db import engine
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import FEATURES, derive
from labuse.scoring.p_model.model import PModel
from labuse.scoring.p_model.shadow import mine_interactions

REPORTS = Path("reports/m36-foncier")
FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)
ZD = [f.name for f in FEATURES]

META = ["idu", "annee", "label", "label_l2", "commune", "secteur", "owner_type",
        "n_mut_nu_36m", "n_mut_bati_36m", "stock_secteur", "window_coverage"]
RAW_FEATS = [f.name for f in FEATURES if f.name not in
             ("rot_nu", "rot_bati", "acces_equipements", "dormance_droits")]
SQL_COLS = sorted(set(META + RAW_FEATS
                      + ["pct_potentiel", "dist_ecole_m", "dist_sante_m",
                         "dist_commerce_m", "dist_tcsp_m"]) - {"window_coverage"})


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_ext(years: tuple[int, ...]) -> pd.DataFrame:
    cols = ", ".join(dict.fromkeys(SQL_COLS + ["window_coverage"]))
    yrs = ", ".join(str(y) for y in years)
    df = pd.read_sql(
        f"SELECT {cols} FROM p_model_ext_dataset WHERE annee IN ({yrs})", engine())
    return derive(df)


def bin_loghazard(model: PModel, feat: str, cat: str) -> float:
    bf = model.encoder.binned.get(feat)
    if bf is None or cat not in bf.categories:
        return float("nan")
    return model.coefs.get(feat, 0.0) * bf.woe[bf.categories[cat]]


def fit_fold(df: pd.DataFrame, test_year: int, label_col: str,
             interactions: list[tuple[str, str]], copro: pd.Series) -> dict:
    train = df[(df.annee >= 2017) & (df.annee <= test_year - 2)].reset_index(drop=True)
    cal = df[df.annee == test_year - 1].reset_index(drop=True)
    test = df[df.annee == test_year].reset_index(drop=True)
    y_tr = train[label_col].astype(int)
    y_cal = cal[label_col].astype(int)
    y_te = test[label_col].astype(int).to_numpy()

    m = PModel(feature_names=ZD)
    m.year_dummies = sorted(train.annee.unique())[:-1]  # référence = dernière année train
    m.interactions = interactions
    m.fit(train, y_tr, C=5.0)
    m.calibrate(cal, y_cal)

    p = m.predict_proba(test)
    n_boot = 1000 if test_year == 2025 else 500
    rr = ev.bootstrap_rr(y_te, p, 1158, n_boot=n_boot)
    ece, _ = ev.ece(y_te, p)
    hc = ~test["idu"].map(copro).fillna(False).to_numpy()
    rr_hc = ev.bootstrap_rr(y_te[hc], p[hc], 1158, n_boot=n_boot)

    return {
        "model": m, "p_test": p, "test_idu": test["idu"],
        "fold": test_year, "label": label_col,
        "n_train": len(train), "taux_test": float(y_te.mean()),
        "rr@1158": rr["rr"], "ic_bas": rr["ic95_bas"], "ic_haut": rr["ic95_haut"],
        "rr@1158_hors_copro": rr_hc["rr"], "ic_bas_hc": rr_hc["ic95_bas"],
        "ic_haut_hc": rr_hc["ic95_haut"],
        "ece": ece,
        "ap_test": float(average_precision_score(y_te, p)),
        "lh_permis_recent": bin_loghazard(m, "permis_bin", "<2a"),
        "lh_piscine": bin_loghazard(m, "piscine", "true"),
        "signes": {f: float(np.sign(m.coefs.get(f, 0.0))) for f in ZD},
    }


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    copro = pd.read_sql(
        "SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
        engine()).set_index("idu")["copro"]
    log("chargement dataset étendu 2017-2025…")
    df = load_ext(tuple(range(2017, 2026)))
    log(f"{len(df)} lignes chargées")

    # interactions : minées une fois sur le fold le plus ancien (train 17-18, val 19)
    tr0 = df[df.annee.isin((2017, 2018))].reset_index(drop=True)
    va0 = df[df.annee == 2019].reset_index(drop=True)
    seed_model = PModel(feature_names=ZD)
    seed_model.year_dummies = [2017]
    seed_model.fit(tr0, tr0["label"].astype(int), C=5.0)
    inter, jdf = mine_interactions(seed_model, tr0, tr0["label"].astype(int),
                                   va0, va0["label"].astype(int))
    jdf.to_csv(REPORTS / "interactions-fold-ancien.csv", index=False)
    log(f"croisements minés sur fold ancien : {inter}")

    rows, signes_rows = [], []
    p2025 = {}
    for label_col in ("label", "label_l2"):
        for fy in FOLDS:
            r = fit_fold(df, fy, label_col, inter, copro)
            log(f"fold {fy} [{label_col}] : RR@1158={r['rr@1158']:.1f} "
                f"[{r['ic_bas']:.1f},{r['ic_haut']:.1f}] | hors copro "
                f"{r['rr@1158_hors_copro']:.1f} | ECE {r['ece']:.5f}")
            if label_col == "label":
                signes_rows.append({"fold": fy, **r["signes"],
                                    "lh_permis_recent": r["lh_permis_recent"],
                                    "lh_piscine": r["lh_piscine"]})
                if fy == 2025:
                    p2025 = {"idu": r["test_idu"], "p": r["p_test"], "model": r["model"]}
            rows.append({k: v for k, v in r.items()
                         if k not in ("model", "p_test", "test_idu", "signes")})

    wf = pd.DataFrame(rows)
    wf.to_csv(REPORTS / "walk-forward.csv", index=False)

    sg = pd.DataFrame(signes_rows).set_index("fold")
    feat_cols = [c for c in sg.columns if not c.startswith("lh_")]
    stab = pd.DataFrame({
        "feature": feat_cols,
        "signe_majoritaire": [np.sign(sg[c].sum()) for c in feat_cols],
        "n_folds_concordants": [int((sg[c] == np.sign(sg[c].sum())).sum()) if sg[c].sum() != 0
                                else int((sg[c] == 0).sum()) for c in feat_cols],
        "stable_5_sur_6": [bool((sg[c] == np.sign(sg[c].sum())).sum() >= 5) if sg[c].sum() != 0
                           else False for c in feat_cols],
    })
    stab.to_csv(REPORTS / "stabilite-signes.csv", index=False)
    sg[["lh_permis_recent", "lh_piscine"]].to_csv(REPORTS / "suivi-permis-piscine.csv")
    log(f"signes stables (≥5/6) : {int(stab['stable_5_sur_6'].sum())}/{len(stab)}")

    # scores 2025 du fold final, pour le comparatif lot 3 (overlap top-1158 vs M3)
    pd.DataFrame({"idu": p2025["idu"], "p_l2f": p2025["p"]}).to_csv(
        REPORTS / "scores-2025-fold-final.csv", index=False)
    import joblib
    joblib.dump(p2025["model"], REPORTS / "artifacts-m36-fold2025.joblib")
    log("FIN lot 2")


if __name__ == "__main__":
    main()
