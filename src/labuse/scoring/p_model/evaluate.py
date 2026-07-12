"""Protocole d'évaluation strict (lot 5) — RR@k, IC bootstrap, lift, calibration,
churn, contrôles négatifs. Tirages seedés 974, documentés.

RR@k = taux de mutation observé dans le top-k / taux global.
Les égalités de score (V v1.3 notamment) sont départagées par tirage aléatoire
SEEDÉ — jamais par l'ordre de la table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import SEED


def _ranked_top_mask(score: np.ndarray, k: int, rng: np.random.RandomState) -> np.ndarray:
    """Masque du top-k au score décroissant, ties départagés par tirage seedé.
    Les scores NaN (ex. V absent chez les PP) sont relégués en toute fin, dans un
    ordre lui aussi seedé."""
    tie = rng.random(len(score))
    s = np.where(np.isnan(score), -np.inf, score)
    order = np.lexsort((tie, -s))
    mask = np.zeros(len(score), dtype=bool)
    mask[order[:k]] = True
    return mask


def rr_at_k(y: np.ndarray, score: np.ndarray, k: int,
            seed: int = SEED) -> dict:
    rng = np.random.RandomState(seed)
    top = _ranked_top_mask(score, k, rng)
    base = float(y.mean())
    top_rate = float(y[top].mean())
    return {"k": k, "taux_global": base, "taux_topk": top_rate,
            "rr": top_rate / base if base > 0 else float("nan"),
            "positifs_topk": int(y[top].sum())}


def bootstrap_rr(y: np.ndarray, score: np.ndarray, k: int, n_boot: int = 1000,
                 seed: int = SEED) -> dict:
    """IC95 bootstrap du RR@k (rééchantillonnage des lignes, k constant)."""
    rng = np.random.RandomState(seed)
    vals = []
    n = len(y)
    for _ in range(n_boot):
        idx = rng.randint(0, n, n)
        yb, sb = y[idx], score[idx]
        top = _ranked_top_mask(sb, k, rng)
        base = yb.mean()
        if base > 0:
            vals.append(yb[top].mean() / base)
    lo, hi = np.percentile(vals, [2.5, 97.5])
    point = rr_at_k(y, score, k, seed=seed)
    return {**point, "ic95_bas": float(lo), "ic95_haut": float(hi), "n_boot": n_boot}


def lift_table(y: np.ndarray, score: np.ndarray, seed: int = SEED,
               percentiles: tuple[float, ...] = (0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 50, 100)) -> pd.DataFrame:
    n = len(y)
    base = y.mean()
    rows = []
    for pct in percentiles:
        k = max(1, int(round(n * pct / 100)))
        top = _ranked_top_mask(score, k, np.random.RandomState(seed))
        rows.append((pct, k, int(y[top].sum()), float(y[top].mean()),
                     float(y[top].mean() / base) if base > 0 else np.nan,
                     float(y[top].sum() / max(y.sum(), 1))))
    return pd.DataFrame(rows, columns=["percentile", "k", "positifs", "taux",
                                       "rr", "rappel"])


def ventilation(df: pd.DataFrame, y: np.ndarray, score: np.ndarray, k: int,
                col: str = "owner_type", seed: int = SEED) -> pd.DataFrame:
    """Composition du top-k et performance par segment (PM/PP/public/bailleur)."""
    rng = np.random.RandomState(seed)
    top = _ranked_top_mask(score, k, rng)
    seg = df[col].fillna("na").to_numpy()
    rows = []
    for g in pd.unique(seg):
        m = seg == g
        base_g = float(y[m].mean()) if m.sum() else np.nan
        in_top = int((top & m).sum())
        rows.append((g, int(m.sum()), base_g, in_top,
                     float(y[top & m].mean()) if in_top else np.nan,
                     float(y[top & m].mean() / base_g) if in_top and base_g > 0 else np.nan))
    return pd.DataFrame(rows, columns=[col, "n_total", "taux_base", "n_topk",
                                       "taux_topk", "rr_segment"])


def ece(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> tuple[float, pd.DataFrame]:
    """Expected calibration error (bins équi-effectifs) + courbe de fiabilité."""
    order = np.argsort(p)
    splits = np.array_split(order, n_bins)
    rows, err = [], 0.0
    for s in splits:
        if not len(s):
            continue
        conf, obs = float(p[s].mean()), float(y[s].mean())
        rows.append((len(s), conf, obs))
        err += len(s) / len(y) * abs(conf - obs)
    return float(err), pd.DataFrame(rows, columns=["n", "p_moyen", "taux_observe"])


def churn_topk(scores_a: pd.Series, scores_b: pd.Series, k: int,
               seed: int = SEED) -> dict:
    """Overlap du top-k entre deux scorings (index = idu)."""
    common = scores_a.index.intersection(scores_b.index)
    a, b = scores_a.loc[common], scores_b.loc[common]
    rng = np.random.RandomState(seed)
    top_a = set(common[_ranked_top_mask(a.to_numpy(), k, rng)])
    rng = np.random.RandomState(seed)
    top_b = set(common[_ranked_top_mask(b.to_numpy(), k, rng)])
    inter = len(top_a & top_b)
    return {"k": k, "overlap": inter, "overlap_pct": inter / k,
            "entrants": len(top_b - top_a), "sortants": len(top_a - top_b)}


def permutation_control(y: np.ndarray, score: np.ndarray, annees: np.ndarray,
                        k: int, seed: int = SEED) -> dict:
    """Labels permutés INTRA-année : RR@k attendu ≈ 1."""
    rng = np.random.RandomState(seed)
    y_perm = y.copy()
    for a in np.unique(annees):
        m = annees == a
        y_perm[m] = rng.permutation(y_perm[m])
    return rr_at_k(y_perm, score, k, seed=seed)
