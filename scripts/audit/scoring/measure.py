"""SCORING-1 (audit, lecture seule) — toutes les mesures numériques du rapport.

Sous-commandes :
  coverage      B.1 — couverture réelle de chaque feature (année scorée)
  importance    B.2 — importance par permutation (AUC + RR@top) sur validation
  correl        B.3 — corrélations entre features
  calibration   C.1 — calibration par décile (servi iso-2025 ET fold out-of-sample)
  commune       C.2 — lift du décile sup par commune
  bytype        C.3 — calibration par type (terrain/bâti × zone)
  paliers       C.4 + D.2 + D.4 — taux de vente réel, effectifs, lift par palier
  stability     C.5 + H.2 — q_v10 → q_v11, mouvements de palier

Tout sort en CSV dans reports/audit-scoring/. Aucune écriture en base.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (engine, load_model, load_year, recalibrated_model,  # noqa: E402
                     SERVED_RUN, ROOT)
from labuse.scoring.p_model.features import FEATURES  # noqa: E402

OUT = ROOT / "reports/audit-scoring"
OUT.mkdir(parents=True, exist_ok=True)
LIB = {f.name: f for f in FEATURES}
RETIRED = {f.name for f in FEATURES if f.retired}

# ---- univers servi : hors copro (le ranking produit) --------------------------------
def copro_mask(eng, df) -> np.ndarray:
    c = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro", eng)
    m = df[["idu"]].merge(c, on="idu", how="left")["copro"].fillna(False).to_numpy()
    return m.astype(bool)


def rr_at(y, p, k=1158) -> float:
    """Rendement relatif : taux dans le top-k / taux de base."""
    n = len(y)
    base = y.mean()
    idx = np.argsort(-p)[:k]
    return float(y[idx].mean() / base) if base > 0 else float("nan")


# ============================================================ B.1
def coverage():
    eng = engine()
    annee = 2026
    df = pd.read_sql(f"SELECT * FROM p_model_ext_dataset WHERE annee={annee}", eng)
    n = len(df)
    rows = []
    for f in FEATURES:
        col = f.name
        # feature dérivée : présente après derive(), pas dans la table brute
        raw = None
        if col in df.columns:
            raw = df[col]
        elif col == "rot_nu":
            raw = df["rot_nu_brute"]
        elif col == "rot_bati":
            raw = df["rot_bati_brute"]
        elif col == "dormance_droits":
            raw = df["pct_potentiel"]
        elif col == "acces_equipements":
            raw = df[["dist_ecole_m", "dist_sante_m", "dist_commerce_m", "dist_tcsp_m"]].notna().any(axis=1)
        if raw is None:
            rows.append((col, f.bloc, f.kind, "COLONNE ABSENTE", None, None, col in RETIRED))
            continue
        nn = int(raw.notna().sum())
        # "informative" : non-null ET non-défaut (bool True, cat != inconnu, num != 0 pour comptages)
        if f.kind == "bool":
            info = int(pd.Series(raw).fillna(False).astype(bool).sum())
        elif f.kind == "cat":
            vals = pd.Series(raw).astype(str)
            info = int((~vals.isin(["inconnu", "jamais", "None", "nan", ""])).sum())
        else:
            info = nn
        rows.append((col, f.bloc, f.kind, round(100*nn/n, 2), round(100*info/n, 2),
                     f.source[:60], col in RETIRED))
    out = pd.DataFrame(rows, columns=["feature", "bloc", "kind", "pct_non_null",
                                      "pct_informatif", "source", "retired"])
    out.to_csv(OUT / "b1_coverage.csv", index=False)
    print(out.to_string(index=False))
    print(f"\nN parcelles = {n}")


# ============================================================ B.2
def importance():
    eng = engine()
    # OUT-OF-SAMPLE : modèle fold2025 (jamais vu 2025) prédit 2025.
    import joblib
    fold = joblib.load(ROOT / "reports/m36-foncier/artifacts-m36-fold2025.joblib")
    df = load_year(eng, 2025)
    y = df["label"].astype(int).to_numpy()
    hors = ~copro_mask(eng, df)
    dfh, yh = df[hors].reset_index(drop=True), y[hors]
    p0 = fold.predict_proba(dfh)
    auc0, ap0, rr0 = roc_auc_score(yh, p0), average_precision_score(yh, p0), rr_at(yh, p0)
    rng = np.random.RandomState(974)
    rows = []
    # colonnes réellement encodées (features du modèle)
    feats = [f.name for f in FEATURES]
    for col in feats:
        # colonne source à permuter dans dfh (avant re-derive si dérivée)
        drops_auc, drops_rr = [], []
        for _ in range(3):
            d2 = dfh.copy()
            if col in d2.columns:
                d2[col] = rng.permutation(d2[col].to_numpy())
            else:
                continue
            p = fold.predict_proba(d2)
            drops_auc.append(auc0 - roc_auc_score(yh, p))
            drops_rr.append(rr0 - rr_at(yh, p))
        rows.append((col, LIB[col].bloc, round(np.mean(drops_auc), 5) if drops_auc else None,
                     round(np.mean(drops_rr), 3) if drops_rr else None, col in RETIRED))
    out = pd.DataFrame(rows, columns=["feature", "bloc", "delta_auc", "delta_rr1158", "retired"])
    out = out.sort_values("delta_auc", ascending=False)
    out.to_csv(OUT / "b2_importance.csv", index=False)
    print(f"BASELINE fold2025 sur 2025 hors copro : AUC={auc0:.4f} AP={ap0:.4f} "
          f"RR@1158={rr0:.2f}  (n={len(yh)}, ventes={yh.sum()})")
    print(out.to_string(index=False))


# ============================================================ B.3
def correl():
    eng = engine()
    df = load_year(eng, 2025)
    num = [f.name for f in FEATURES if f.kind == "num" and f.name in df.columns]
    corr = df[num].apply(pd.to_numeric, errors="coerce").corr(method="spearman")
    corr.to_csv(OUT / "b3_correl.csv")
    # paires |rho|>0.5
    pairs = []
    for i in range(len(num)):
        for j in range(i+1, len(num)):
            r = corr.iloc[i, j]
            if abs(r) > 0.5:
                pairs.append((num[i], num[j], round(r, 3)))
    print("Paires de features corrélées |rho|>0.5 (Spearman, 2025) :")
    for a, b, r in sorted(pairs, key=lambda x: -abs(x[2])):
        print(f"  {a:24s} ~ {b:24s} : {r}")


# ============================================================ C.1
def calibration():
    eng = engine()
    res = {}
    # (a) SERVI : modèle servi (iso calibré sur 2025) prédit 2025 — IN-SAMPLE pour l'iso.
    m, last = recalibrated_model(eng)
    df = load_year(eng, last)
    y = df["label"].astype(int).to_numpy()
    hors = ~copro_mask(eng, df)
    for tag, model in [("servi_iso2025_insample", m)]:
        p = model.predict_proba(df)[hors]
        yy = y[hors]
        _decile_table(p, yy, OUT / f"c1_calibration_{tag}.csv", tag)
    # (b) OUT-OF-SAMPLE : fold2025 (jamais vu 2025) prédit 2025.
    import joblib
    fold = joblib.load(ROOT / "reports/m36-foncier/artifacts-m36-fold2025.joblib")
    p = fold.predict_proba(df)[hors]
    _decile_table(p, y[hors], OUT / "c1_calibration_fold2025_oos.csv", "fold2025_oos")


def _decile_table(p, y, path, tag):
    q = pd.qcut(pd.Series(p).rank(method="first"), 10, labels=False)
    t = pd.DataFrame({"p": p, "y": y, "d": q})
    agg = t.groupby("d").agg(n=("y", "size"), p_moyen=("p", "mean"),
                             taux_obs=("y", "mean"), ventes=("y", "sum"))
    agg["ecart"] = agg["p_moyen"] - agg["taux_obs"]
    agg["lift"] = agg["taux_obs"] / y.mean()
    agg.to_csv(path)
    ece = float((agg["n"] * (agg["p_moyen"] - agg["taux_obs"]).abs()).sum() / agg["n"].sum())
    print(f"\n== C.1 {tag} (hors copro, n={len(y)}, taux base={y.mean():.4f}, "
          f"AUC={roc_auc_score(y,p):.4f}, ECE={ece:.5f}) ==")
    print(agg.round(5).to_string())


# ============================================================ C.2
def commune():
    eng = engine()
    m, last = recalibrated_model(eng)
    df = load_year(eng, last)
    y = df["label"].astype(int).to_numpy()
    p = m.predict_proba(df)
    hors = ~copro_mask(eng, df)
    d = pd.DataFrame({"commune": df["commune"], "p": p, "y": y})[hors]
    rows = []
    for com, g in d.groupby("commune"):
        if len(g) < 50:
            continue
        thr = g["p"].quantile(0.9)
        top = g[g["p"] >= thr]
        base = g["y"].mean()
        rows.append((com, len(g), int(g["y"].sum()), round(base, 4),
                     round(top["y"].mean(), 4) if len(top) else None,
                     round(top["y"].mean()/base, 2) if base > 0 and len(top) else None,
                     int(g["y"].sum())))
    out = pd.DataFrame(rows, columns=["commune", "n", "ventes", "taux_base",
                                      "taux_top10pct", "lift_top10", "n_ventes"])
    out = out.sort_values("n", ascending=False)
    out.to_csv(OUT / "c2_commune.csv", index=False)
    print(out.to_string(index=False))


# ============================================================ C.3
def bytype():
    eng = engine()
    m, last = recalibrated_model(eng)
    df = load_year(eng, last)
    y = df["label"].astype(int).to_numpy()
    p = m.predict_proba(df)
    hors = ~copro_mask(eng, df)
    df2 = df[hors].copy()
    df2["p"], df2["y"] = p[hors], y[hors]
    df2["type_bati"] = np.where(df2["nu"].fillna(False), "terrain_nu", "bati")
    df2["zone"] = df2["zone_plu"].fillna("inconnu")
    rows = []
    for (tb, z), g in df2.groupby(["type_bati", "zone"]):
        if len(g) < 100:
            continue
        base = g["y"].mean()
        thr = g["p"].quantile(0.9)
        top = g[g["p"] >= thr]
        rows.append((tb, z, len(g), int(g["y"].sum()), round(base, 4),
                     round(roc_auc_score(g["y"], g["p"]), 3) if g["y"].nunique() > 1 else None,
                     round(top["y"].mean()/base, 2) if base > 0 and len(top) else None))
    out = pd.DataFrame(rows, columns=["type", "zone", "n", "ventes", "taux_base", "auc", "lift_top10"])
    out = out.sort_values("n", ascending=False)
    out.to_csv(OUT / "c3_bytype.csv", index=False)
    print(out.to_string(index=False))


# ============================================================ C.4 + D.2 + D.4
def paliers():
    """Taux de vente réel par palier AFFICHÉ.
    Backtest honnête : on reconstruit les tiers avec la p de l'année N-1 (features
    as-of 01/01/2025, prédiction de la fenêtre 2025) mais les GATES statiques du
    produit (étage0, déclassements, SDP, copro) sont ceux servis — ils sont
    quasi-statiques (millésime unique 2026). On mesure ensuite le label 2025.
    """
    from labuse.scoring.p_v2.statuts import assign_tiers, calibre_brulante, calibre_n_entree, TierParams, plancher_c
    from labuse.scoring.tiers_client import court
    eng = engine()
    m, last = recalibrated_model(eng)
    df = load_year(eng, last)               # 2025 features + label 2025
    y = df["label"].astype(int).to_numpy()
    p = m.predict_proba(df)
    contrib = m.contributions(df)
    df["copro"] = copro_mask(eng, df)
    # gates statiques servis (mêmes lectures que le pipeline)
    _attach_gates(eng, df)
    # rangs hors copro
    hors = ~df["copro"].to_numpy()
    order = np.argsort(-p[hors])
    rang = np.full(len(df), np.nan)
    rh = np.empty(hors.sum()); rh[order] = np.arange(1, hors.sum()+1)
    rang[hors] = rh
    work = df.assign(rang=rang, p=p, contrib_d=contrib["contrib_D"].to_numpy(),
                     event_age_mois=np.nan)
    base_params = TierParams(n_entree=1, n_sortie=1)
    elig = work[~work["copro"] & ~work["ecartee_etage0"] & plancher_c(work, base_params)]
    n_e = calibre_n_entree(elig["rang"], cible=1150)
    params = TierParams(n_entree=n_e, n_sortie=int(round(1.4*n_e)))
    tier = assign_tiers(work, params, None)
    chaudes = work[tier.isin(["chaude", "brulante"])]
    params = calibre_brulante(chaudes, params)
    tier = assign_tiers(work, params, None)
    work["tier"] = tier.values
    work["y"] = y
    work["palier"] = work["tier"].map(lambda t: court(t) or t)
    base = y.mean()
    agg = work.groupby("palier").agg(
        n=("y", "size"), ventes=("y", "sum"), taux_obs=("y", "mean"),
        p_median=("p", "median")).reset_index()
    agg["lift"] = (agg["taux_obs"]/base).round(2)
    agg["taux_obs"] = agg["taux_obs"].round(4)
    agg["p_median"] = agg["p_median"].round(5)
    agg = agg.sort_values("taux_obs", ascending=False)
    agg.to_csv(OUT / "c4_paliers_backtest.csv", index=False)
    print(f"Backtest palier reconstruit sur {last} (p as-of, gates statiques servis). "
          f"taux base hors copro={base:.4f}, n_entree={n_e}")
    print(agg.to_string(index=False))
    # composition terrain/bâti par palier (D.2)
    work["type"] = np.where(work["nu"].fillna(False), "nu", "bati")
    comp = work.groupby(["palier", "type"]).size().unstack(fill_value=0)
    comp.to_csv(OUT / "d2_composition_paliers.csv")
    print("\nComposition nu/bati par palier :")
    print(comp.to_string())


def _attach_gates(eng, df):
    from sqlalchemy import text
    def has(t):
        with eng.connect() as c:
            return c.execute(text(f"SELECT to_regclass('{t}') IS NOT NULL")).scalar()
    # étage0 servi
    e0 = pd.read_sql(f"""SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
                         WHERE d.run_label='{SERVED_RUN}' AND d.status IN ('exclue','faux_positif_probable')""", eng)
    df["ecartee_etage0"] = df["idu"].isin(set(e0["idu"]))
    # constructibilité
    df["declasse_cause"] = None
    if has("parcel_constructibilite"):
        dcl = pd.read_sql("SELECT pp.idu, c.label AS dl FROM parcel_constructibilite c JOIN parcels pp ON pp.id=c.parcel_id", eng)
        df.drop(columns=[c for c in ["dl"] if c in df.columns], inplace=True, errors="ignore")
        df_m = df.merge(dcl, on="idu", how="left")
        df["declasse_cause"] = df_m["dl"].values
    df["au_statut"] = None
    if has("parcel_au_statut"):
        au = pd.read_sql("SELECT ap.idu, a.classe AS cl FROM parcel_au_statut a JOIN parcels ap ON ap.id=a.parcel_id", eng)
        df["au_statut"] = df.merge(au, on="idu", how="left")["cl"].values
    df["bati_revele"] = False
    if has("parcel_bati_revele"):
        br = pd.read_sql("SELECT idu, true AS b FROM parcel_bati_revele WHERE bande='regle'", eng)
        df["bati_revele"] = df.merge(br, on="idu", how="left")["b"].fillna(False).values
    df["bati_sature"] = False
    if has("parcel_filtre_bati"):
        fb = pd.read_sql("""SELECT f.idu, true AS b FROM parcel_filtre_bati f WHERE f.decision='saturee'
            AND NOT EXISTS (SELECT 1 FROM parcels p JOIN parcel_residuel r ON r.parcel_id=p.id
                            WHERE p.idu=f.idu AND r.cause IS NULL AND r.sdp_residuelle_m2>0)""", eng)
        df["bati_sature"] = df.merge(fb, on="idu", how="left")["b"].fillna(False).values
    df["dans_pau"] = False


# ============================================================ C.5 + H.2
def stability():
    eng = engine()
    a = pd.read_sql(f"SELECT parcelle_id idu, tier t_new FROM parcel_p_score_v2 WHERE run_id='{SERVED_RUN}'", eng)
    b = pd.read_sql("SELECT parcelle_id idu, tier t_old FROM parcel_p_score_v2 WHERE run_id='q_v10_m129'", eng)
    from labuse.scoring.tiers_client import court
    j = a.merge(b, on="idu")
    j["p_new"] = j["t_new"].map(lambda t: court(t) or t)
    j["p_old"] = j["t_old"].map(lambda t: court(t) or t)
    n = len(j)
    changed = (j["p_new"] != j["p_old"]).sum()
    print(f"q_v10_m129 → q_v11_m137 : {n} parcelles, {changed} changent de palier "
          f"({100*changed/n:.2f}%)")
    mat = pd.crosstab(j["p_old"], j["p_new"])
    mat.to_csv(OUT / "hd_stability_matrix.csv")
    print("\nMatrice de transition (palier ancien → nouveau) :")
    print(mat.to_string())
    # tier interne aussi
    matt = pd.crosstab(j["t_old"], j["t_new"])
    matt.to_csv(OUT / "hd_stability_matrix_tier.csv")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    fns = {"coverage": coverage, "importance": importance, "correl": correl,
           "calibration": calibration, "commune": commune, "bytype": bytype,
           "paliers": paliers, "stability": stability}
    if cmd == "all":
        for k, fn in fns.items():
            print(f"\n{'='*70}\n{k.upper()}\n{'='*70}")
            fn()
    else:
        fns[cmd]()
