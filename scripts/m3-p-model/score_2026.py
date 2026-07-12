"""Lot 6 — scoring 2026 (préversion produit).

Features au 01/01/2026 (DVF/Sitadel → 31/12/2025) → P sur la totalité du parc.
Intercept recalé sur l'année labellisée la plus récente (2025) — coefficients et
calibration val inchangés (mandat 4.4). Écrit :
  - table NOUVELLE p_model_scores_2026 (parcelle, P, décile, contrib Z, contrib D)
    — jamais dans les tables de prod ;
  - reports/m3-p-model/top-1158-2026.csv avec les 5 premières contributions
    lisibles par parcelle (feature = bin → log-hazard signé).

Usage : LABUSE_DATABASE_URL=… python scripts/m3-p-model/score_2026.py
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from labuse.db import engine, session_scope
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import load_dataset
from labuse.scoring.p_model.model import PModel

REPORTS = Path("reports/m3-p-model")
ART = REPORTS / "artifacts"


def main() -> None:
    model = PModel.load(str(ART / "p_model.joblib"))

    # Recalage d'intercept sur 2025 (année labellisée la plus récente) — production
    # post-évaluation : les labels 2025 sont utilisables ici, le verdict test est déjà figé.
    df25 = load_dataset(engine(), (2025,))
    model.recale_intercept(df25, df25["label"].astype(int))
    print(f"intercept recalé sur 2025 : décalage {model.intercept_shift:+.4f}")

    df26 = load_dataset(engine(), (2026,))
    assert df26["label"].isna().all(), "2026 ne doit avoir AUCUN label"
    p = model.predict_proba(df26)
    assert len(p) == len(df26) and not np.isnan(p).any(), "P manquant — NA interdit"

    contrib = model.contributions(df26)
    decile = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False) + 1

    out = pd.DataFrame({
        "parcelle_id": df26["idu"],
        "p_mutation_12m": np.round(p, 6),
        "decile": decile.astype(int),
        "contrib_z": np.round(contrib["contrib_Z"].to_numpy(), 4),
        "contrib_d": np.round(contrib["contrib_D"].to_numpy(), 4),
    })
    with session_scope() as session:
        session.execute(text("DROP TABLE IF EXISTS p_model_scores_2026"))
        session.execute(text("""
            CREATE TABLE p_model_scores_2026 (
                parcelle_id varchar(14) PRIMARY KEY,
                p_mutation_12m double precision NOT NULL,
                decile smallint NOT NULL,
                contrib_z double precision NOT NULL,
                contrib_d double precision NOT NULL,
                version varchar(24) NOT NULL DEFAULT 'm3-phase1'
            )"""))
        out.to_sql("p_model_scores_2026", session.connection(), if_exists="append",
                   index=False, method="multi", chunksize=5000)
    n = len(out)
    print(f"p_model_scores_2026 : {n} parcelles scorées (100 % du parc, aucun NA)")

    # ---- top-1158 avec 5 contributions lisibles --------------------------------
    rng = np.random.RandomState(974)
    top_mask = ev._ranked_top_mask(p, 1158, rng)
    top = df26[top_mask].reset_index(drop=True)
    ctop = contrib[top_mask].reset_index(drop=True)
    feat_cols = [c for c in ctop.columns if not c.startswith("contrib_")]

    def lisible(i: int) -> list[str]:
        vals = ctop.loc[i, feat_cols].astype(float)
        best = vals.abs().sort_values(ascending=False).head(5).index
        out5 = []
        for f in best:
            base = f.split("*")[0] if "*" in f else f
            bf = model.encoder.binned.get(base)
            lab = ""
            if bf is not None and "*" not in f:
                bi = int(bf.bin_index(top.loc[[i], f])[0])
                lab = f" [{bf.bin_label(bi)}]"
            out5.append(f"{f}{lab}: {vals[f]:+.3f}")
        return out5

    cols5 = pd.DataFrame([lisible(i) for i in range(len(top))],
                         columns=[f"contribution_{j}" for j in range(1, 6)])
    export = pd.concat([
        pd.DataFrame({"parcelle_id": top["idu"], "commune": top["commune"],
                      "p_mutation_12m": np.round(p[top_mask], 6),
                      "contrib_z": np.round(ctop["contrib_Z"], 4),
                      "contrib_d": np.round(ctop["contrib_D"], 4)}),
        cols5], axis=1).sort_values("p_mutation_12m", ascending=False)
    export.to_csv(REPORTS / "top-1158-2026.csv", index=False)
    print(f"top-1158-2026.csv écrit ({len(export)} lignes) — {time.strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
