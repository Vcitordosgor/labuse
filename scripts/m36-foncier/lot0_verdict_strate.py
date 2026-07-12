"""M3.6 lot 0 — verdict stratifié copro/foncier. AUCUN ré-entraînement :
modèles gelés M3 (sha256 vérifié), test 2025 déjà lu (TEST-2025-LU.json),
seule la STRATE d'évaluation change (sous-univers hors copro).

RR@k hors copro = top-k recalculé PARMI les parcelles hors copro, taux de base
recalculé sur ce sous-univers. IC95 bootstrap seed 974.

Usage : LABUSE_DATABASE_URL=… python scripts/m36-foncier/lot0_verdict_strate.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from labuse.db import engine, session_scope
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model import ext_sql
from labuse.scoring.p_model.features import load_dataset
from labuse.scoring.p_model.model import PModel

REPORTS = Path("reports/m36-foncier")
ART = Path("reports/m3-p-model/artifacts")
K_LIST = (1158, 500)

_journal: list[str] = []


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    _journal.append(line)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    freeze = json.loads((ART / "FREEZE.json").read_text())
    marker = json.loads((ART / "TEST-2025-LU.json").read_text())
    log(f"modèle gelé M3 {freeze['sha256'][:16]}… ; test 2025 déjà lu le {marker['lu_le']} "
        "— lot 0 = re-stratification post-hoc, aucun re-fit")

    # ---- 0.1 flag copro -------------------------------------------------------
    with session_scope() as session:
        ext_sql.build_copro_flags(session)
    flags = pd.read_sql("SELECT idu, copro_rnic, copro_dvf FROM p_model_ext_copro", engine())
    flags["copro"] = flags["copro_rnic"] | flags["copro_dvf"]
    eff = {
        "parcelles": int(len(flags)),
        "copro_rnic": int(flags["copro_rnic"].sum()),
        "copro_dvf": int(flags["copro_dvf"].sum()),
        "copro_total": int(flags["copro"].sum()),
    }
    log(f"effectifs copro : {eff}")
    pd.DataFrame([eff]).to_csv(REPORTS / "effectifs-copro.csv", index=False)

    # ---- 0.2 verdict stratifié sur le test 2025 -------------------------------
    model = PModel.load(str(ART / "p_model.joblib"))
    model_z = PModel.load(str(ART / "p_model_z_seul.joblib"))
    df = load_dataset(engine(), (2025,)).reset_index(drop=True)
    df = df.merge(flags[["idu", "copro"]], on="idu", how="left")
    df["copro"] = df["copro"].fillna(False)

    y = df["label"].astype(int).to_numpy()
    scores = {
        "P (Z+D, calibré)": model.predict_proba(df),
        "ablation Z seul": model_z.predict_proba(df),
        "baseline rotation DVF secteur": (
            pd.to_numeric(df["rot_nu"], errors="coerce").fillna(0)
            + pd.to_numeric(df["rot_bati"], errors="coerce").fillna(0)).to_numpy(),
        "baseline V v1.3 (ties à 0/NULL seedés 974)": df.merge(
            pd.read_sql("SELECT parcelle_id AS idu, v_score FROM parcel_v_score", engine()),
            on="idu", how="left")["v_score"].to_numpy(dtype=float),
    }

    rows = []
    for strate, mask in [("hors_copro", ~df["copro"].to_numpy()),
                         ("copro", df["copro"].to_numpy()),
                         ("tout", np.ones(len(df), bool))]:
        ym = y[mask]
        for name, s in scores.items():
            for k in K_LIST:
                r = ev.bootstrap_rr(ym, s[mask], k)
                rows.append({"strate": strate, "n_univers": int(mask.sum()),
                             "score": name, **r})
        log(f"strate {strate} : n={mask.sum()}, taux base={ym.mean():.4%}")
    res = pd.DataFrame(rows)
    res.to_csv(REPORTS / "verdict-strate.csv", index=False)
    v = res[(res.strate == "hors_copro") & (res.k == 1158)][
        ["score", "rr", "ic95_bas", "ic95_haut", "taux_topk", "positifs_topk"]]
    log("VERDICT PRODUIT (hors copro, RR@1158) :\n" + v.to_string(index=False))

    # ---- 0.3 signe « permis < 24 mois » copro vs hors copro --------------------
    d234 = load_dataset(engine(), (2023, 2024)).merge(
        flags[["idu", "copro"]], on="idu", how="left")
    d234["copro"] = d234["copro"].fillna(False)
    dec = (d234.groupby(["copro", "permis_bin"])
           .agg(n=("label", "size"), taux_mutation=("label", "mean")).reset_index())
    dec.to_csv(REPORTS / "permis-signe-copro.csv", index=False)
    log("décomposition permis (2023-24) :\n" + dec.to_string(index=False))

    (REPORTS / "ORDRE-OPERATIONS-lot0.md").write_text(
        "# M3.6 lot 0 — re-stratification post-hoc (modèle gelé, zéro re-fit)\n\n"
        + "\n".join(f"- {ligne}" for ligne in _journal) + "\n")


if __name__ == "__main__":
    main()
