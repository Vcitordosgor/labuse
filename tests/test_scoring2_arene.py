"""SCORING-2 — gardes du harnais d'arène (fonctions pures, sans DB, sans artefact).

Le harnais scripts/audit/scoring/ n'est PAS du code servi : ces tests verrouillent
seulement ses invariants purs — la table de traduction K6 (français, source datée),
la règle de promotion K5 (écrite, jamais appliquée), le codage censoring K1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/audit/scoring"))


@pytest.fixture(scope="module")
def raisons():
    return pytest.importorskip("raisons")


@pytest.fixture(scope="module")
def challenger():
    return pytest.importorskip("challenger")


def _ligne_type() -> dict:
    return {
        "idu": "97411000AB0001", "tenure_annees": 8.2, "tenure_censuree": False,
        "tenure_plancher_annees": 11.0, "permis_anciennete_annees": np.nan,
        "permis_jamais": True, "zone_plu": "U", "sdp_residuelle_v2_m2": 640.0,
        "sdp_residuelle_m2": 640.0, "sous_densite_v2": True, "sous_densite": True,
        "residuel_famille": "calculee", "nu_constructible_v3": "nu_droits",
        "surface_m2": 812.0, "rot_nu": 0.031, "rot_bati": 0.012,
        "med_pm2_terrain_36m": 210.0, "med_pm2_bati_36m": 2350.0,
        "tendance_pm2_bati": 0.06, "dens_bati_secteur": 0.4,
        "pct_bati_secteur": 0.72, "filo_snv_pp": 19500.0, "filo_pct_pauv": 0.31,
        "filo_pct_prop": 0.55, "pente_moy_deg": 7.0, "piscine": False,
        "pv_candidat": False, "ventes_150m_12m": 2.0, "ventes_150m_24m": 3.0,
        "ventes_400m_12m": 9.0, "ventes_400m_24m": 14.0, "ventes_400m_delta": 4.0,
        "permis_100m_24m": 1.0, "operations_pa_400m_24m": 1.0,
        "volume_commune_a1": 612.0, "med_pm2_commune_a1": 2380.0,
        "tendance_volume_3ans": 1.08, "pm_vendeur_actif": True,
        "acces_equipements": 2.1, "canopee_pct": 12.0, "ndvi_moyen": 0.3,
        "friche": False,
    }


def test_k6_table_traduction_phrases_completes(raisons):
    """Chaque entrée produit une phrase non vide, sourcée (parenthèse) — jamais
    un nom de variable brut ni un gabarit non rempli."""
    row = _ligne_type()
    for nom, fn in raisons.TABLE_TRADUCTION.items():
        phrase = fn(row)
        assert isinstance(phrase, str) and len(phrase) > 8, nom
        assert "(" in phrase and ")" in phrase, f"{nom} : source manquante"
        assert "{" not in phrase and "nan" not in phrase.lower(), f"{nom} : gabarit non rempli"
        assert "_" not in phrase.split("(")[0], f"{nom} : nom de variable brut dans la phrase"


def test_k6_censure_et_absences_explicites(raisons):
    """Censuré → « aucune vente connue depuis au moins N ans » ; jamais de
    permis → dit tel quel. L'absence est une information, pas un trou."""
    row = {**_ligne_type(), "tenure_annees": np.nan, "tenure_censuree": True}
    ph = raisons.TABLE_TRADUCTION["tenure_annees"](row)
    assert "Aucune vente connue depuis au moins 11 ans" in ph
    assert "DVF" in ph
    ph2 = raisons.TABLE_TRADUCTION["permis_anciennete_annees"](_ligne_type())
    assert "Jamais de permis" in ph2 and "Sitadel" in ph2


def test_k5_regle_promotion_ecrite_jamais_appliquee(challenger):
    assert challenger.REGLE_PROMOTION["appliquee_dans_ce_mandat"] is False
    champ = {"prec@100_commune_mediane": 0.06, "prec_priorite": 0.14,
             "auc_global": 0.61, "ece_bati_individuel": 0.002,
             "ece_terrain_nu": 0.004, "ece_personne_morale": 0.006,
             "ece_copropriete": 0.02}
    chall_perd = {**champ, "auc_global": 0.60,
                  "ece_bati_individuel": 0.002, "ece_terrain_nu": 0.004,
                  "ece_personne_morale": 0.006, "ece_copropriete": 0.005}
    v = challenger.verdict_arene(champ, chall_perd)
    assert v["promotion_satisfaite"] is False
    assert v["promotion_appliquee"] is False
    chall_gagne = {"prec@100_commune_mediane": 0.08, "prec_priorite": 0.18,
                   "auc_global": 0.66, "ece_bati_individuel": 0.003,
                   "ece_terrain_nu": 0.005, "ece_personne_morale": 0.007,
                   "ece_copropriete": 0.009}
    v2 = challenger.verdict_arene(champ, chall_gagne)
    assert v2["promotion_satisfaite"] is True
    assert v2["promotion_appliquee"] is False  # TOUJOURS False : Vic bascule


def test_k5_monotonie_metier_jamais_sur_categorielle(challenger):
    """Les contraintes déclarées ne portent que sur des numériques."""
    cats = {"zone_plu", "tenure_bin", "permis_bin", "residuel_famille",
            "nu_constructible_v2", "nu_constructible_v3"}
    assert not (set(challenger.MONOTONIE_METIER) & cats)


def test_k1_codage_censoring_pur():
    """appliquer_censoring : valeur connue → années ; inconnue → NaN (bin WoE
    explicite) + indicateur censuré vrai ; jamais l'inverse."""
    candidats = pytest.importorskip("candidats")
    df = pd.DataFrame({
        "idu": ["a", "b"], "annee": [2025, 2025],
        "nu": [True, False], "zone_plu": ["U", "A"],
    })
    cens = pd.DataFrame({
        "idu": ["a", "b"], "annee": [2025, 2025],
        "derniere_mutation": ["2020-06-01", None],
        "dernier_permis": [None, "2023-03-01"],
        "debut_histo": ["2014-01-05", "2014-01-05"],
    })
    out = candidats.appliquer_censoring(df, cens)
    assert out.loc[0, "tenure_censuree"] == False  # noqa: E712
    assert abs(out.loc[0, "tenure_annees"] - 4.6) < 0.1
    assert out.loc[1, "tenure_censuree"] == True  # noqa: E712
    assert pd.isna(out.loc[1, "tenure_annees"])
    assert out.loc[0, "permis_jamais"] == True  # noqa: E712
    assert pd.isna(out.loc[0, "permis_anciennete_annees"])
    assert abs(out.loc[1, "permis_anciennete_annees"] - 1.8) < 0.1
    assert list(out["nu_constructible_v2"]) == ["nu_constructible", "bati"]
