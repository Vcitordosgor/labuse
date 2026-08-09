"""ALGO-2 (précision Vic n°3) — le bin « inconnu » des features propriétaire est une
VRAIE catégorie WoE (effectif ≥ min_count → WoE propre), jamais un zéro neutre :
sinon les folds 2017-2019 (sans panel PM) seraient silencieusement dégradés et la
comparaison au champion biaisée.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from labuse.scoring.p_model.woe import fit_categorical


def test_inconnu_categorie_reelle_woe_propre():
    # 3 000 lignes : 'inconnu' (années sans panel) a un taux d'événement DIFFÉRENT du reste
    rng = np.random.RandomState(974)
    cat = np.array(["inconnu"] * 1000 + ["pm_privee"] * 1000 + ["public"] * 1000)
    y = pd.Series(np.concatenate([
        rng.binomial(1, 0.02, 1000),      # inconnu : 2 %
        rng.binomial(1, 0.08, 1000),      # pm_privee : 8 %
        rng.binomial(1, 0.01, 1000)]))    # public : 1 %
    bf = fit_categorical("prop_type", pd.Series(cat), y, min_count=200)
    assert "inconnu" in bf.categories, "'inconnu' doit être une catégorie à part entière"
    i = bf.categories["inconnu"]
    assert bf.counts[i] >= 200
    assert bf.woe[i] != 0.0, "WoE propre exigé — pas un zéro neutre"
    # et il est bien DISTINCT du WoE de pm_privee (taux différents → WoE différents)
    j = bf.categories["pm_privee"]
    assert abs(bf.woe[i] - bf.woe[j]) > 0.3


def test_inconnu_string_pas_nan():
    # garde-fou : si 'inconnu' arrivait en NaN, il passerait en missing_woe —
    # le builder ALGO-2 émet la CHAÎNE 'inconnu' (fillna compris), jamais NaN.
    cat = pd.Series(["inconnu"] * 300 + ["pm_privee"] * 300)
    y = pd.Series([0] * 280 + [1] * 20 + [0] * 270 + [1] * 30)
    bf = fit_categorical("prop_type", cat, y, min_count=200)
    assert bf.missing_count == 0                     # rien en NaN
    assert set(bf.categories) == {"inconnu", "pm_privee"}
