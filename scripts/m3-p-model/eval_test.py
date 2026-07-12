"""Lot 5 — évaluation stricte. ORDRE IMPOSÉ ET TRACÉ :

  1. vérifie le gel (FREEZE.json) et l'absence de lecture antérieure du test ;
  2. CONTRÔLES NÉGATIFS sur val 2024 (labels permutés intra-année ≈ RR 1 ;
     features décalées +1 an, c.-à-d. rassies d'un an → chute attendue) ;
  3. churn : top-1158 au 01/01/2024 vs 01/01/2025 (aucun label utilisé) ;
  4. LECTURE UNIQUE du test 2025 : RR@1158/500 (IC95 bootstrap), lift, ventilation
     PM/PP/public/bailleur, baselines (rotation seule ; V v1.3 au même k, ties
     seedés ; ablation Z-seul), ECE + fiabilité.

Le verdict test est reporté MÊME s'il est décevant.
Usage : LABUSE_DATABASE_URL=… python scripts/m3-p-model/eval_test.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from labuse.db import engine
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import load_dataset
from labuse.scoring.p_model.model import PModel

REPORTS = Path("reports/m3-p-model")
ART = REPORTS / "artifacts"
MARKER = ART / "TEST-2025-LU.json"
K_LIST = (1158, 500)

_journal: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    _journal.append(line)


def main() -> None:
    freeze = json.loads((ART / "FREEZE.json").read_text())
    log(f"modèle gelé le {freeze['gel']} (sha256 {freeze['sha256'][:16]}…)")
    if MARKER.exists():
        log("ATTENTION : le test 2025 a DÉJÀ été lu — protocole verrouillé, abandon.")
        sys.exit(1)
    model = PModel.load(str(ART / "p_model.joblib"))
    model_z = PModel.load(str(ART / "p_model_z_seul.joblib"))

    # ---------- 2. contrôles négatifs sur VAL (le test n'est pas encore chargé) --
    dfv = load_dataset(engine(), (2023, 2024))
    val = dfv[dfv.annee == 2024].reset_index(drop=True)
    yval = val["label"].astype(int).to_numpy()
    p_val = model.predict_proba(val)

    perm = ev.permutation_control(yval, p_val, val["annee"].to_numpy(), 1158)
    log(f"contrôle labels permutés intra-année (val) : RR@1158 = {perm['rr']:.3f} (attendu ≈ 1)")

    # features « décalées +1 an » : labels 2024 appariés aux features as-of 01/01/2023
    stale = dfv[dfv.annee == 2023].set_index("idu")
    lab24 = val.set_index("idu")["label"].astype(int)
    common = stale.index.intersection(lab24.index)
    stale = stale.loc[common].reset_index()
    y_stale = lab24.loc[common].to_numpy()
    p_stale = model.predict_proba(stale)
    rr_true = ev.rr_at_k(yval, p_val, 1158)["rr"]
    rr_stale = ev.rr_at_k(y_stale, p_stale, 1158)["rr"]
    log(f"contrôle features rassies d'un an (val) : RR@1158 {rr_stale:.2f} vs {rr_true:.2f} "
        f"à jour (chute attendue)")

    controles = pd.DataFrame([
        {"controle": "labels permutés intra-année (val 2024)", "rr@1158": perm["rr"],
         "attendu": "≈ 1", "verdict": "PASS" if abs(perm["rr"] - 1) < 0.5 else "FAIL"},
        {"controle": "features décalées +1 an (val 2024)", "rr@1158": rr_stale,
         "attendu": f"< {rr_true:.2f} (à jour)",
         "verdict": "PASS" if rr_stale < rr_true else "FAIL"},
    ])
    controles.to_csv(REPORTS / "controles-negatifs.csv", index=False)
    if (controles["verdict"] == "FAIL").any():
        log("CONTRÔLE NÉGATIF EN ÉCHEC — le test ne sera PAS lu. Abandon.")
        (REPORTS / "ORDRE-OPERATIONS-lot5.md").write_text(
            "# Lot 5 — ABANDON avant lecture du test\n\n" + "\n".join(f"- {ligne}" for ligne in _journal))
        sys.exit(1)

    # ---------- 3. churn top-1158 : scoring 01/01/2024 vs 01/01/2025 (sans labels) --
    df25 = load_dataset(engine(), (2025,))
    feats25 = df25.drop(columns=["label"])          # les labels 2025 restent scellés ici
    s24 = pd.Series(model.predict_proba(val), index=val["idu"])
    s25 = pd.Series(model.predict_proba(feats25), index=feats25["idu"])
    churn = ev.churn_topk(s24, s25, 1158)
    log(f"churn top-1158 2024→2025 : overlap {churn['overlap']} ({churn['overlap_pct']:.1%})")
    pd.DataFrame([churn]).to_csv(REPORTS / "churn-top1158.csv", index=False)

    # ---------- 4. LECTURE UNIQUE DU TEST 2025 -----------------------------------
    log("=== LECTURE UNIQUE DU TEST 2025 — début ===")
    MARKER.write_text(json.dumps({"lu_le": time.strftime("%Y-%m-%d %H:%M:%S"),
                                  "sha256_modele": freeze["sha256"]}, indent=2))
    test = df25.reset_index(drop=True)
    ytest = test["label"].astype(int).to_numpy()
    p_test = model.predict_proba(test)
    log(f"test 2025 : {len(test)} lignes, {ytest.mean():.4%} positifs")

    rows = []
    for k in K_LIST:
        rows.append({"score": "P (Z+D, calibré)", **ev.bootstrap_rr(ytest, p_test, k)})
    p_z = model_z.predict_proba(test)
    for k in K_LIST:
        rows.append({"score": "ablation Z seul", **ev.bootstrap_rr(ytest, p_z, k)})
    rot = (pd.to_numeric(test["rot_nu"], errors="coerce").fillna(0)
           + pd.to_numeric(test["rot_bati"], errors="coerce").fillna(0)).to_numpy()
    for k in K_LIST:
        rows.append({"score": "baseline rotation DVF secteur", **ev.bootstrap_rr(ytest, rot, k)})
    vsc = pd.read_sql("SELECT parcelle_id AS idu, v_score FROM parcel_v_score", engine())
    v = test.merge(vsc, on="idu", how="left")["v_score"].to_numpy(dtype=float)
    for k in K_LIST:
        rows.append({"score": "baseline V v1.3 (ties à 0/NULL seedés 974)",
                     **ev.bootstrap_rr(ytest, v, k)})
    res = pd.DataFrame(rows)
    res.to_csv(REPORTS / "test-2025-resultats.csv", index=False)
    log("résultats test :\n" + res.to_string(index=False))

    ev.lift_table(ytest, p_test).to_csv(REPORTS / "test-2025-lift.csv", index=False)
    ev.ventilation(test, ytest, p_test, 1158).to_csv(
        REPORTS / "test-2025-ventilation-owner.csv", index=False)
    ece_t, rel = ev.ece(ytest, p_test)
    rel.to_csv(REPORTS / "test-2025-calibration.csv", index=False)
    log(f"ECE test : {ece_t:.5f} | AP {average_precision_score(ytest, p_test):.5f} "
        f"| AUC {roc_auc_score(ytest, p_test):.4f}")
    log("=== LECTURE UNIQUE DU TEST 2025 — fin ===")

    (REPORTS / "ORDRE-OPERATIONS-lot5.md").write_text(
        "# Lot 5 — ordre des opérations (gel → contrôles → churn → test UNIQUE)\n\n"
        + "\n".join(f"- {ligne}" for ligne in _journal) + "\n")


if __name__ == "__main__":
    main()
