"""M132 — L'EXAMEN À HAUTE PUISSANCE : l'écart pairé actuel vs C_bati agrégé sur 3 folds.

Contexte : M131 — le gain bâti de C_bati pointe pour la 3e fois (+11 %/+9,6 %/+8 %) mais
l'IC franchit 0 à un seul fold (~15 mutations sur 959 têtes). La voie : PLUS DE PUISSANCE,
pas un autre modèle. On agrège l'écart pairé sur les folds 2023, 2024, 2025 (≈3× les
mutations), IC resserré, verdict mécanique sous la double barre v2.

RIEN ne change : ni la métrique (top 0,4 % par segment, gravée), ni les modèles, ni le run
servi. On ajoute des données à la MESURE. Le VIVIER est un instantané unique de la cascade
(exclusions physiques/légales, ~invariantes) : tenu FIXE (q_v10_m129) sur les 3 folds, seuls
l'année de label + la fenêtre d'entraînement (walk-forward) changent — ça isole la puissance
ajoutée de toute dérive d'univers.

Deux agrégations, DITES :
  • POOLING des paires (primaire) : micro-moyenne des RR sur les 3 folds (pool des événements),
    bootstrap pairé unique — chaque tirage rééchantillonne les 3 folds, top-k par fold, RR poolé.
  • MÉTA-ANALYSE des folds (contrôle) : Δ par fold + variance (bootstrap pairé M131), pool
    inverse-variance (effet fixe). Si les deux divergent sur le verdict, les deux sont donnés.

Mesure seule. Cache par fold (reports/m132/preds_<fy>.npz ; 2025 réutilise reports/m131).
Usage : PYTHONPATH=src python scripts/m132/examen_hp.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, "scripts/m127")
from examen import KEPT, fit_fold  # protocole M127/M130/M131 réutilisé tel quel  # noqa: E402
sys.path.insert(0, "scripts/m127bis")
from examen_bis import BATI_SPECS, CAUSE_SPEC, frame_for, load_v2bis  # noqa: E402

from labuse.db import engine  # noqa: E402
from labuse.scoring.p_model.evaluate import _ranked_top_mask  # noqa: E402

REPORTS = Path("reports/m132")
SERVED_RUN = "q_v10_m129"
TOP_PCT = 0.004
FOLDS = (2023, 2024, 2025)
SEED = 974
N_BOOT = 2000

LADDERS = {
    "actuel": {"specs": KEPT, "residuel": "v1"},
    "C_bati": {"specs": KEPT + [CAUSE_SPEC] + BATI_SPECS, "residuel": "v2"},
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def rr_point(y, p, k, rng):
    base = y.mean()
    if base <= 0:
        return np.nan
    return y[_ranked_top_mask(p, k, rng)].mean() / base


def rr_median(y, p, k, seeds=range(1, 21)):
    return float(np.median([rr_point(y, p, k, np.random.RandomState(s)) for s in seeds]))


def paired_delta_ic(y, pa, pb, k, n_boot=N_BOOT):
    """IC95 + variance de l'écart pairé RR(C_bati) − RR(actuel) sur UN fold (M131)."""
    rng = np.random.RandomState(SEED)
    n = len(y)
    deltas = []
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        yb, pab, pbb = y[idx], pa[idx], pb[idx]
        base = yb.mean()
        if base <= 0:
            continue
        deltas.append(yb[_ranked_top_mask(pbb, k, rng)].mean() / base
                      - yb[_ranked_top_mask(pab, k, rng)].mean() / base)
    deltas = np.array(deltas)
    return float(np.median(deltas)), float(np.percentile(deltas, 2.5)), \
        float(np.percentile(deltas, 97.5)), float(np.var(deltas, ddof=1))


def pooled_delta_ic(folds_seg, n_boot=N_BOOT):
    """POOLING des paires : micro-moyenne des RR sur les folds (pool des événements), bootstrap
    pairé unique. `folds_seg` = liste de (y, pa, pb, k) par fold, déjà restreints au segment."""
    rng = np.random.RandomState(SEED)

    def pooled_rr(resample: bool):
        na = nb = kk = pos = nn = 0.0
        for y, pa, pb, k in folds_seg:
            if resample:
                idx = rng.randint(0, len(y), len(y))
                y2, pa2, pb2 = y[idx], pa[idx], pb[idx]
            else:
                y2, pa2, pb2 = y, pa, pb
            na += y2[_ranked_top_mask(pa2, k, rng)].sum()
            nb += y2[_ranked_top_mask(pb2, k, rng)].sum()
            kk += k
            pos += y2.sum()
            nn += len(y2)
        base = pos / nn
        return (na / kk) / base, (nb / kk) / base

    ra, rb = pooled_rr(False)
    deltas = []
    for _ in range(n_boot):
        a, b = pooled_rr(True)
        deltas.append(b - a)
    deltas = np.array(deltas)
    return {"rr_actuel": ra, "rr_C_bati": rb, "delta": rb - ra,
            "delta_median": float(np.median(deltas)),
            "ic_bas": float(np.percentile(deltas, 2.5)),
            "ic_haut": float(np.percentile(deltas, 97.5))}


