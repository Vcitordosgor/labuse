"""Tests unitaires PURS (sans DB) du binning WoE, du modèle et des métriques."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from labuse.scoring.p_model import evaluate as ev
from labuse.scoring.p_model.woe import fit_categorical, fit_numeric

RNG = np.random.RandomState(974)


def test_woe_numerique_monotone_contraint():
    # signal croissant bruité → la contrainte +1 doit produire des taux non décroissants
    x = pd.Series(RNG.uniform(0, 1, 20000))
    y = pd.Series((RNG.uniform(0, 1, 20000) < 0.02 + 0.10 * x).astype(int))
    bf = fit_numeric("f", x, y, monotone=+1, min_count=500)
    rates = bf.event_rates
    assert all(rates[i + 1] >= rates[i] - 1e-12 for i in range(len(rates) - 1))
    assert len(bf.woe) <= 10


def test_woe_effectif_minimum_et_plafond_bins():
    x = pd.Series(RNG.normal(0, 1, 5000))
    y = pd.Series(RNG.binomial(1, 0.05, 5000))
    bf = fit_numeric("f", x, y, monotone=0, min_count=400)
    assert all(c >= 400 for c in bf.counts)
    assert len(bf.woe) <= 10


def test_woe_bin_manquant_explicite():
    x = pd.Series(np.where(RNG.uniform(0, 1, 10000) < 0.3, np.nan, RNG.uniform(0, 1, 10000)))
    y = pd.Series(RNG.binomial(1, 0.05, 10000))
    bf = fit_numeric("f", x, y, min_count=200)
    assert bf.missing_count > 2500
    tr = bf.transform(pd.Series([np.nan, 0.5]))
    assert tr[0] == pytest.approx(bf.missing_woe)
    assert not np.isnan(tr).any()          # aucun NA silencieux


def test_woe_categoriel_regroupe_les_rares():
    x = pd.Series(["a"] * 4000 + ["b"] * 4000 + ["rare1"] * 30 + ["rare2"] * 20)
    y = pd.Series(RNG.binomial(1, 0.05, 8050))
    bf = fit_categorical("f", x, y, min_count=200)
    assert bf.categories["rare1"] == bf.categories["rare2"]  # bin « autres » commun
    assert bf.categories["a"] != bf.categories["b"]


def test_woe_booleen_via_categoriel():
    x = pd.Series(RNG.uniform(0, 1, 8000) < 0.5)
    y = pd.Series((RNG.uniform(0, 1, 8000) < np.where(x, 0.08, 0.02)).astype(int))
    bf = fit_categorical("f", x, y, min_count=200)
    i_true, i_false = bf.categories["true"], bf.categories["false"]
    assert bf.woe[i_true] > bf.woe[i_false]


def test_rr_at_k_score_parfait_et_aleatoire():
    y = np.zeros(10000, dtype=int)
    y[:100] = 1
    parfait = y.astype(float)
    assert ev.rr_at_k(y, parfait, 100)["rr"] == pytest.approx(100.0)  # 1 % de base
    hasard = np.random.RandomState(974).uniform(size=10000)
    assert ev.rr_at_k(y, hasard, 1000)["rr"] == pytest.approx(1.0, abs=0.6)


def test_rr_ties_departages_par_seed_reproductible():
    y = np.random.RandomState(1).binomial(1, 0.1, 5000)
    score = np.zeros(5000)  # égalité totale → tirage seedé
    a = ev.rr_at_k(y, score, 500, seed=974)
    b = ev.rr_at_k(y, score, 500, seed=974)
    assert a == b


def test_permutation_control_proche_de_1():
    rng = np.random.RandomState(974)
    y = rng.binomial(1, 0.02, 50000)
    score = y * 10.0 + rng.normal(0, 1, 50000)      # score très informatif
    annees = np.full(50000, 2024)
    assert ev.rr_at_k(y, score, 1000)["rr"] > 5     # sanité : le vrai score marche
    perm = ev.permutation_control(y, score, annees, 1000)
    assert perm["rr"] == pytest.approx(1.0, abs=0.7)


def test_contributions_somment_au_margin():
    from labuse.scoring.p_model.model import PModel

    n = 6000
    df = pd.DataFrame({
        "annee": 2023,
        "rot_nu": RNG.uniform(0, 0.05, n),
        "rot_bati": RNG.uniform(0, 0.05, n),
        "zone_plu": RNG.choice(["U", "AU", "A", "N", "inconnu"], n),
        "tenure_bin": RNG.choice(["<1", "1-2", "inconnu"], n),
    })
    logit = -4 + 40 * df["rot_nu"] + (df["zone_plu"] == "U") * 0.8
    y = pd.Series((RNG.uniform(0, 1, n) < 1 / (1 + np.exp(-logit))).astype(int))
    names = ["rot_nu", "rot_bati", "zone_plu", "tenure_bin"]
    m = PModel(feature_names=names).fit(df, y, C=1.0, min_count=200)
    contrib = m.contributions(df)
    recomposed = contrib[names].sum(axis=1).to_numpy() + m.intercept
    assert np.allclose(recomposed, m.margin(df), atol=1e-9)
    assert (contrib["contrib_Z"] + contrib["contrib_D"]).to_numpy() == pytest.approx(
        contrib[names].sum(axis=1).to_numpy(), abs=1e-9)
