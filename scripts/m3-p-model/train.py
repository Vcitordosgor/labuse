"""Lots 2-4 — entraînement du modèle P (Z puis Z+D), sensibilité train étendu,
mining d'interactions (GBM shadow), calibration isotonique, GEL du modèle.

Protocole (tracé dans reports/m3-p-model/ORDRE-OPERATIONS.md) :
  1. train = 2023, val = 2024. Le TEST 2025 N'EST PAS LU ICI.
  2. C (régularisation) choisi sur val ; ablation Z-seul vs Z+D sur val ;
     sensibilité train 2022+2023 (fenêtres dégradées + window_coverage) sur val.
  3. GBM shadow → ≤ 5 croisements réinjectés si gain val (le GBM ne sort jamais).
  4. Calibration isotonique sur val 2024, puis GEL (joblib + manifeste sha256).

Usage : LABUSE_DATABASE_URL=… python scripts/m3-p-model/train.py
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from labuse.db import engine
from labuse.scoring.p_model import SEED
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import FEATURES, generate_dictionary, load_dataset
from labuse.scoring.p_model.model import PModel
from labuse.scoring.p_model.shadow import mine_interactions

REPORTS = Path("reports/m3-p-model")
ART = REPORTS / "artifacts"
K_LIST = (1158, 500)

Z_FEATURES = [f.name for f in FEATURES if f.bloc == "Z"]
ZD_FEATURES = [f.name for f in FEATURES]

_journal: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    _journal.append(line)


def val_metrics(model: PModel, df_val: pd.DataFrame, y_val: pd.Series) -> dict:
    p = model.predict_proba(df_val)
    out = {"val_ap": float(average_precision_score(y_val, p)),
           "val_auc": float(roc_auc_score(y_val, p))}
    for k in K_LIST:
        out[f"val_rr@{k}"] = ev.rr_at_k(y_val.to_numpy(), p, k)["rr"]
    return out


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    log("DÉBUT lot 4 — le test 2025 n'est pas chargé (années lues : 2022, 2023, 2024)")

    df = load_dataset(engine(), (2022, 2023, 2024))
    train23 = df[df.annee == 2023].reset_index(drop=True)
    train22_23 = df[df.annee.isin((2022, 2023))].reset_index(drop=True)
    val = df[df.annee == 2024].reset_index(drop=True)
    y23, y2223, yval = (d["label"].astype(int) for d in (train23, train22_23, val))
    log(f"train 2023 : {len(train23)} lignes, {y23.mean():.4%} positifs ; "
        f"val 2024 : {len(val)} lignes, {yval.mean():.4%} positifs")

    results = []

    # ---- 1. C sur val (Z+D, train 2023) --------------------------------------
    best = None
    for C in (0.05, 0.2, 1.0, 5.0):
        m = PModel(feature_names=ZD_FEATURES).fit(train23, y23, C=C)
        met = val_metrics(m, val, yval)
        results.append({"config": f"Z+D train23 C={C}", **met})
        log(f"Z+D C={C} : {met}")
        if best is None or met["val_ap"] > best[1]["val_ap"]:
            best = (C, met)
    C = best[0]
    log(f"C retenu (val) : {C}")

    # ---- 2. Ablation Z-seul vs Z+D (train 2023) -------------------------------
    mZ = PModel(feature_names=Z_FEATURES).fit(train23, y23, C=C)
    metZ = val_metrics(mZ, val, yval)
    results.append({"config": "Z seul train23", **metZ})
    mZD = PModel(feature_names=ZD_FEATURES).fit(train23, y23, C=C)
    metZD = val_metrics(mZD, val, yval)
    results.append({"config": "Z+D train23", **metZD})
    log(f"ablation : Z seul {metZ} | Z+D {metZD}")

    # ---- 3. Sensibilité train étendu 2022+2023 (lot 1.4) ----------------------
    mExt = PModel(feature_names=ZD_FEATURES)
    mExt.year_dummies = [2022]  # intercept par année (référence 2023)
    mExt.fit(train22_23, y2223, C=C)
    metExt = val_metrics(mExt, val, yval)
    results.append({"config": "Z+D train22+23", **metExt})
    log(f"sensibilité train étendu : {metExt}")

    use_ext = metExt["val_ap"] > metZD["val_ap"]
    train_df, y_train = (train22_23, y2223) if use_ext else (train23, y23)
    base_model = mExt if use_ext else mZD
    log(f"ARBITRAGE val : train {'2022+2023' if use_ext else '2023 seul'}")

    # ---- 4. GBM shadow → interactions ----------------------------------------
    inter, jdf = mine_interactions(base_model, train_df, y_train, val, yval)
    jdf.to_csv(REPORTS / "interactions-journal.csv", index=False)
    log(f"croisements retenus ({len(inter)}) : {inter}")

    final = PModel(feature_names=ZD_FEATURES)
    final.year_dummies = [2022] if use_ext else []
    final.interactions = inter
    final.fit(train_df, y_train, C=C)
    met_final = val_metrics(final, val, yval)
    results.append({"config": "FINAL avant calibration", **met_final})

    # ---- 5. Baselines sur val (chaque bloc prouve son incrément AVANT le test) -
    rot = (pd.to_numeric(val["rot_nu"], errors="coerce").fillna(0)
           + pd.to_numeric(val["rot_bati"], errors="coerce").fillna(0)).to_numpy()
    base_rot = {f"val_rr@{k}": ev.rr_at_k(yval.to_numpy(), rot, k)["rr"] for k in K_LIST}
    results.append({"config": "BASELINE rotation seule", **base_rot})
    vsc = pd.read_sql("SELECT parcelle_id AS idu, v_score FROM parcel_v_score", engine())
    v = val.merge(vsc, on="idu", how="left")["v_score"].to_numpy(dtype=float)
    base_v = {f"val_rr@{k}": ev.rr_at_k(yval.to_numpy(), v, k)["rr"] for k in K_LIST}
    results.append({"config": "BASELINE V v1.3 (ties seedés)", **base_v})
    log(f"baselines val : rotation {base_rot} | V {base_v}")

    # ---- 6. Calibration isotonique sur val + ECE ------------------------------
    final.calibrate(val, yval)
    p_cal = final.predict_proba(val)
    ece_val, rel = ev.ece(yval.to_numpy(), p_cal)
    rel.to_csv(REPORTS / "calibration-val.csv", index=False)
    log(f"ECE val (après isotonique) : {ece_val:.5f}")
    results.append({"config": "FINAL calibré (val)", "val_ece": ece_val,
                    **val_metrics(final, val, yval)})

    # ---- 7. GEL ----------------------------------------------------------------
    final.meta.update({"train": "2022+2023" if use_ext else "2023",
                       "C": C, "interactions": [list(t) for t in inter],
                       "seed": SEED, "gel": time.strftime("%Y-%m-%d %H:%M:%S")})
    path = ART / "p_model.joblib"
    final.save(str(path))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (ART / "FREEZE.json").write_text(json.dumps(
        {"sha256": sha, "gel": final.meta["gel"], "meta": final.meta,
         "protocole": "modèle gelé sur val 2024 — le test 2025 n'a PAS été lu"},
        indent=2, ensure_ascii=False))
    log(f"MODÈLE GELÉ : {path} sha256={sha[:16]}…")

    # Z-seul gelé lui aussi (baseline d'ablation au test, même calibration val)
    mZ_cal = PModel(feature_names=Z_FEATURES)
    mZ_cal.year_dummies = final.year_dummies
    mZ_cal.fit(train_df, y_train, C=C).calibrate(val, yval)
    mZ_cal.save(str(ART / "p_model_z_seul.joblib"))

    pd.DataFrame(results).to_csv(REPORTS / "val-resultats.csv", index=False)
    final.model_card_rows().to_csv(REPORTS / "model-card-bins.csv", index=False)
    (REPORTS / "dictionnaire-features.md").write_text(generate_dictionary())
    iv = final.encoder.iv_table()
    iv.to_csv(REPORTS / "iv-features.csv", index=False)
    (REPORTS / "ORDRE-OPERATIONS.md").write_text(
        "# Ordre des opérations — lots 2-4 (avant tout accès au test)\n\n"
        + "\n".join(f"- {ligne}" for ligne in _journal) + "\n")
    log("FIN lot 4")


if __name__ == "__main__":
    main()
