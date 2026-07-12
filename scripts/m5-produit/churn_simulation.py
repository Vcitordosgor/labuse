"""M5 lot 2.3 — SIMULATION du churn chaude entre les scorings 01/01/2024 et
01/01/2025 (données ext existantes, artifact gelé, AUCUN ré-entraînement).

Cible : churn < 15 % par recalcul HORS événements (les événements datés ne sont
pas reconstruits rétroactivement — la simulation est donc « hors événements »
par construction, exactement le périmètre de la cible).
Scénarios : sans hystérésis (N_s = N_e), N_s = 1,4 × N_e (défaut mandat),
élargissements 1,6 / 1,8 si la cible n'est pas tenue.

Usage : LABUSE_DATABASE_URL=… python scripts/m5-produit/churn_simulation.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from labuse.db import engine
from labuse.scoring.p_model.features import derive
from labuse.scoring.p_v2 import SEED
from labuse.scoring.p_v2.pipeline import verify_artifact
from labuse.scoring.p_v2.statuts import TierParams, assign_tiers, calibre_n_entree, plancher_c

REPORTS = Path("reports/m5-produit")


def year_frame(annee: int, model, copro: pd.DataFrame, etage0: set) -> pd.DataFrame:
    df = pd.read_sql(text("SELECT * FROM p_model_ext_dataset WHERE annee = :a"),
                     engine(), params={"a": annee})
    df = derive(df).reset_index(drop=True)
    p = model.predict_proba(df)
    df = df.merge(copro, on="idu", how="left")
    df["copro"] = df["copro"].fillna(False).astype(bool)
    rng = np.random.RandomState(SEED)
    tie = rng.random(len(df))
    hors = ~df["copro"].to_numpy()
    rang = np.full(len(df), np.nan)
    order = np.lexsort((tie[hors], -p[hors]))
    rh = np.empty(hors.sum())
    rh[order] = np.arange(1, hors.sum() + 1)
    rang[hors] = rh
    return df.assign(p=p, rang=rang, contrib_d=0.0, event_age_mois=np.nan,
                     ecartee_etage0=df["idu"].isin(etage0))


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    model, _ = verify_artifact()
    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro "
                        "FROM p_model_ext_copro", engine())
    etage0 = set(pd.read_sql("""
        SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id = d.parcel_id
        WHERE d.run_label = 'q_v2' AND d.status IN ('exclue','faux_positif_probable')
    """, engine())["idu"])

    d24 = year_frame(2024, model, copro, etage0)
    d25 = year_frame(2025, model, copro, etage0)

    elig = d24[~d24["copro"] & ~d24["ecartee_etage0"]
               & plancher_c(d24, TierParams(1, 1))]
    n_e = calibre_n_entree(elig["rang"], cible=1150)

    rows = []
    for facteur in (1.0, 1.4, 1.6, 1.8):
        params = TierParams(n_entree=n_e, n_sortie=int(round(facteur * n_e)))
        t24 = assign_tiers(d24, params)
        prev = d25["idu"].map(pd.Series(t24.values, index=d24["idu"]))
        t25 = assign_tiers(d25, params, prev)
        hot24 = set(d24.loc[t24.isin(["chaude", "brulante"]), "idu"])
        hot25 = set(d25.loc[t25.isin(["chaude", "brulante"]), "idu"])
        sortants = len(hot24 - hot25)
        rows.append({
            "scenario": f"N_s = {facteur:.1f} × N_e" if facteur > 1 else "sans hystérésis",
            "n_entree": n_e, "n_sortie": params.n_sortie,
            "chaudes_2024": len(hot24), "chaudes_2025": len(hot25),
            "sortants": sortants, "entrants": len(hot25 - hot24),
            "churn_pct": round(sortants / max(len(hot24), 1) * 100, 1),
            "cible_15pct": sortants / max(len(hot24), 1) < 0.15,
        })
        print(rows[-1])
    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "churn-simulation.csv", index=False)
    retenu = out[out["cible_15pct"]].iloc[0] if out["cible_15pct"].any() else out.iloc[-1]
    print(f"\nscénario retenu : {retenu['scenario']} (churn {retenu['churn_pct']}%)")


if __name__ == "__main__":
    main()
