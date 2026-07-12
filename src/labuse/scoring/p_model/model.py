"""Modèle P : logistique régularisée sur WoE → log-hazard additif par bloc.

Contributions traçables ligne à ligne : contribution(feature) = coef × WoE(bin),
contribution(bloc) = Σ features du bloc — la doctrine des 43 M de lignes survit.
Calibration isotonique ajustée sur val 2024 ; intercept recalable sur l'année la
plus récente sans toucher aux coefficients.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from . import SEED
from .features import FEATURES
from .woe import WoeEncoder

SPEC_BY_NAME = {f.name: f for f in FEATURES}


@dataclass
class PModel:
    feature_names: list[str]
    encoder: WoeEncoder | None = None
    coefs: dict[str, float] = field(default_factory=dict)
    intercept: float = 0.0
    intercept_shift: float = 0.0          # recalage éventuel (année la plus récente)
    interactions: list[tuple[str, str]] = field(default_factory=list)
    inter_coefs: dict[str, float] = field(default_factory=dict)
    year_dummies: list[int] = field(default_factory=list)  # années non-référence du train
    year_coefs: dict[int, float] = field(default_factory=dict)
    iso: IsotonicRegression | None = None
    meta: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ fit
    def fit(self, df: pd.DataFrame, y: pd.Series, C: float = 1.0,
            min_count: int = 200) -> "PModel":
        if self.encoder is None:  # un encodeur déjà fourni (mining) est réutilisé tel quel
            specs = [SPEC_BY_NAME[n] for n in self.feature_names]
            self.encoder = WoeEncoder(min_count=min_count).fit(df, y, specs)
        self.coefs, self.inter_coefs, self.year_coefs = {}, {}, {}
        X = self._design(df)
        lr = LogisticRegression(C=C, max_iter=2000, random_state=SEED)  # L2 par défaut
        lr.fit(X.to_numpy(), y.to_numpy())
        for col, c in zip(X.columns, lr.coef_[0]):
            if col.startswith("annee_"):
                self.year_coefs[int(col.split("_")[1])] = float(c)
            elif "*" in col:
                self.inter_coefs[col] = float(c)
            else:
                self.coefs[col] = float(c)
        self.intercept = float(lr.intercept_[0])
        self.meta["C"] = C
        self.meta["n_train"] = int(len(df))
        return self

    def _design(self, df: pd.DataFrame) -> pd.DataFrame:
        X = self.encoder.transform(df)
        for f1, f2 in self.interactions:
            X[f"{f1}*{f2}"] = X[f1] * X[f2]
        for yr in self.year_dummies:
            X[f"annee_{yr}"] = (df["annee"] == yr).astype(float)
        return X

    # -------------------------------------------------------------- predict
    def margin(self, df: pd.DataFrame) -> np.ndarray:
        """Log-hazard additif (avant calibration), intercept_shift inclus."""
        X = self._design(df)
        z = np.full(len(df), self.intercept + self.intercept_shift)
        for col, c in {**self.coefs, **self.inter_coefs}.items():
            z += c * X[col].to_numpy()
        for yr, c in self.year_coefs.items():
            z += c * X[f"annee_{yr}"].to_numpy()
        return z

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        z = self.margin(df)
        if self.iso is not None:
            return np.clip(self.iso.predict(z), 1e-7, 1 - 1e-7)
        return 1.0 / (1.0 + np.exp(-z))

    def contributions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Contribution par feature (coef × WoE) + agrégats par bloc, ligne à ligne."""
        X = self._design(df)
        out = pd.DataFrame(index=df.index)
        for col, c in {**self.coefs, **self.inter_coefs}.items():
            out[col] = c * X[col].to_numpy()
        bloc = {f.name: f.bloc for f in FEATURES}
        z_cols = [c for c in out.columns if bloc.get(c) == "Z"]
        d_cols = [c for c in out.columns if bloc.get(c) == "D"]
        x_cols = [c for c in out.columns if "*" in c]
        out["contrib_Z"] = out[z_cols].sum(axis=1)
        out["contrib_D"] = out[d_cols].sum(axis=1)
        out["contrib_interactions"] = out[x_cols].sum(axis=1) if x_cols else 0.0
        return out

    # ------------------------------------------------------------ calibrate
    def calibrate(self, df_val: pd.DataFrame, y_val: pd.Series) -> "PModel":
        z = self.margin(df_val)
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.iso.fit(z, y_val.to_numpy())
        return self

    def recale_intercept(self, df: pd.DataFrame, y: pd.Series) -> "PModel":
        """Recale l'intercept (décalage additif du log-hazard) pour que le taux moyen
        prédit (avant isotonique) colle au taux observé de l'année fournie —
        coefficients inchangés."""
        base_rate = float(y.mean())
        z = self.margin(df) - self.intercept_shift
        # recherche du décalage delta : mean(sigmoid(z + delta)) = base_rate
        lo, hi = -10.0, 10.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if float((1 / (1 + np.exp(-(z + mid)))).mean()) < base_rate:
                lo = mid
            else:
                hi = mid
        self.intercept_shift = (lo + hi) / 2
        return self

    # ---------------------------------------------------------------- io
    def save(self, path: str) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path: str) -> "PModel":
        return joblib.load(path)

    # ------------------------------------------------------------- lisible
    def model_card_rows(self) -> pd.DataFrame:
        """WoE + coefficients lisibles (model-card.md)."""
        rows = []
        for name, bf in self.encoder.binned.items():
            coef = self.coefs.get(name, 0.0)
            for i, w in enumerate(bf.woe):
                rows.append((name, SPEC_BY_NAME[name].bloc, bf.bin_label(i),
                             bf.counts[i], bf.event_rates[i], w, coef, coef * w))
            if bf.missing_count:
                rows.append((name, SPEC_BY_NAME[name].bloc, "manquant/inconnu",
                             bf.missing_count, bf.missing_rate, bf.missing_woe,
                             coef, coef * bf.missing_woe))
        return pd.DataFrame(rows, columns=[
            "feature", "bloc", "bin", "effectif", "taux_evenement", "woe",
            "coef", "log_hazard"])
