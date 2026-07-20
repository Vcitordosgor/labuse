"""PHASE 0 « Le Juge » — J1.c : features dérivées du modèle P (`p_model/features.derive`).

Fonctions PURES (pandas, aucune base) : composite d'accès aux équipements (décroissance
exponentielle des distances) et shrinkage gamma-Poisson des taux de rotation. Encode le
comportement ACTUEL (τ = 800 m, r̂ = (n + m·r_commune)/(expo + m)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from labuse.scoring.p_model.features import EQUIP_TAU_M, derive


def _df(rows: list[dict]) -> pd.DataFrame:
    """DataFrame minimal portant TOUTES les colonnes que `derive` consomme."""
    base = dict(annee=2024, secteur="974150001", n_mut_nu_36m=0, n_mut_bati_36m=0,
                window_coverage=1.0, stock_secteur=100.0, pct_potentiel=0.0,
                dist_ecole_m=np.nan, dist_sante_m=np.nan, dist_commerce_m=np.nan, dist_tcsp_m=np.nan)
    return pd.DataFrame([{**base, **r} for r in rows])


# ───────────────────── composite équipements : décroissance exp(-d/τ) ─────────────────────

def test_equipements_decroit_avec_la_distance_ratio_e_moins_1():
    out = derive(_df([{"secteur": "974150001", "dist_ecole_m": 0.0},
                      {"secteur": "974150002", "dist_ecole_m": EQUIP_TAU_M}]))
    v0, v_tau = out["acces_equipements"].iloc[0], out["acces_equipements"].iloc[1]
    assert v0 > v_tau                                   # plus proche = contribution plus forte
    assert v0 == pytest_approx(1.0)                     # exp(0) = 1 (une seule distance à 0)
    assert v_tau == pytest_approx(np.exp(-1))           # exp(-τ/τ) = e⁻¹ ≈ 0.368
    assert (v0 / v_tau) == pytest_approx(np.e)          # ratio d=0 / d=τ = e


def test_equipements_distance_absente_contribue_zero():
    out = derive(_df([{"dist_ecole_m": np.nan}]))       # parcelle isolée (aucune distance)
    assert out["acces_equipements"].iloc[0] == 0.0


def test_equipements_somme_sur_les_quatre_familles():
    out = derive(_df([{"dist_ecole_m": 0.0, "dist_sante_m": 0.0,
                       "dist_commerce_m": 0.0, "dist_tcsp_m": 0.0}]))
    assert out["acces_equipements"].iloc[0] == pytest_approx(4.0)   # 4 familles × exp(0)


# ───────────────────── shrinkage gamma-Poisson : petit parc → prior, gros parc → brut ─────────────────────

def test_shrinkage_petit_secteur_tire_vers_la_commune_gros_reste_au_brut():
    # même commune (préfixe 97415) ; secteur A minuscule (expo ~3, 0 mutation) et secteur B massif
    # (expo ~30 000, 300 mutations). r_commune ≈ taux de B ≈ 0,01.
    out = derive(_df([
        {"secteur": "974150001", "stock_secteur": 1.0, "n_mut_nu_36m": 0},        # A : minuscule
        {"secteur": "974150002", "stock_secteur": 10000.0, "n_mut_nu_36m": 300},  # B : massif
    ]))
    a = out[out.secteur == "974150001"].iloc[0]
    b = out[out.secteur == "974150002"].iloc[0]
    r_com = 300.0 / (3.0 + 30000.0)                     # ≈ 0.009999
    raw_a, raw_b = 0.0, 300.0 / 30000.0                 # 0.0 et 0.01
    # A (peu de données) : TIRÉ vers la commune, loin de son brut (0).
    assert a["rot_nu"] > raw_a
    assert abs(a["rot_nu"] - r_com) < abs(a["rot_nu"] - raw_a)
    # B (beaucoup de données) : reste TRÈS proche de son taux brut.
    assert abs(b["rot_nu"] - raw_b) / raw_b < 0.05
    # le petit secteur subit un shrinkage BIEN plus fort que le gros.
    assert abs(a["rot_nu"] - raw_a) > abs(b["rot_nu"] - raw_b)


# petit util local (évite d'importer pytest.approx au niveau module pour ces comparaisons flottantes)
def pytest_approx(x, tol=1e-6):
    class _A:
        def __eq__(self, other):
            return abs(float(other) - float(x)) <= tol
    return _A()
