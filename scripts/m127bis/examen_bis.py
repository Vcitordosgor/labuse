"""M127-bis — le RE-EXAMEN après les trois réparations. Même protocole, même métrique,
même fold que M127/M36 : RR@1158 hors copro, fold 2025, référence 6,73.

Échelles :
  A = référence nettoyée (22 features, résiduel v1) — l'acquis gratuit du M127 (ancre)
  B = A + zéros M125 AVEC la cause en CATÉGORIE (réparation 2)
  C = B + features bâti (réparation 3)
  D = C + proc_collective (réparation 1 : le seul signal propriétaire daté — les 3
      instantanés ne concourent PAS, ils deviendront des faits affichés)
+ RR par segment nu/bâti (fold 2025) À CHAQUE échelle — c'est le bâti qu'on veut voir remonter.

Usage : python scripts/m127bis/examen_bis.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import average_precision_score  # noqa: F401 (parité protocole)

sys.path.insert(0, "scripts/m127")
from examen import KEPT, fit_fold, log  # protocole M127 réutilisé tel quel  # noqa: E402

from labuse.db import engine  # noqa: E402
from labuse.scoring.p_model import evaluate as ev  # noqa: E402
from labuse.scoring.p_model.features import FeatureSpec, derive  # noqa: E402

REPORTS = Path("reports/m127bis")
FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)
K = 1158

_ST = "état physique 2026 (statique consigné — le bâti bouge peu)"
CAUSE_SPEC = FeatureSpec("residuel_cause_cat", "D", "cat", 0,
                         "parcel_residuel.cause (M125)", "statique", "familles de cause")
BATI_SPECS = [
    FeatureSpec("taux_occupation", "D", "num", 0, "emprise/surface", "statique", _ST),
    FeatureSpec("nb_batiments", "D", "num", 0, "BD TOPO ∩ parcelle (≥10 m²)", "statique", _ST),
    FeatureSpec("bati_max_m2", "D", "num", 0, "BD TOPO", "statique", _ST),
    FeatureSpec("hauteur_max_m", "D", "num", 0, "BD TOPO attrs", "statique", _ST),
    FeatureSpec("etages_max", "D", "num", 0, "BD TOPO attrs", "statique", _ST),
    FeatureSpec("nb_logements_bdtopo", "D", "num", 0, "BD TOPO attrs", "statique", _ST),
    FeatureSpec("usage_dominant", "D", "cat", 0, "BD TOPO usage/nature", "statique", _ST),
    FeatureSpec("surelevation_possible", "D", "bool", 0, "parcel_residuel_bati", "statique", _ST),
    # pct_potentiel_v2 (bâti vs droits) entre comme num — la colonne existe au dataset
    FeatureSpec("pct_potentiel_v2", "D", "num", 0, "parcel_residuel (M125)", "statique",
                "bâti consommé / droits max — une case sur 2000 m² U ≠ immeuble saturé"),
]
PROC_SPEC = FeatureSpec("proc_collective", "D", "bool", 0, "BODACC pcl (M126)",
                        "as-of date_annonce", "2008+ ; lien parcelle→SIREN 2025 consigné")

LADDERS = {
    "A_ref": {"specs": KEPT, "residuel": "v1"},
    "B_causes": {"specs": KEPT + [CAUSE_SPEC], "residuel": "v2"},
    "C_bati": {"specs": KEPT + [CAUSE_SPEC] + BATI_SPECS, "residuel": "v2"},
    "D_proprio_date": {"specs": KEPT + [CAUSE_SPEC] + BATI_SPECS + [PROC_SPEC], "residuel": "v2"},
}


def load_v2bis() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM p_model_dataset_v2bis WHERE annee <= 2025", engine())
    df["pct_potentiel"] = df["pct_potentiel_v2"]
    df = derive(df)
    for b in ("proc_collective", "nu_constructible", "piscine", "sous_densite_v1",
              "sous_densite_v2", "surelevation_possible"):
        df[b] = df[b].map({True: "true", False: "false"}).astype(object)
    return df


def frame_for(df: pd.DataFrame, residuel: str) -> pd.DataFrame:
    out = df.copy()
    out["sdp_residuelle_m2"] = df[f"sdp_residuelle_m2_{residuel}"]
    out["sous_densite"] = df[f"sous_densite_{residuel}"]
    return out


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
                        engine()).set_index("idu")["copro"]
    log("chargement dataset v2bis…")
    df = load_v2bis()
    log(f"{len(df):,} lignes")

    rows, segs = [], []
    best = {}
    for ladder, spec in LADDERS.items():
        fdf = frame_for(df, spec["residuel"])
        for fy in FOLDS:
            r = fit_fold(fdf, spec["specs"], fy, copro)
            log(f"{ladder} fold {fy} : rr_hc {r['rr_hc']:.2f} "
                f"[{r['ic_bas_hc']:.2f},{r['ic_haut_hc']:.2f}] · ECE {r['ece']:.4f}")
            rows.append({"ladder": ladder, "fold": fy, "rr": r["rr"], "rr_hc": r["rr_hc"],
                         "ic_bas_hc": r["ic_bas_hc"], "ic_haut_hc": r["ic_haut_hc"],
                         "ece": r["ece"], "ap": r["ap"], "n_train": r["n_train"]})
            pd.DataFrame(rows).to_csv(REPORTS / "echelle-bis.csv", index=False)
            if fy == 2025:
                best[ladder] = r
                test, p, y, hc = r["test"], r["p"], r["y"], r["hc"]
                thc, phc, yhc = test[hc], p[hc], y[hc]
                for seg_name, mask in [("nu", (thc["nu"] == True).to_numpy()),      # noqa: E712
                                       ("bati", (thc["nu"] == False).to_numpy())]:  # noqa: E712
                    k_seg = max(1, int(round(K * mask.mean())))
                    rrk = ev.rr_at_k(yhc[mask], phc[mask], k_seg)
                    segs.append({"ladder": ladder, "segment": seg_name, "n": int(mask.sum()),
                                 "k": k_seg, "rr@k": rrk["rr"],
                                 "taux_base": rrk["taux_global"],
                                 "positifs_topk": rrk["positifs_topk"]})
                    log(f"  segment {seg_name}: rr@{k_seg} = {rrk['rr']:.2f}")
                pd.DataFrame(segs).to_csv(REPORTS / "segments-bis-2025.csv", index=False)

    # meilleur modèle (rr_hc fold 2025) → artefact d'examen + model-card
    champ = max(best, key=lambda k: best[k]["rr_hc"])
    m = best[champ]["model"]
    joblib.dump(m, REPORTS / f"artifact-m127bis-{champ}-fold2025.joblib")
    mrows = []
    for name, bf in m.encoder.binned.items():
        coef = m.coefs.get(name, 0.0)
        for i, w in enumerate(bf.woe):
            mrows.append((name, bf.bin_label(i), bf.counts[i], bf.event_rates[i], w, coef, coef * w))
        if bf.missing_count:
            mrows.append((name, "manquant/inconnu", bf.missing_count, bf.missing_rate,
                          bf.missing_woe, coef, coef * bf.missing_woe))
    pd.DataFrame(mrows, columns=["feature", "bin", "effectif", "taux_evenement",
                                 "woe", "coef", "log_hazard"]
                 ).to_csv(REPORTS / f"model-card-{champ}-2025.csv", index=False)
    log(f"FIN — meilleur : {champ} (rr_hc {best[champ]['rr_hc']:.2f})")


if __name__ == "__main__":
    main()
