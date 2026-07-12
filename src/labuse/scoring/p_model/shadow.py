"""GBM shadow — UNIQUEMENT pour miner les interactions (jamais en prod).

HistGradientBoosting sur les MÊMES colonnes WoE que la logistique ; les paires de
features les plus importantes fournissent les candidats, la sélection finale se
fait par gain RÉEL sur val (average precision) en réinjectant le produit WoE dans
la logistique — 5 croisements maximum.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score

from . import SEED
from .model import PModel


def shadow_report(X_train: pd.DataFrame, y_train: pd.Series,
                  X_val: pd.DataFrame, y_val: pd.Series) -> dict:
    """Écart de tête logistique vs GBM (marge d'interactions à récupérer)."""
    gbm = HistGradientBoostingClassifier(random_state=SEED, max_iter=300,
                                         early_stopping=True, validation_fraction=0.15)
    gbm.fit(X_train.to_numpy(), y_train.to_numpy())
    p = gbm.predict_proba(X_val.to_numpy())[:, 1]
    return {
        "gbm": gbm,
        "val_ap": float(average_precision_score(y_val, p)),
        "val_auc": float(roc_auc_score(y_val, p)),
    }


def top_features(gbm, X_val: pd.DataFrame, y_val: pd.Series, k: int = 10,
                 sample: int = 60000) -> list[str]:
    rng = np.random.RandomState(SEED)
    idx = rng.choice(len(X_val), size=min(sample, len(X_val)), replace=False)
    imp = permutation_importance(gbm, X_val.iloc[idx].to_numpy(), y_val.iloc[idx].to_numpy(),
                                 n_repeats=3, random_state=SEED, scoring="average_precision")
    order = np.argsort(-imp.importances_mean)
    return [X_val.columns[i] for i in order[:k]]


def mine_interactions(model: PModel, df_train: pd.DataFrame, y_train: pd.Series,
                      df_val: pd.DataFrame, y_val: pd.Series,
                      max_cross: int = 5, top_k: int = 10,
                      min_gain: float = 1e-4) -> tuple[list[tuple[str, str]], pd.DataFrame]:
    """Sélection gloutonne : ajoute un produit WoE si et seulement si il améliore
    l'average precision sur val. Retourne les croisements retenus + le journal."""
    X_train = model.encoder.transform(df_train)
    X_val = model.encoder.transform(df_val)

    rep = shadow_report(X_train, y_train, X_val, y_val)
    feats = top_features(rep["gbm"], X_val, y_val, k=top_k)
    candidates = list(combinations(feats, 2))

    journal = []
    selected: list[tuple[str, str]] = []
    base = PModel(feature_names=model.feature_names)
    base.encoder = model.encoder          # binning partagé : seuls les coefs bougent
    base.year_dummies = model.year_dummies
    base.interactions = []
    base.fit(df_train, y_train, C=model.meta.get("C", 1.0))
    best_ap = float(average_precision_score(y_val, base.predict_proba(df_val)))
    journal.append(("(base)", best_ap, rep["val_ap"], True))

    while len(selected) < max_cross and candidates:
        results = []
        for pair in candidates:
            trial = PModel(feature_names=model.feature_names)
            trial.encoder = model.encoder
            trial.year_dummies = model.year_dummies
            trial.interactions = selected + [pair]
            trial.fit(df_train, y_train, C=model.meta.get("C", 1.0))
            ap = float(average_precision_score(y_val, trial.predict_proba(df_val)))
            results.append((pair, ap))
        pair, ap = max(results, key=lambda r: r[1])
        keep = ap > best_ap + min_gain
        journal.append((f"{pair[0]}*{pair[1]}", ap, rep["val_ap"], keep))
        if not keep:
            break
        selected.append(pair)
        candidates.remove(pair)
        best_ap = ap

    jdf = pd.DataFrame(journal, columns=["croisement", "val_ap_logistique",
                                         "val_ap_gbm_shadow", "retenu"])
    return selected, jdf
