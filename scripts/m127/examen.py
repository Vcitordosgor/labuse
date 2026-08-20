"""M127 Phases 2-5 — L'EXAMEN : échelle d'ablation A/C/D, pondération, segments,
ablation statiques, challenger GBM. Même protocole que M36 (lot2_walk_forward) :
train ≤ N-2 (binning+fit sur train SEUL), calibration isotonique N-1, test N ;
métrique de promotion RR@1158 HORS COPRO fold 2025 ; référence à battre 6,73.

PRÉMISSE CORRIGÉE : la profondeur DVF est DÉJÀ dans la référence (EXT_DVF_START=2014,
M3.5/M3.6) — la marche « B » est un no-op, l'échelle réelle est A → C → D.

RIEN de servi ne bouge : lit p_model_dataset_v2, écrit reports/m127/ uniquement.
Usage : python scripts/m127/examen.py
"""
from __future__ import annotations

import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score

from labuse.db import engine
from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.features import FEATURES, FeatureSpec, derive
from labuse.scoring.p_model.model import PModel
from labuse.scoring.p_model.woe import WoeEncoder

REPORTS = Path("reports/m127")
FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)
K = 1158
SEED = 974

#: les 5 croisements de BASE (FREEZE M36) — on change la MATIÈRE, pas la mécanique.
INTERACTIONS = [("tenure_bin", "permis_bin"), ("tenure_bin", "surface_m2"),
                ("ndvi_moyen", "zone_plu"), ("tenure_bin", "rot_nu"),
                ("surface_m2", "permis_bin")]

#: retraits physiques (7 mortes/retirées) + les 22 conservées, spec reprise du registre.
RETRAITS = {"qpv", "friche", "window_coverage", "pv_candidat",
            "permis_24m_norm", "filo_dens_pop", "dormance_droits"}
KEPT = [f for f in FEATURES if f.name not in RETRAITS and not f.retired]

_ST = "instantané 2026 consigné (prudence : ablation statiques dédiée)"
#: les candidates M126 (division_recente exclue — morte-née). `retired=False` implicite.
NEW_SPECS = [
    FeatureSpec("proc_collective", "D", "bool", 0, "BODACC pcl (M126)", "as-of date_annonce", "2008+"),
    FeatureSpec("succession_indivision", "D", "bool", 0, "veille RNE (M126)", "statique", _ST),
    FeatureSpec("age_dirigeant_bin", "D", "cat", 0, "RNE naissance (M126)", "âge exact au 01/01/Y", "liste 2026 consignée"),
    FeatureSpec("pm_nue_dormante", "D", "bool", 0, "prédicat nu_pm (M126)", "statique", _ST),
    FeatureSpec("contagion_voisinage", "Z", "num", 0, "adjacence × DVF L2 (M126)", "24 mois as-of", "2014+"),
    FeatureSpec("vente_tab_proximite", "Z", "bool", 0, "DVF VTB ≤300 m (M126)", "24 mois as-of", "2014+"),
    FeatureSpec("permis_etat", "D", "cat", 0, "Sitadel3 état (M126)", "autorisation as-of ; état 2026", _ST),
    FeatureSpec("pc_accorde_jamais_commence", "D", "bool", 0, "Sitadel3 (M126)", "idem", _ST),
]
STATIQUES_PRUDENCE = {"succession_indivision", "pm_nue_dormante",
                      "permis_etat", "pc_accorde_jamais_commence"}