def meta_pool(per_fold):
    """MÉTA-ANALYSE effet fixe : pool inverse-variance des Δ par fold."""
    d = np.array([f["delta_median"] for f in per_fold])
    v = np.array([f["var"] for f in per_fold])
    w = 1.0 / v
    dm = float((w * d).sum() / w.sum())
    se = float(np.sqrt(1.0 / w.sum()))
    return {"delta": dm, "ic_bas": dm - 1.96 * se, "ic_haut": dm + 1.96 * se}


def fit_or_load(fy, vivier_idus, copro, df_cache):
    cache = (Path("reports/m131/preds.npz") if fy == 2025 else REPORTS / f"preds_{fy}.npz")
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        log(f"fold {fy} : prédictions rechargées ({cache})")
        return {k: z[k] for k in z.files}
    df = df_cache[0]
    if df is None:
        log("chargement dataset v2bis…")
        df = load_v2bis()
        df_cache[0] = df
        log(f"{len(df):,} lignes")
    preds, idu_ref = {}, None
    for name, spec in LADDERS.items():
        fdf = frame_for(df, spec["residuel"])
        log(f"fold {fy} : fit {name} ({spec['residuel']})…")
        r = fit_fold(fdf, spec["specs"], fy, copro)
        if idu_ref is None:
            idu_ref = r["test"]["idu"].to_numpy()
            preds["y"] = np.asarray(r["y"], dtype=int)
            preds["hc"] = r["hc"]
            preds["in_vivier"] = r["test"]["idu"].isin(vivier_idus).to_numpy()
            preds["nu"] = (r["test"]["nu"] == True).to_numpy()   # noqa: E712
            preds["idu"] = idu_ref
        else:
            assert np.array_equal(r["test"]["idu"].to_numpy(), idu_ref), "lignes désalignées"
        preds[f"p_{name}"] = r["p"]
    REPORTS.mkdir(parents=True, exist_ok=True)
    np.savez(cache, **preds)
    log(f"fold {fy} : caché → {cache}")
    return preds


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    vivier_idus = set(pd.read_sql(text(
        "SELECT par.idu FROM dryrun_parcel_evaluations d JOIN parcels par ON par.id = d.parcel_id "
        "WHERE d.run_label = :r AND d.status <> 'exclue'"), engine(),
        params={"r": SERVED_RUN})["idu"])
    log(f"vivier servi (fixe sur les 3 folds) : {len(vivier_idus):,} parcelles")
    copro = pd.read_sql("SELECT idu, (copro_rnic OR copro_dvf) AS copro FROM p_model_ext_copro",
                        engine()).set_index("idu")["copro"]
    df_cache = [None]

    data = {fy: fit_or_load(fy, vivier_idus, copro, df_cache) for fy in FOLDS}

    seg_defs = {"nu": lambda d: d["nu"], "bati": lambda d: ~d["nu"]}
    per_fold_rows, pooled_rows, verdict = [], [], {}
    for seg, segfn in seg_defs.items():
        folds_seg, per_fold_meta = [], []
        for fy in FOLDS:
            d = data[fy]
            m = d["hc"] & d["in_vivier"] & segfn(d)
            y, pa, pb = d["y"][m], d["p_actuel"][m], d["p_C_bati"][m]
            k = max(1, int(round(TOP_PCT * len(y))))
            folds_seg.append((y, pa, pb, k))
            ra = rr_median(y, pa, k)
            rb = rr_median(y, pb, k)
            dmed, dlo, dhi, dvar = paired_delta_ic(y, pa, pb, k)
            statut = "supérieur" if dlo > 0 else "inférieur" if dhi < 0 else "dans le bruit"
            per_fold_meta.append({"delta_median": dmed, "var": dvar})
            per_fold_rows.append({"segment": seg, "fold": fy, "n": len(y), "k": k,
                                  "base_pct": round(float(y.mean()) * 100, 4),
                                  "rr_actuel": round(ra, 3), "rr_C_bati": round(rb, 3),
                                  "delta": round(dmed, 3), "ic_bas": round(dlo, 3),
                                  "ic_haut": round(dhi, 3), "statut": statut})
            log(f"[{seg} {fy}] n={len(y):,} k={k} base {y.mean()*100:.3f}% · "
                f"actuel {ra:.2f} · C_bati {rb:.2f} · Δ {dmed:+.2f} [{dlo:+.2f},{dhi:+.2f}] → {statut}")

        pool = pooled_delta_ic(folds_seg)
        meta = meta_pool(per_fold_meta)
        sup_pool = pool["ic_bas"] > 0
        inf_pool = pool["ic_haut"] < 0
        sup_meta = meta["ic_bas"] > 0
        inf_meta = meta["ic_haut"] < 0
        verdict[seg] = {"sup_pool": sup_pool, "inf_pool": inf_pool,
                        "sup_meta": sup_meta, "inf_meta": inf_meta}
        pooled_rows.append({"segment": seg,
                            "pool_rr_actuel": round(pool["rr_actuel"], 3),
                            "pool_rr_C_bati": round(pool["rr_C_bati"], 3),
                            "pool_delta": round(pool["delta_median"], 3),
                            "pool_ic_bas": round(pool["ic_bas"], 3),
                            "pool_ic_haut": round(pool["ic_haut"], 3),
                            "pool_statut": "supérieur" if sup_pool else "inférieur" if inf_pool else "dans le bruit",
                            "meta_delta": round(meta["delta"], 3),
                            "meta_ic_bas": round(meta["ic_bas"], 3),
                            "meta_ic_haut": round(meta["ic_haut"], 3),
                            "meta_statut": "supérieur" if sup_meta else "inférieur" if inf_meta else "dans le bruit"})
        log(f"[{seg} AGRÉGÉ] POOLING Δ {pool['delta_median']:+.2f} "
            f"[{pool['ic_bas']:+.2f},{pool['ic_haut']:+.2f}] → {pooled_rows[-1]['pool_statut']}  ·  "
            f"MÉTA Δ {meta['delta']:+.2f} [{meta['ic_bas']:+.2f},{meta['ic_haut']:+.2f}] "
            f"→ {pooled_rows[-1]['meta_statut']}")

    pd.DataFrame(per_fold_rows).to_csv(REPORTS / "par_fold.csv", index=False)
    pd.DataFrame(pooled_rows).to_csv(REPORTS / "agrege.csv", index=False)

    # ── ECE agrégée (micro-moyenne sur les 3 folds, population vivier) ────────────────
    from labuse.scoring.p_model import evaluate as ev
    ece_rows = []
    ys_a, pa_a, pb_a = [], [], []
    for fy in FOLDS:
        d = data[fy]
        m = d["hc"] & d["in_vivier"]
        ys_a.append(d["y"][m]); pa_a.append(d["p_actuel"][m]); pb_a.append(d["p_C_bati"][m])
    ys_a = np.concatenate(ys_a); pa_a = np.concatenate(pa_a); pb_a = np.concatenate(pb_a)
    ea, _ = ev.ece(ys_a, pa_a); eb, _ = ev.ece(ys_a, pb_a)
    ece_rows.append({"population": "vivier_3folds", "ece_actuel": round(ea, 4),
                     "ece_C_bati": round(eb, 4), "degrade": eb > ea + 1e-4})
    pd.DataFrame(ece_rows).to_csv(REPORTS / "ece.csv", index=False)
    log(f"ECE agrégée (vivier, 3 folds) : actuel {ea:.4f} · C_bati {eb:.4f}")

    # ── LA DOUBLE BARRE sur l'AGRÉGÉ (pooling primaire) ──────────────────────────────
    a = not any(v["inf_pool"] for v in verdict.values())
    b = any(v["sup_pool"] for v in verdict.values())
    c = not ece_rows[0]["degrade"]
    promu = a and b and c
    # accord des deux méthodes ?
    a_m = not any(v["inf_meta"] for v in verdict.values())
    b_m = any(v["sup_meta"] for v in verdict.values())
    promu_meta = a_m and b_m and c
    log("═" * 72)
    log(f"DOUBLE BARRE (POOLING) : (a) jamais inférieur={a} · (b) supérieur ≥1 seg={b} · (c) ECE ok={c}")
    log(f"  → C_bati {'PROMU' if promu else 'NON PROMU'} (pooling)")
    log(f"DOUBLE BARRE (MÉTA)    : (a)={a_m} · (b)={b_m} · (c)={c} → {'PROMU' if promu_meta else 'NON PROMU'}")
    log(f"ACCORD DES DEUX MÉTHODES : {'OUI' if promu == promu_meta else 'NON — donner les deux'}")
    pd.DataFrame([{"methode": "pooling", "a": a, "b": b, "c": c, "promu": promu},
                  {"methode": "meta", "a": a_m, "b": b_m, "c": c, "promu": promu_meta}]
                 ).to_csv(REPORTS / "verdict.csv", index=False)
    log("FIN — sorties dans reports/m132/")


if __name__ == "__main__":
    main()
