"""M71 B3 — garde de NON-CONSTANCE du scoring (règle des trois fois).

Trois signaux morts découverts silencieux (Renouvellement constant, entonnoir_motifs
constant, pv_candidat false partout — audit M66-B) : un signal constant sur tout le parc
ne discrimine rien. La garde tourne sur la matrice de features au BUILD (p_v2.pipeline,
après derive) ; ces tests verrouillent sa logique sur des matrices synthétiques.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from labuse.scoring.p_model.features import (
    FEATURE_NAMES_ACTIFS,
    FEATURES,
    NON_CONSTANCE_EXEMPTIONS,
    SignalConstantError,
    check_non_constance,
)


def _matrice(n: int = 50, constantes: dict | None = None) -> pd.DataFrame:
    """Matrice synthétique : chaque feature active VARIE (2 valeurs), sauf `constantes`."""
    rng = np.random.default_rng(42)
    df = pd.DataFrame({name: rng.integers(0, 2, n) for name in FEATURE_NAMES_ACTIFS})
    for name, val in (constantes or {}).items():
        df[name] = val
    return df


def test_matrice_vivante_passe():
    assert check_non_constance(_matrice(), exemptions={}) == []


def test_signal_constant_refuse_et_nomme():
    # le cas pv_candidat : bool false partout → build refusé, la feature est NOMMÉE
    with pytest.raises(SignalConstantError, match="pv_candidat"):
        check_non_constance(_matrice(constantes={"pv_candidat": False}), exemptions={})


def test_constant_meme_avec_nan_refuse():
    # une colonne 100 % NaN est constante aussi (nunique dropna=False == 1)
    with pytest.raises(SignalConstantError, match="pente_moy_deg"):
        check_non_constance(_matrice(constantes={"pente_moy_deg": np.nan}), exemptions={})


def test_exemption_datee_passe_mais_journalisee():
    # un mort EXEMPTÉ (arbitrage en cours) ne casse pas le build mais est RENVOYÉ (jamais avalé)
    morts = check_non_constance(
        _matrice(constantes={"pv_candidat": False}),
        exemptions={"pv_candidat": "arbitrage en cours"})
    assert morts == ["pv_candidat"]


def test_feature_retiree_ignoree():
    # une feature `retired` constante n'échoue pas : elle est déjà hors des entraînements
    retiree = next(f.name for f in FEATURES if f.retired)
    df = _matrice()
    df[retiree] = 0
    assert check_non_constance(df, exemptions={}) == []


def test_exemption_reelle_est_datee_et_motivee():
    # l'exemption vivante du registre (pv_candidat, M71 B2) doit rester motivée — jamais
    # une chaîne vide qui deviendrait un silence institutionnalisé.
    for name, motif in NON_CONSTANCE_EXEMPTIONS.items():
        assert name in {f.name for f in FEATURES}
        assert "M71" in motif and len(motif) > 30