LADDERS = {
    "A_nettoyage": {"specs": KEPT, "residuel": "v1"},
    "C_zeros_m125": {"specs": KEPT, "residuel": "v2"},
    "D_complet": {"specs": KEPT + NEW_SPECS, "residuel": "v2"},
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_v2() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM p_model_dataset_v2 WHERE annee <= 2025", engine())
    # dérivations du registre (shrinkage rotations, accès équipements) — pct_potentiel
    # requis par derive() (dormance retirée : calculée puis ignorée)
    df["pct_potentiel"] = df["pct_potentiel_v2"]
    df = derive(df)
    # bool pandas → object propre pour le binning catégoriel
    for b in ("proc_collective", "succession_indivision", "pm_nue_dormante",
              "vente_tab_proximite", "pc_accorde_jamais_commence", "nu_constructible",
              "piscine", "sous_densite_v1", "sous_densite_v2"):
        df[b] = df[b].map({True: "true", False: "false"}).astype(object)
    return df


def frame_for(df: pd.DataFrame, residuel: str) -> pd.DataFrame:
    out = df.copy()
    out["sdp_residuelle_m2"] = df[f"sdp_residuelle_m2_{residuel}"]
    out["sous_densite"] = df[f"sous_densite_{residuel}"]
    return out


def fit_fold(df: pd.DataFrame, specs: list, test_year: int, copro: pd.Series,
             weight_hl: float | None = None) -> dict:
    names = [s.name for s in specs]
    train = df[(df.annee >= 2017) & (df.annee <= test_year - 2)].reset_index(drop=True)
    cal = df[df.annee == test_year - 1].reset_index(drop=True)
    test = df[df.annee == test_year].reset_index(drop=True)
    y_tr, y_cal = train["label"].astype(int), cal["label"].astype(int)
    y_te = test["label"].astype(int).to_numpy()

    enc = WoeEncoder(min_count=200).fit(train, y_tr, specs)   # bornes sur TRAIN SEUL
    m = PModel(feature_names=names, encoder=enc)
    m.year_dummies = sorted(train.annee.unique())[:-1]
    m.interactions = [(a, b) for a, b in INTERACTIONS if a in names and b in names]
    sw = None
    if weight_hl:                       # décroissance exponentielle par ancienneté d'année
        age = (test_year - 2) - train["annee"].to_numpy()
        sw = np.power(0.5, age / weight_hl)
    m.fit(train, y_tr, C=5.0, sample_weight=sw)
    m.calibrate(cal, y_cal)

    p = m.predict_proba(test)
    n_boot = 1000 if test_year == 2025 else 400
    hc = ~test["idu"].map(copro).fillna(False).to_numpy()
    rr = ev.bootstrap_rr(y_te, p, K, n_boot=n_boot)
    rr_hc = ev.bootstrap_rr(y_te[hc], p[hc], K, n_boot=n_boot)
    ece, _ = ev.ece(y_te, p)
    return {"fold": test_year, "model": m, "p": p, "test": test, "hc": hc, "y": y_te,
            "rr": rr["rr"], "rr_hc": rr_hc["rr"],
            "ic_bas_hc": rr_hc["ic95_bas"], "ic_haut_hc": rr_hc["ic95_haut"],
            "ece": ece, "ap": float(average_precision_score(y_te, p)),
            "n_train": len(train)}


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
                        engine()).set_index("idu")["copro"]
    log("chargement dataset v2 (2017-2025)…")
    df = load_v2()
    log(f"{len(df):,} lignes")

    # ── Phase 4 · l'échelle A → C → D, walk-forward complet ─────────────────────
    rows = []
    keep_2025 = {}
    for ladder, spec in LADDERS.items():
        fdf = frame_for(df, spec["residuel"])
        for fy in FOLDS:
            r = fit_fold(fdf, spec["specs"], fy, copro)
            log(f"{ladder} fold {fy} : RR@{K} hors copro {r['rr_hc']:.2f} "
                f"[{r['ic_bas_hc']:.2f},{r['ic_haut_hc']:.2f}] · ECE {r['ece']:.4f}")
            rows.append({"ladder": ladder, "fold": fy, "rr": r["rr"], "rr_hc": r["rr_hc"],
                         "ic_bas_hc": r["ic_bas_hc"], "ic_haut_hc": r["ic_haut_hc"],
                         "ece": r["ece"], "ap": r["ap"], "n_train": r["n_train"]})
            pd.DataFrame(rows).to_csv(REPORTS / "echelle-walk-forward.csv", index=False)
            if fy == 2025:
                keep_2025[ladder] = r

    # ── Phase 2.2 · pondération des années récentes (JUSTIFIÉE par walk-forward) ──
    # candidates : sans (déjà mesuré) · demi-vie 5 ans · 3 ans. Sélection sur les folds de
    # VALIDATION 2022-2024 (moyenne rr_hc) ; 2025 reste le test rendu avec le choix.
    wrows = []
    fdf = frame_for(df, "v2")
    for hl in (5.0, 3.0):
        for fy in (2022, 2023, 2024, 2025):
            r = fit_fold(fdf, LADDERS["D_complet"]["specs"], fy, copro, weight_hl=hl)
            log(f"D+poids hl={hl} fold {fy} : rr_hc {r['rr_hc']:.2f}")
            wrows.append({"hl": hl, "fold": fy, "rr_hc": r["rr_hc"], "ece": r["ece"]})
            pd.DataFrame(wrows).to_csv(REPORTS / "ponderation.csv", index=False)
            if fy == 2025:
                keep_2025[f"D_poids_hl{hl:g}"] = r

    # ── Phase 3.4 · segments (fold 2025, modèle D sans pondération) ───────────────
    d25 = keep_2025["D_complet"]
    test, p, y, hc = d25["test"], d25["p"], d25["y"], d25["hc"]
    seg_rows = []
    thc, phc, yhc = test[hc], p[hc], y[hc]
    for seg_name, mask in [
        ("nu", (thc["nu"] == True).to_numpy()),           # noqa: E712 (pandas bool)
        ("bati", (thc["nu"] == False).to_numpy()),        # noqa: E712
        ("pm_connu", thc["owner_type"].eq("pm").to_numpy()),
        ("non_pm", ~thc["owner_type"].eq("pm").to_numpy()),
    ]:
        k_seg = max(1, int(round(K * mask.mean())))
        rr = ev.rr_at_k(yhc[mask], phc[mask], k_seg)
        seg_rows.append({"segment": seg_name, "n": int(mask.sum()),
                         "taux_base": rr["taux_global"], "k": k_seg,
                         "rr@k": rr["rr"], "positifs_topk": rr["positifs_topk"]})
        log(f"segment {seg_name}: n={mask.sum():,} rr@{k_seg}={rr['rr']:.2f}")
    pd.DataFrame(seg_rows).to_csv(REPORTS / "segments-2025.csv", index=False)

    # ── Phase 2.4 · ablation STATIQUES (fold 2025) — le point fuite ───────────────
    sans_stat = [s for s in LADDERS["D_complet"]["specs"] if s.name not in STATIQUES_PRUDENCE]
    r = fit_fold(fdf, sans_stat, 2025, copro)
    log(f"D SANS statiques fold 2025 : rr_hc {r['rr_hc']:.2f}")
    pd.DataFrame([{"variante": "D_complet", "rr_hc": d25["rr_hc"], "ece": d25["ece"]},
                  {"variante": "D_sans_statiques", "rr_hc": r["rr_hc"], "ece": r["ece"]}]
                 ).to_csv(REPORTS / "ablation-statiques.csv", index=False)
    keep_2025["D_sans_statiques"] = r

    # ── Phase 5 · challenger GBM (annexe — ne concourt pas) ───────────────────────
    grows = []
    for fy in FOLDS:
        names = [s.name for s in LADDERS["D_complet"]["specs"]]
        train = fdf[(fdf.annee >= 2017) & (fdf.annee <= fy - 2)].reset_index(drop=True)
        cal = fdf[fdf.annee == fy - 1].reset_index(drop=True)
        test_g = fdf[fdf.annee == fy].reset_index(drop=True)
        enc = WoeEncoder(min_count=200).fit(train, train["label"].astype(int),
                                            LADDERS["D_complet"]["specs"])
        Xtr, Xte = enc.transform(train), enc.transform(test_g)
        gbm = HistGradientBoostingClassifier(random_state=SEED, max_iter=300,
                                             learning_rate=0.08, max_leaf_nodes=31,
                                             validation_fraction=0.15)
        gbm.fit(Xtr.to_numpy(), train["label"].astype(int).to_numpy())
        pg = gbm.predict_proba(Xte.to_numpy())[:, 1]
        yg = test_g["label"].astype(int).to_numpy()
        hcg = ~test_g["idu"].map(copro).fillna(False).to_numpy()
        rr_hcg = ev.bootstrap_rr(yg[hcg], pg[hcg], K, n_boot=400 if fy < 2025 else 1000)
        eceg, _ = ev.ece(yg, pg)
        log(f"GBM fold {fy} : rr_hc {rr_hcg['rr']:.2f} · ECE {eceg:.4f}")
        grows.append({"fold": fy, "rr_hc": rr_hcg["rr"], "ic_bas": rr_hcg["ic95_bas"],
                      "ic_haut": rr_hcg["ic95_haut"], "ece": eceg,
                      "ap": float(average_precision_score(yg, pg))})
        pd.DataFrame(grows).to_csv(REPORTS / "gbm-challenger.csv", index=False)

    # ── artefacts + poids du modèle D (fold 2025) ────────────────────────────────
    joblib.dump(d25["model"], REPORTS / "artifact-m127-D-fold2025.joblib")
    d25["model"].model_card_rows().to_csv(REPORTS / "model-card-D-2025.csv", index=False)
    log("FIN examen — sorties dans reports/m127/")


if __name__ == "__main__":
    main()
