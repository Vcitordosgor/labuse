"""Binning WoE — ≤ 10 bins par feature, effectif minimum par bin, monotonie
contrainte où le domaine l'impose (fusion PAV des bins adjacents violant l'ordre),
bin « manquant »/« inconnu » TOUJOURS explicite (aucun NA silencieux).

WoE(bin) = ln( part des positifs du bin / part des négatifs du bin ), lissage +0.5.
IV = Σ (part_pos - part_neg) × WoE.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

MAX_BINS = 10
PREBINS = 20
SMOOTH = 0.5


@dataclass
class BinnedFeature:
    name: str
    kind: str                                  # 'num' | 'cat'
    monotone: int = 0
    edges: list[float] = field(default_factory=list)        # num : bornes internes
    categories: dict[str, int] = field(default_factory=dict)  # cat : cat → index bin
    woe: list[float] = field(default_factory=list)
    missing_woe: float = 0.0
    counts: list[int] = field(default_factory=list)
    event_rates: list[float] = field(default_factory=list)
    missing_count: int = 0
    missing_rate: float = float("nan")
    iv: float = 0.0

    # ---------------------------------------------------------------- transform
    def transform(self, x: pd.Series) -> np.ndarray:
        idx = self.bin_index(x)
        out = np.where(idx >= 0, np.asarray(self.woe + [0.0])[idx], self.missing_woe)
        return out.astype(float)

    def bin_index(self, x: pd.Series) -> np.ndarray:
        """Index de bin par valeur ; -1 = manquant/inconnu."""
        if self.kind == "num":
            v = pd.to_numeric(x, errors="coerce")
            idx = np.searchsorted(np.asarray(self.edges), v.to_numpy(), side="right")
            return np.where(v.notna(), idx, -1)
        s = x.astype(object).where(pd.notna(x), None)
        mapped = s.map(lambda c: self.categories.get(_cat_key(c), -1) if c is not None else -1)
        return mapped.to_numpy(dtype=int)

    def bin_label(self, i: int) -> str:
        if i < 0:
            return "manquant"
        if self.kind == "cat":
            cats = [c for c, j in self.categories.items() if j == i]
            return " / ".join(sorted(cats))
        lo = self.edges[i - 1] if i > 0 else None
        hi = self.edges[i] if i < len(self.edges) else None
        if lo is None:
            return f"≤ {hi:.4g}"
        if hi is None:
            return f"> {lo:.4g}"
        return f"({lo:.4g}, {hi:.4g}]"


def _cat_key(c) -> str:
    if isinstance(c, (bool, np.bool_)):
        return "true" if c else "false"
    return str(c)


def _woe_iv(n1: np.ndarray, n0: np.ndarray) -> tuple[np.ndarray, float]:
    N1, N0 = n1.sum(), n0.sum()
    k = len(n1)
    p1 = (n1 + SMOOTH) / (N1 + SMOOTH * k)
    p0 = (n0 + SMOOTH) / (N0 + SMOOTH * k)
    woe = np.log(p1 / p0)
    iv = float(((p1 - p0) * woe).sum())
    return woe, iv


def fit_numeric(name: str, x: pd.Series, y: pd.Series, monotone: int = 0,
                min_count: int = 200, max_bins: int = MAX_BINS) -> BinnedFeature:
    v = pd.to_numeric(x, errors="coerce")
    mask = v.notna()
    yv = y[mask].to_numpy(float)
    vv = v[mask].to_numpy(float)

    edges: list[float] = []
    if len(vv) >= 2 * min_count and len(np.unique(vv)) > 1:
        qs = np.quantile(vv, np.linspace(0, 1, PREBINS + 1)[1:-1])
        edges = sorted(set(float(q) for q in qs))
    idx = np.searchsorted(np.asarray(edges), vv, side="right")
    n_bins = len(edges) + 1
    n1 = np.bincount(idx, weights=yv, minlength=n_bins)
    n0 = np.bincount(idx, weights=1 - yv, minlength=n_bins)

    def merge(i: int) -> None:
        """Fusionne le bin i avec le bin i+1 (supprime la borne edges[i])."""
        nonlocal n1, n0, edges
        n1 = np.concatenate([n1[:i], [n1[i] + n1[i + 1]], n1[i + 2:]])
        n0 = np.concatenate([n0[:i], [n0[i] + n0[i + 1]], n0[i + 2:]])
        edges = edges[:i] + edges[i + 1:]

    # 1. effectif minimum
    while len(n1) > 1:
        tot = n1 + n0
        i = int(tot.argmin())
        if tot[i] >= min_count:
            break
        merge(i if i < len(n1) - 1 else i - 1)
    # 2. monotonie contrainte : fusion des adjacents violant l'ordre des taux
    if monotone:
        changed = True
        while changed and len(n1) > 1:
            changed = False
            rates = n1 / np.maximum(n1 + n0, 1)
            for i in range(len(rates) - 1):
                if (rates[i + 1] - rates[i]) * monotone < 0:
                    merge(i)
                    changed = True
                    break
    # 3. plafond de bins : fusion des taux adjacents les plus proches
    while len(n1) > max_bins:
        rates = n1 / np.maximum(n1 + n0, 1)
        i = int(np.abs(np.diff(rates)).argmin())
        merge(i)

    woe, iv = _woe_iv(n1, n0)
    bf = BinnedFeature(name=name, kind="num", monotone=monotone, edges=list(edges),
                       woe=[float(w) for w in woe],
                       counts=[int(c) for c in (n1 + n0)],
                       event_rates=[float(r) for r in n1 / np.maximum(n1 + n0, 1)],
                       iv=iv)
    _fit_missing(bf, y, mask, min_count)
    return bf


def fit_categorical(name: str, x: pd.Series, y: pd.Series,
                    min_count: int = 200) -> BinnedFeature:
    s = x.astype(object).where(pd.notna(x), None)
    mask = s.notna()
    keys = s[mask].map(_cat_key)
    yv = y[mask].to_numpy(float)

    stats = pd.DataFrame({"k": keys.to_numpy(), "y": yv}).groupby("k")["y"].agg(["sum", "count"])
    small = stats[stats["count"] < min_count]
    big = stats[stats["count"] >= min_count]
    groups: list[list[str]] = [[k] for k in big.index]
    if len(small):
        groups.append(list(small.index))  # « autres » : catégories rares regroupées

    n1 = np.array([stats.loc[g, "sum"].sum() for g in groups], float)
    n0 = np.array([stats.loc[g, "count"].sum() for g in groups], float) - n1
    woe, iv = _woe_iv(n1, n0)
    categories = {k: i for i, g in enumerate(groups) for k in g}
    bf = BinnedFeature(name=name, kind="cat", categories=categories,
                       woe=[float(w) for w in woe],
                       counts=[int(c) for c in (n1 + n0)],
                       event_rates=[float(r) for r in n1 / np.maximum(n1 + n0, 1)],
                       iv=iv)
    _fit_missing(bf, y, mask, min_count)
    return bf


def _fit_missing(bf: BinnedFeature, y: pd.Series, mask: pd.Series, min_count: int) -> None:
    """Bin « manquant » explicite : WoE propre si l'effectif le permet, sinon 0
    (neutre, jamais de NA silencieux)."""
    miss = ~mask
    bf.missing_count = int(miss.sum())
    if bf.missing_count:
        bf.missing_rate = float(y[miss].mean())
    if bf.missing_count >= min_count:
        n1m = float(y[miss].sum())
        n0m = float(bf.missing_count) - n1m
        N1 = float(y.sum())
        N0 = float(len(y)) - N1
        p1 = (n1m + SMOOTH) / (N1 + 2 * SMOOTH)
        p0 = (n0m + SMOOTH) / (N0 + 2 * SMOOTH)
        bf.missing_woe = float(np.log(p1 / p0))
    else:
        bf.missing_woe = 0.0


class WoeEncoder:
    """Encodeur WoE de l'ensemble des features (fit sur TRAIN uniquement)."""

    def __init__(self, min_count: int = 200):
        self.min_count = min_count
        self.binned: dict[str, BinnedFeature] = {}

    def fit(self, df: pd.DataFrame, y: pd.Series, specs) -> "WoeEncoder":
        for spec in specs:
            col = _spec_column(spec, df)
            if spec.kind == "num":
                self.binned[spec.name] = fit_numeric(
                    spec.name, col, y, monotone=spec.monotone, min_count=self.min_count)
            else:  # cat et bool : catégoriel (bool → 'true'/'false')
                self.binned[spec.name] = fit_categorical(
                    spec.name, col, y, min_count=self.min_count)
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = {}
        for name, bf in self.binned.items():
            out[name] = bf.transform(_named_column(name, df))
        return pd.DataFrame(out, index=df.index)

    def iv_table(self) -> pd.DataFrame:
        return pd.DataFrame(
            [(n, b.kind, len(b.woe), b.iv, b.missing_count) for n, b in self.binned.items()],
            columns=["feature", "kind", "n_bins", "iv", "n_manquants"],
        ).sort_values("iv", ascending=False)


def _spec_column(spec, df: pd.DataFrame) -> pd.Series:
    return _named_column(spec.name, df)


def _named_column(name: str, df: pd.DataFrame) -> pd.Series:
    if name not in df.columns:
        raise KeyError(f"feature absente du dataset : {name}")
    return df[name]
