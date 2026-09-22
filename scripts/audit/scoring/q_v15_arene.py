"""SCORING-7 §2 — l'arène du candidat q_v15 : recette q_v14 MOINS piscine/pv_candidat.

Recette = `labuse.scoring.p_v2.qv15` (SOURCE UNIQUE, le pipeline réel score avec ce code).
Banc K0 identique à q_v14 (train ≤ 2023 · isotonique par segment 2024 · test AVEUGLE 2025 ;
horizon 24 mois : train ≤2022, cal 2023, test 2024). Le modèle est GELÉ (sha256 au manifeste),
le pipeline le LIT. `q_v11_m137` reste servi ; AUCUN run île ici, AUCUN promote.

Sous-commandes :
  cache — construit le dataset enrichi 2017-2026 (identique à q_v14 : mêmes features as-of ;
          q_v15 n'en RETIRE que 2 → on réutilise le cache q_v14 s'il existe).
  fit   — test de fuite, garde-fou ECE PM, fit 12+24 mois, métriques K0 (dont Brier,
          prec@100/500/1000/2000, mutations captées, précision par niveau), GEL des artefacts.

Doctrine : rien de servi ne change ; la bascule est un geste de Vic.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidats  # noqa: E402
import protocole  # noqa: E402
import q_v14_arene as arene14  # noqa: E402 — réutilise test_fuite / _q_v12_baseline_ece
from _common import ROOT, SERVED_RUN, engine  # noqa: E402
from labuse.scoring.p_v2 import qv12, qv15  # noqa: E402

QDIR = ROOT / "reports/q-v15"
QDIR.mkdir(parents=True, exist_ok=True)
QDIR14 = ROOT / "reports/q-v14"
YEARS = tuple(range(2017, 2027))
CACHE = ROOT / "reports/score-v2-arene/cache"
ENRICHI = QDIR / "enrichi_2017_2026.pkl"
ENRICHI14 = QDIR14 / "enrichi_2017_2026.pkl"
ECE_TOLERANCE = 0.01
NIVEAU_SEUILS = {"fort": 0.20, "moyen": 0.10}   # PALIERS-1 (signal_mutation) : fort ≥0,20, moyen ≥0,10


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def _charger_enrichi(eng, force=False):
    """Dataset enrichi (q_v14 = q_v15 côté enrichissement). Réutilise le cache q_v14 si présent."""
    if ENRICHI.exists() and not force:
        return pd.read_pickle(ENRICHI)
    if ENRICHI14.exists() and not force:
        log(f"réutilisation du cache q_v14 {ENRICHI14.name} (enrichissement identique)…")
        return pd.read_pickle(ENRICHI14)
    log("chargement 2017-2026 + enrichissement recette q_v14/q_v15…")
    df = qv15.enrichir(eng, protocole.load_range(eng, YEARS), YEARS, cache_dir=CACHE)
    df.to_pickle(ENRICHI)
    log(f"cache écrit : {ENRICHI} ({len(df)} lignes)")
    return df


def cache():
    _charger_enrichi(engine(), force=True)


def _mesurer(eng, df, seg_all, avec_ventes_pm, tag):
    names, specs, inter = qv15.features_qv15(avec_ventes_pm=avec_ventes_pm)
    m12 = qv15.fit_qv15(df, seg_all, names, specs, inter)
    ctx = protocole.Contexte(eng, df[df.annee == protocole.TEST_YEAR],
                             df[df.annee == protocole.SCORE_YEAR])
    seg_test = seg_all[(df.annee == protocole.TEST_YEAR).to_numpy()].reset_index(drop=True)
    seg_26 = seg_all[(df.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    p = m12.predict_proba(ctx.test, seg_test)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    cd = m12.contributions(ctx.test)[[c for c in d_feats if c in m12.base.coefs]].sum(axis=1).to_numpy()
    p26 = m12.predict_proba(ctx.score26, seg_26)
    row = protocole.metriques(ctx, tag, p, cd, p26)
    return row, m12, names, specs, inter, ctx, p, seg_test


def _metriques_extra(y, p, seg=None):
    """Métriques SUPPLÉMENTAIRES du mandat §2 (sur le test 2025, hors copro déjà filtré) :
    Brier, precision@K (100/500/1000/2000), part des mutations captées (recall@K), et
    précision + rappel par niveau de Signal fort/moyen/faible (seuils absolus PALIERS-1)."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    npos = float(y.sum())
    order = np.argsort(-p)
    out = {"brier": float(np.mean((p - y) ** 2)), "n": int(len(y)), "n_positifs": int(npos)}
    for K in (100, 500, 1000, 2000):
        k = min(K, len(y))
        top = order[:k]
        out[f"prec@{K}"] = float(y[top].mean())
        out[f"mutations_captees@{K}"] = float(y[top].sum() / npos) if npos else float("nan")
    for niv, lo in (("fort", NIVEAU_SEUILS["fort"]), ("moyen", NIVEAU_SEUILS["moyen"]),
                    ("faible", 0.0)):
        hi = 1.01 if niv == "fort" else (NIVEAU_SEUILS["fort"] if niv == "moyen" else NIVEAU_SEUILS["moyen"])
        m = (p >= lo) & (p < hi)
        out[f"n_{niv}"] = int(m.sum())
        out[f"prec_{niv}"] = float(y[m].mean()) if m.any() else float("nan")
        out[f"rappel_{niv}"] = float(y[m].sum() / npos) if npos else float("nan")
    return out


