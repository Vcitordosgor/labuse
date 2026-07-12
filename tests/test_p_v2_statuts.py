"""Tests synthétiques des statuts v2 (M5 lot 6.1) — hystérésis, bypass, brûlante.

Cas exigés au mandat : une parcelle qui oscille autour du seuil ne churne pas ;
un événement daté bypasse l'hystérésis à l'entrée.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from labuse.scoring.p_v2.statuts import (
    TIER_A_CREUSER,
    TIER_BRULANTE,
    TIER_CHAUDE,
    TIER_ECARTEE,
    TIER_RESERVE,
    TierParams,
    assign_tiers,
    calibre_brulante,
    calibre_n_entree,
)

P = TierParams(n_entree=1000, n_sortie=1400, brulante_seuil_d=0.5,
               brulante_top_decile_d=1.5)


def base_row(**kw) -> dict:
    row = dict(rang=np.nan, copro=False, ecartee_etage0=False,
               sdp_residuelle_m2=100.0, surface_m2=800.0, zone_plu="U",
               p=0.01, contrib_d=0.0, event_age_mois=np.nan)
    row.update(kw)
    return row


def tiers(rows: list[dict], prev: list[str] | None = None) -> pd.Series:
    df = pd.DataFrame(rows)
    prev_s = pd.Series(prev, index=df.index) if prev is not None else None
    return assign_tiers(df, P, prev_s)


def test_oscillation_autour_du_seuil_ne_churne_pas():
    # run 1 : rang 990 → chaude. run 2 : rang 1 250 (zone tampon) → RESTE chaude.
    # run 3 : rang 1 500 (> n_sortie) → sort.
    r1 = tiers([base_row(rang=990)])
    assert r1[0] == TIER_CHAUDE
    r2 = tiers([base_row(rang=1250)], prev=[r1[0]])
    assert r2[0] == TIER_CHAUDE                     # hystérésis : pas de churn
    r3 = tiers([base_row(rang=1500)], prev=[r2[0]])
    assert r3[0] == TIER_A_CREUSER


def test_pas_d_entree_dans_la_zone_tampon_sans_evenement():
    # jamais chaude avant, rang 1 250 (entre n_entree et n_sortie) → PAS d'entrée
    r = tiers([base_row(rang=1250)], prev=[TIER_A_CREUSER])
    assert r[0] == TIER_A_CREUSER


def test_evenement_date_bypasse_l_hysteresis_a_l_entree():
    # même parcelle, événement daté de 3 mois → entre malgré la zone tampon
    r = tiers([base_row(rang=1250, event_age_mois=3)], prev=[TIER_A_CREUSER])
    assert r[0] == TIER_CHAUDE
    # événement trop vieux (8 mois > bypass 6) → pas d'entrée
    r = tiers([base_row(rang=1250, event_age_mois=8)], prev=[TIER_A_CREUSER])
    assert r[0] == TIER_A_CREUSER
    # bypass ne franchit JAMAIS n_sortie
    r = tiers([base_row(rang=1500, event_age_mois=3)], prev=[TIER_A_CREUSER])
    assert r[0] == TIER_A_CREUSER


def test_plancher_c_obligatoire_pour_chaude():
    # rang excellent mais aucune capacité (SDP 0, surface 300 m²) → pas chaude
    r = tiers([base_row(rang=5, sdp_residuelle_m2=0, surface_m2=300)])
    assert r[0] != TIER_CHAUDE
    # surface 700 m² en U sans SDP → plancher tenu
    assert tiers([base_row(rang=5, sdp_residuelle_m2=0, surface_m2=700)])[0] == TIER_CHAUDE
    # 700 m² en zone A : plancher NON tenu
    assert tiers([base_row(rang=5, sdp_residuelle_m2=0, surface_m2=700,
                           zone_plu="A")])[0] != TIER_CHAUDE


def test_copro_et_etage0_jamais_chaudes():
    assert tiers([base_row(rang=1, copro=True)])[0] != TIER_CHAUDE
    r = tiers([base_row(rang=1, ecartee_etage0=True)])
    assert r[0] == TIER_ECARTEE                      # l'étage 0 prime sur tout


def test_brulante_exige_contribution_non_zone():
    # chaude + événement récent MAIS contribution D sous le seuil → PAS brûlante
    # (doctrine : un contexte seul ne franchit jamais un seuil)
    r = tiers([base_row(rang=10, contrib_d=0.1, event_age_mois=2)])
    assert r[0] == TIER_CHAUDE
    # chaude + contribution D ≥ seuil + événement < 12 mois → brûlante
    r = tiers([base_row(rang=10, contrib_d=0.8, event_age_mois=10)])
    assert r[0] == TIER_BRULANTE
    # chaude + D très forte (top décile) sans événement → brûlante aussi
    r = tiers([base_row(rang=10, contrib_d=2.0)])
    assert r[0] == TIER_BRULANTE
    # chaude + D moyenne (≥ seuil, < top décile) sans événement → pas brûlante
    r = tiers([base_row(rang=10, contrib_d=0.8)])
    assert r[0] == TIER_CHAUDE


def test_reserve_fonciere_c_fort_p_faible():
    rows = [base_row(rang=np.nan, sdp_residuelle_m2=s, p=p)
            for s, p in [(5000, 0.001), (5000, 0.5), (10, 0.001)]] \
        + [base_row(sdp_residuelle_m2=s) for s in np.linspace(1, 100, 30)]
    r = tiers(rows)
    assert r[0] == TIER_RESERVE                      # C top décile, P sous médiane
    assert r[1] == TIER_A_CREUSER                    # C fort mais P fort → pas réserve
    assert r[2] == TIER_A_CREUSER                    # C faible


def test_calibrages():
    rangs = pd.Series(np.arange(1, 3000))
    assert calibre_n_entree(rangs, cible=1150) == 1150
    rng = np.random.RandomState(974)
    chaude = pd.DataFrame({"contrib_d": rng.normal(1, 0.5, 1000),
                           "event_age_mois": np.where(rng.uniform(size=1000) < 0.02,
                                                      3.0, np.nan)})
    p2 = calibre_brulante(chaude, P)
    df = chaude.assign(**{c: v for c, v in base_row(rang=10).items()
                          if c not in chaude})
    n = (assign_tiers(df, p2) == TIER_BRULANTE).sum()
    assert 30 <= n <= 120
