"""SCORING-1 (audit, lecture seule) — chargement commun.

Charge l'artefact GELÉ servi (m36-l2f-2026), le dataset réel (p_model_ext_dataset),
reconstruit les probabilités du modèle P. NE MODIFIE RIEN. NE RÉÉCRIT AUCUNE TABLE.

Le harnais est VALIDÉ contre la prod : la p reconstruite pour l'année scorée doit
coïncider avec parcel_p_score_v2.p_raw du run servi (q_v11_m137) — voir validate().
"""
from __future__ import annotations

import os
import sys
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from labuse.scoring.p_model.features import derive, FEATURES  # noqa: E402
from labuse.scoring.p_model.model import PModel  # noqa: E402

DB = os.environ.get("LABUSE_DATABASE_URL",
                    "postgresql+psycopg://openclaw@localhost:5432/labuse")
ARTIFACT = ROOT / "reports/m36-foncier/artifacts-m36-scoring2026.joblib"
FREEZE = ROOT / "reports/m36-foncier/FREEZE-scoring2026.json"
SERVED_RUN = "q_v11_m137"


def engine():
    from sqlalchemy import create_engine
    return create_engine(DB)


def load_model() -> PModel:
    import joblib
    sha = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    freeze = json.loads(FREEZE.read_text())
    assert sha == freeze["sha256"], f"sha mismatch {sha} != {freeze['sha256']}"
    return joblib.load(ARTIFACT)


def load_year(eng, annee: int) -> pd.DataFrame:
    df = pd.read_sql(f"SELECT * FROM p_model_ext_dataset WHERE annee = {int(annee)}", eng)
    return derive(df).reset_index(drop=True)


def recalibrated_model(eng, model: PModel | None = None) -> tuple[PModel, int]:
    """Modèle avec l'intercept recalé sur la dernière année labellisée — EXACTEMENT
    comme le pipeline de prod (politique 1.3)."""
    model = model or load_model()
    last = int(pd.read_sql(
        "SELECT max(annee) FROM p_model_ext_dataset WHERE label IS NOT NULL", eng).iloc[0, 0])
    dcal = load_year(eng, last)
    m = copy.deepcopy(model)
    m.recale_intercept(dcal, dcal["label"].astype(int))
    return m, last


def validate(eng) -> dict:
    """Le harnais reproduit-il la prod ? Compare p reconstruite (année scorée) à
    parcel_p_score_v2.p_raw du run servi, sur les parcelles NON pondérées AU."""
    annee_scored = int(pd.read_sql(
        "SELECT (params->>'annee_features')::int FROM p_score_v2_runs "
        f"WHERE run_id = '{SERVED_RUN}'", eng).iloc[0, 0])
    m, _ = recalibrated_model(eng)
    df = load_year(eng, annee_scored)
    p = m.predict_proba(df)
    stored = pd.read_sql(
        f"SELECT parcelle_id AS idu, p_raw FROM parcel_p_score_v2 WHERE run_id = '{SERVED_RUN}'",
        eng)
    j = df[["idu"]].assign(p_recon=p).merge(stored, on="idu", how="inner")
    j["diff"] = (j["p_recon"] - j["p_raw"]).abs()
    return {"annee_scored": annee_scored, "n": len(j),
            "max_diff": float(j["diff"].max()),
            "median_diff": float(j["diff"].median()),
            "n_diff_gt_1e4": int((j["diff"] > 1e-4).sum())}


if __name__ == "__main__":
    eng = engine()
    print(json.dumps(validate(eng), indent=2, ensure_ascii=False))