def fit():
    eng = engine()
    log("[q_v15] test de fuite (voisinage q_v12 + as-of)…")
    fuite = arene14.test_fuite(eng)
    assert not fuite["fuite_detectee"], "FUITE détectée"
    df = _charger_enrichi(eng)
    copro = qv15.copro_de(eng, df)
    seg_all = qv15.segmenter(df, copro)

    base_ece = arene14._q_v12_baseline_ece()
    log("[q_v15] mesure AVEC ventes_pm (test 2025)…")
    row_avec, m_avec, na, sa, ia, ctx_a, p_a, segtest_a = _mesurer(eng, df, seg_all, True, "q_v15_avec_ventespm")
    protocole.enregistrer(row_avec)
    d_ece_pm = row_avec["ece_personne_morale"] - base_ece["personne_morale"]
    log(f"[q_v15] ΔECE PM = {d_ece_pm:+.4f} (seuil {ECE_TOLERANCE})")
    if d_ece_pm > ECE_TOLERANCE:
        log("[q_v15] garde-fou → ventes_pm SORT")
        avec = False
        row_q, m12, names, specs, inter, ctx, p12, seg_test = _mesurer(eng, df, seg_all, False, "q_v15")
    else:
        log("[q_v15] garde-fou OK → ventes_pm reste")
        avec = True
        row_q, m12, names, specs, inter, ctx, p12, seg_test = row_avec, m_avec, na, sa, ia, ctx_a, p_a, segtest_a
        row_q = dict(row_q)
    row_q["candidat"] = "q_v15"
    degrade = {s: round(row_q[f"ece_{s}"] - base_ece[s], 4) for s in qv12.SEGMENTS
               if row_q[f"ece_{s}"] - base_ece[s] > ECE_TOLERANCE}
    protocole.enregistrer(row_q)

    # métriques extra sur le test 2025 (hors copro, comme protocole) — pour q_v15 ET q_v14 refit
    m = ctx.eval_mask
    hors = (~ctx.copro[m]).to_numpy() if hasattr(ctx.copro[m], "to_numpy") else ~np.asarray(ctx.copro)[m]
    y_h = ctx.y[m][hors]
    extra15 = _metriques_extra(y_h, p12[m][hors])
    log("[q_v15] refit q_v14 sur le MÊME banc pour comparer les métriques extra…")
    from labuse.scoring.p_v2 import qv14
    n14, s14, i14 = qv14.features_qv14(avec_ventes_pm=avec)
    m14 = qv14.fit_qv14(df, seg_all, n14, s14, i14)
    p14 = m14.predict_proba(ctx.test, seg_test)
    extra14 = _metriques_extra(y_h, p14[m][hors])
    pd.DataFrame([{"candidat": "q_v15", **extra15}, {"candidat": "q_v14", **extra14}]).to_csv(
        QDIR / "k0_metriques_extra.csv", index=False)

    log("[q_v15] fit 24 mois (≤2022, cal 2023, test 2024)…")
    df24 = candidats.appliquer_label24(df.copy(), candidats.charger_label24(eng))
    m24 = qv15.fit_qv15(df24, seg_all, names, specs, inter, label_col="label_24m",
                        train_max=qv15.TRAIN_MAX_24M, cal_year=qv15.CAL_YEAR_24M)
    ctx24 = protocole.Contexte(eng, df24[df24.annee == 2024], df24[df24.annee == protocole.SCORE_YEAR],
                               label_col="label_24m", annee_test=2024, horizon_mois=24)
    seg24 = seg_all[(df24.annee == 2024).to_numpy()].reset_index(drop=True)
    seg26 = seg_all[(df24.annee == protocole.SCORE_YEAR).to_numpy()].reset_index(drop=True)
    d_feats = [s.name for s in specs if s.bloc == "D"]
    p_t24 = m24.predict_proba(ctx24.test, seg24)
    cd24 = m24.contributions(ctx24.test)[[c for c in d_feats if c in m24.base.coefs]].sum(axis=1).to_numpy()
    row_24 = protocole.metriques(ctx24, "q_v15_24m_test2024", p_t24, cd24,
                                 m24.predict_proba(ctx24.score26, seg26))
    table = protocole.enregistrer(row_24)

    log("[q_v15] gel des artefacts…")
    df26 = df[df.annee == protocole.SCORE_YEAR]
    couv = [{"feature": n, "pct_non_null": round(100 * float(df26[n].notna().mean()), 2)
             if n in df26.columns else None} for n in names]
    manifeste = {
        "candidat": qv15.QV15_VERSION,
        "gel": time.strftime("%Y-%m-%d %H:%M:%S"),
        "doctrine": f"calculé par le pipeline réel, jamais basculé — {SERVED_RUN} reste servi",
        "recette": "q_v14 MOINS piscine/pv_candidat (aucune variable nouvelle)",
        "retirees_vs_q_v14": list(qv15.RETIREES_QV15),
        "ventes_pm_secteur_36m_retenue": avec,
        "garde_fou_ece": {"seuil": ECE_TOLERANCE, "ece_pm_q_v12": base_ece["personne_morale"],
                          "ece_pm_avec_ventespm": row_avec["ece_personne_morale"],
                          "delta_ece_pm_avec_ventespm": round(d_ece_pm, 4),
                          "segments_degrades_final": degrade},
        "protocole_12m": {"train": f"{qv15.TRAIN_MIN}-{qv15.TRAIN_MAX}", "calibration": qv15.CAL_YEAR,
                          "test": protocole.TEST_YEAR},
        "protocole_24m": {"train": f"{qv15.TRAIN_MIN}-{qv15.TRAIN_MAX_24M}", "calibration": qv15.CAL_YEAR_24M,
                          "test": 2024},
        "segments": {s: int((seg_all == s).sum()) for s in qv15.SEGMENTS},
        "n_features": len(names), "features": names, "interactions": inter,
        "features_couverture_2026": couv,
        "test_fuite": fuite,
        "metriques_k0_2025": {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in row_q.items()},
        "metriques_extra_k0_2025": {"q_v15": extra15, "q_v14_refit": extra14},
        "metriques_24m_test2024": {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in row_24.items()},
    }
    manifeste = qv15.geler_artifacts(m12, m24, manifeste)
    # round-trip
    m12b, _, _ = qv15.verify_artifacts()
    ech = ctx.test.sample(n=min(2000, len(ctx.test)), random_state=974)
    seg_ech = seg_test.loc[ech.index]
    assert np.allclose(m12b.predict_proba(ech, seg_ech), m12.predict_proba(ech, seg_ech)), "round-trip KO"
    log(f"[q_v15] gelé {manifeste['sha256_12m'][:16]}… / {manifeste['sha256_24m'][:16]}…")
    print(table[table.candidat.isin(["ligne_de_base", "q_v12", "q_v14", "q_v15"])].to_string(index=False))
    print("\nEXTRA:", json.dumps({"q_v15": extra15, "q_v14_refit": extra14}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fit"
    {"cache": cache, "fit": fit}[cmd]()
