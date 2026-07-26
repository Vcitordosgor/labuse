#!/usr/bin/env python
"""ALGO-3 LOT B — challenger voisinage : corrélations (réserves Vic 1-2), walk-forward,
ablations par FAMILLE et par RAYON, RR par commune avec bilan complet (réserve 3).

Champion INTOUCHÉ (aucune écriture hors reports/algo3/). Anti-fuite PASS préalable
(qa/algo3_antifuite.py — exécuté avant, 36/36). Protocole = champion à l'identique.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from labuse.scoring.p_model import SEED, evaluate as ev
from labuse.scoring.p_model.features import FEATURES, FeatureSpec, derive
from labuse.scoring.p_model.model import PModel
from labuse.scoring.p_model.woe import WoeEncoder
from labuse.scoring.arene import paired_bootstrap_diff

DB = os.environ.get("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
OUT = os.path.join(os.path.dirname(__file__), "..", "reports", "algo3")
CH_CSV = "/Users/openclaw/Desktop/labuse/reports/m36-foncier/scores-2025-fold-final.csv"
GOLDEN = "/Users/openclaw/Desktop/labuse/reports/m6-audit/golden/golden-parcelles.json"
K, C_REG = 1158, 5.0
INTERACTIONS = [("tenure_bin", "permis_bin"), ("tenure_bin", "surface_m2"),
                ("ndvi_moyen", "zone_plu"), ("tenure_bin", "rot_nu"),
                ("surface_m2", "permis_bin")]
FOLDS = (2020, 2021, 2022, 2023, 2024, 2025)

S = lambda n, k="num": FeatureSpec(n, "V", k, 0, "voisinage algo3", "as-of", "as-of")  # noqa: E731
FAM = {
    "VENTES":  [S("ventes_50m_24m"), S("ventes_100m_24m"), S("ventes_200m_24m"),
                S("delai_derniere_vente_voisine")],
    "PERMIS":  [S("permis_100m_24m"), S("permis_200m_36m"), S("distance_permis_recent")],
    "MITOYEN": [S("voisin_direct_mute_36m", "bool"), S("nb_voisins_directs")],
    "ECART":   [S("ecart_rotation_local_secteur")],
}
RAYONS = {"V50": [S("ventes_50m_24m")], "V100": [S("ventes_100m_24m")], "V200": [S("ventes_200m_24m")]}
ALL_V = FAM["VENTES"] + FAM["PERMIS"] + FAM["MITOYEN"] + FAM["ECART"]


def fit_variant(df_tr, y_tr, df_cal, y_cal, extra):
    specs = list(FEATURES) + list(extra)
    m = PModel(feature_names=[s.name for s in specs])
    m.encoder = WoeEncoder(min_count=200).fit(df_tr, y_tr, specs)
    m.interactions = list(INTERACTIONS)
    m.year_dummies = sorted(df_tr["annee"].unique())[:-1]
    m.fit(df_tr, y_tr, C=C_REG)
    m.calibrate(df_cal, y_cal.astype(int))
    return m


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    eng = create_engine(DB)
    base = pd.read_sql(text("SELECT * FROM p_model_ext_dataset WHERE annee BETWEEN 2017 AND 2025"
                            " AND label IS NOT NULL"), eng)
    vois = pd.read_sql(text("SELECT * FROM algo3_voisinage WHERE annee BETWEEN 2017 AND 2025"), eng)
    cop = pd.read_sql(text("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro"), eng)
    df = derive(base).merge(vois, on=["idu", "annee"], how="left").merge(cop, on="idu", how="left")
    df["copro"] = df["copro"].fillna(False).astype(bool)
    df["voisin_direct_mute_36m"] = df["voisin_direct_mute_36m"].astype("boolean")
    y_all = df["label"].astype(int)

    # ── RÉSERVES VIC 1-2 : corrélations AVANT tout fit (fold 2025, hors copro) ──
    d25 = df[(df["annee"] == 2025) & (~df["copro"])]
    cols_v = ["ventes_50m_24m", "ventes_100m_24m", "ventes_200m_24m",
              "ecart_rotation_local_secteur", "permis_100m_24m"]
    cols_c = ["rot_nu", "rot_bati", "dens_bati_secteur", "pct_bati_secteur"]
    corr = d25[cols_v + cols_c].corr(method="spearman").loc[cols_v, cols_c].round(3)
    print("── CORRÉLATIONS (Spearman, fold 2025) — réserves 1-2 ──")
    print(corr.to_string(), flush=True)
    corr.to_csv(f"{OUT}/correlations-2025.csv")

    # ── walk-forward FULL ──
    res_folds, signes = [], {}
    for F in FOLDS:
        tr, cal = df[df["annee"] <= F - 2], df[df["annee"] == F - 1]
        te = df[(df["annee"] == F) & (~df["copro"])].reset_index(drop=True)
        m = fit_variant(tr, y_all.loc[tr.index], cal, y_all.loc[cal.index], ALL_V)
        p = m.predict_proba(te)
        rr = ev.bootstrap_rr(te["label"].astype(int).to_numpy(), p, K, n_boot=1000, seed=SEED)
        e, _ = ev.ece(te["label"].astype(int).to_numpy(), p)
        res_folds.append({"fold": F, "rr": rr["rr"], "lo": rr["ic95_bas"], "hi": rr["ic95_haut"], "ece": e})
        for k2, v in m.coefs.items():
            signes.setdefault(k2, []).append(np.sign(v) if abs(v) > 1e-6 else 0.0)
        print(f"FULL fold {F}: RR={rr['rr']:.2f} [{rr['ic95_bas']:.2f};{rr['ic95_haut']:.2f}] ECE={e:.4f}",
              flush=True)
        if F == 2025:
            te25, p_full = te, p

    # ── ablations fold 2025 (familles + rayons), appariées vs BASE ──
    tr, cal = df[df["annee"] <= 2023], df[df["annee"] == 2024]
    y25 = te25["label"].astype(int).to_numpy()
    variants = {"BASE": []} | {f"+{k}": v for k, v in FAM.items()} | \
               {f"+{k}": v for k, v in RAYONS.items()}
    scores = {"FULL": p_full}
    for name, extra in variants.items():
        mv = fit_variant(tr, y_all.loc[tr.index], cal, y_all.loc[cal.index], extra)
        scores[name] = mv.predict_proba(te25)
        print(f"{name}: fit ok", flush=True)
    abl = []
    for name in list(variants) + ["FULL"]:
        rr = ev.bootstrap_rr(y25, scores[name], K, n_boot=1000, seed=SEED)
        d = (paired_bootstrap_diff(y25, scores[name], scores["BASE"], K, n_boot=1000, seed=SEED)
             if name != "BASE" else {"diff_rr": 0, "ic95_bas": 0, "ic95_haut": 0, "significatif": False})
        abl.append({"variante": name, "rr": rr["rr"], "lo": rr["ic95_bas"], "hi": rr["ic95_haut"],
                    "d": d["diff_rr"], "d_lo": d["ic95_bas"], "d_hi": d["ic95_haut"],
                    "sig": bool(d.get("significatif"))})
        print(f"{name}: RR={rr['rr']:.2f} Δ={d['diff_rr']:+.2f} [{d['ic95_bas']:+.2f};{d['ic95_haut']:+.2f}]"
              f"{' SIG' if d.get('significatif') else ''}", flush=True)
    pd.DataFrame(abl).to_csv(f"{OUT}/ablations-2025.csv", index=False)
    pd.DataFrame(res_folds).to_csv(f"{OUT}/walk-forward.csv", index=False)

    # ── vs champion + communes (bilan COMPLET, réserve 3) ──
    ch = pd.read_csv(CH_CSV)
    p_ch = te25.merge(ch, on="idu", how="left")["p_l2f"].to_numpy(float)
    d_ch = paired_bootstrap_diff(y25, p_full, p_ch, K, n_boot=1000, seed=SEED)
    churn = ev.churn_topk(pd.Series(p_ch, index=te25["idu"]), pd.Series(p_full, index=te25["idu"]),
                          K, seed=SEED)
    perm = ev.permutation_control(y25, p_full, np.full(len(te25), 2025), K, seed=SEED)
    rows = []
    for com, g in te25.assign(pf=p_full, pc=p_ch).groupby("commune"):
        yc = g["label"].astype(int).to_numpy()
        k_c = max(5, int(round(K * len(g) / len(te25))))
        dc = paired_bootstrap_diff(yc, g["pf"].to_numpy(), g["pc"].to_numpy(), k_c,
                                   n_boot=500, seed=SEED)
        rows.append({"commune": com, "n": len(g), "k_c": k_c,
                     "rr_full": ev.rr_at_k(yc, g["pf"].to_numpy(), k_c, seed=SEED)["rr"],
                     "rr_champ": ev.rr_at_k(yc, g["pc"].to_numpy(), k_c, seed=SEED)["rr"],
                     "d": dc["diff_rr"], "d_lo": dc["ic95_bas"], "d_hi": dc["ic95_haut"],
                     "sig": bool(dc["significatif"])})
    cdf = pd.DataFrame(rows).sort_values("d", ascending=False)
    cdf.to_csv(f"{OUT}/rr-commune-2025.csv", index=False)
    print("── COMMUNES (Δ apparié, bilan complet) ──")
    print(cdf.to_string(index=False), flush=True)

    gold = json.load(open(GOLDEN, encoding="utf-8"))
    negs = [i for i, e2 in gold["parcelles"].items()
            if (e2.get("anchor") and e2.get("validation") == "factuelle")
            or (not e2.get("anchor") and ((e2.get("db", {}).get("score_v2") or {}).get("tier") == "ecartee"
                                          or e2.get("db", {}).get("etage0")))]
    top = set(te25.loc[ev._ranked_top_mask(p_full, K, np.random.RandomState(SEED)), "idu"])
    stab = {k2: (abs(sum(v)) == len(v)) for k2, v in signes.items()}
    json.dump({"delta_vs_champion": d_ch, "churn_pct": 1 - churn["overlap_pct"],
               "permutation_rr": perm["rr"], "boussole_proxy": sorted(set(negs) & top),
               "signes_stables": f"{sum(stab.values())}/{len(stab)}",
               "instables": [k2 for k2, o in stab.items() if not o]},
              open(f"{OUT}/synthese.json", "w"), indent=1, default=float)
    print(f"Δ FULL−CHAMPION: {d_ch['diff_rr']:+.2f} [{d_ch['ic95_bas']:+.2f};{d_ch['ic95_haut']:+.2f}] "
          f"sig={d_ch['significatif']} · churn {1 - churn['overlap_pct']:.0%} · perm {perm['rr']:.2f}",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
