"""Statuts v2 + hystérésis (M5 lot 2) — fonctions PURES, sans DB.

Tiers : brulante / chaude / a_creuser / reserve_fonciere / ecartee.
L'étage 0 (écartée dure) est INCHANGÉ et prime sur tout.

Doctrine d'hystérésis (anti-churn, cible < 15 % par recalcul hors événements) :
- entrée en chaude : rang hors copro ≤ n_entree ET plancher C ;
- maintien : une parcelle déjà chaude/brûlante reste chaude tant que
  rang ≤ n_sortie (≈ 1,4 × n_entree) et que le plancher C tient ;
- bypass : un ÉVÉNEMENT DATÉ < event_bypass_mois prime — il fait entrer une
  parcelle dans la zone tampon (n_entree < rang ≤ n_sortie) sans attendre.

Plancher C (proposé et documenté, mandat 2.2) : SDP résiduelle > 0 OU
(surface ≥ 600 m² en zone U/AU) — un P fort sans capacité ne fait pas une
opportunité produit ; 600 m² ≈ plancher d'une division en R+1 locale.

Réserve foncière (ex-« à surveiller ») : top décile de C (SDP résiduelle
parmi les valeurs > 0) ET P sous la médiane — vitrine capacité, jamais
présentée comme pipeline (sélection négative prouvée en Phase 0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TIER_BRULANTE = "brulante"
TIER_CHAUDE = "chaude"
TIER_A_CREUSER = "a_creuser"
TIER_RESERVE = "reserve_fonciere"
TIER_ECARTEE = "ecartee"


@dataclass(frozen=True)
class TierParams:
    n_entree: int
    n_sortie: int                       # ≈ 1,4 × n_entree
    c_surface_min_m2: float = 600.0     # plancher C : surface mini en U/AU
    event_bypass_mois: int = 6          # bypass d'hystérésis à l'entrée
    brulante_event_mois: int = 12
    brulante_seuil_d: float = 0.0       # calibré mécaniquement (garde-fou 30-120)
    brulante_top_decile_d: float = 0.0  # seuil du top décile de contrib_D (chaude)


def plancher_c(df: pd.DataFrame, params: TierParams) -> pd.Series:
    """Plancher capacité : SDP résiduelle > 0 OU surface ≥ seuil en U/AU."""
    sdp = pd.to_numeric(df["sdp_residuelle_m2"], errors="coerce").fillna(0)
    surf = pd.to_numeric(df["surface_m2"], errors="coerce").fillna(0)
    en_u_au = df["zone_plu"].isin(["U", "AU"])
    return (sdp > 0) | ((surf >= params.c_surface_min_m2) & en_u_au)


def assign_tiers(df: pd.DataFrame, params: TierParams,
                 prev_tier: pd.Series | None = None) -> pd.Series:
    """Attribue le tier par parcelle.

    Colonnes requises : rang (hors copro, NaN pour copro/écartée), copro (bool),
    ecartee_etage0 (bool), sdp_residuelle_m2, surface_m2, zone_plu, p (proba),
    contrib_d, event_age_mois (NaN si aucun événement daté).
    prev_tier : tiers du run précédent, index aligné sur df.index (hystérésis) ;
    None = premier run (pas d'hystérésis, entrée stricte à n_entree).
    """
    rang = pd.to_numeric(df["rang"], errors="coerce")
    event_age = pd.to_numeric(df["event_age_mois"], errors="coerce")
    c_ok = plancher_c(df, params)
    was_hot = (prev_tier.isin([TIER_CHAUDE, TIER_BRULANTE])
               if prev_tier is not None else pd.Series(False, index=df.index))
    event_recent = event_age <= params.event_bypass_mois

    # ---- chaude (copro exclue par construction : rang NaN) --------------------
    entree = rang <= params.n_entree
    maintien = was_hot & (rang <= params.n_sortie)
    bypass = event_recent & (rang <= params.n_sortie)
    chaude = (entree | maintien | bypass) & c_ok & ~df["copro"] & ~df["ecartee_etage0"]

    # ---- brûlante : doctrine « un contexte seul ne franchit jamais un seuil » --
    contrib_d = pd.to_numeric(df["contrib_d"], errors="coerce").fillna(-np.inf)
    event_brulante = event_age <= params.brulante_event_mois
    brulante = chaude & (contrib_d >= params.brulante_seuil_d) & (
        event_brulante.fillna(False) | (contrib_d >= params.brulante_top_decile_d))

    # ---- réserve foncière : top décile C ∧ P sous la médiane -------------------
    sdp = pd.to_numeric(df["sdp_residuelle_m2"], errors="coerce").fillna(0)
    sdp_pos = sdp[sdp > 0]
    seuil_c = float(sdp_pos.quantile(0.9)) if len(sdp_pos) else np.inf
    p = pd.to_numeric(df["p"], errors="coerce")
    reserve = (sdp >= seuil_c) & (p < p.median()) & ~df["ecartee_etage0"] & ~chaude

    tier = pd.Series(TIER_A_CREUSER, index=df.index)
    tier[reserve] = TIER_RESERVE
    tier[chaude] = TIER_CHAUDE
    tier[brulante] = TIER_BRULANTE
    tier[df["ecartee_etage0"]] = TIER_ECARTEE
    return tier


def calibre_brulante(chaude_df: pd.DataFrame, params: TierParams,
                     effectif_min: int = 30, effectif_max: int = 120) -> TierParams:
    """Calibrage MÉCANIQUE du seuil de contribution D (mandat 3.1, comme M1) :
    seuil = plus petit quantile de contrib_D (parmi les chaudes) qui ramène
    l'effectif brûlante dans [30, 120]. top_decile_d = quantile 0,9 des chaudes.
    """
    d = pd.to_numeric(chaude_df["contrib_d"], errors="coerce").dropna()
    event_ok = pd.to_numeric(chaude_df["event_age_mois"], errors="coerce") \
        <= params.brulante_event_mois
    top_dec = float(d.quantile(0.9)) if len(d) else 0.0
    for q in np.arange(0.0, 1.0, 0.025):
        seuil = float(d.quantile(q)) if len(d) else 0.0
        eligibles = (d >= seuil) & (event_ok.reindex(d.index, fill_value=False)
                                    | (d >= top_dec))
        if eligibles.sum() <= effectif_max:
            if eligibles.sum() < effectif_min:
                # garde-fou bas : on retient le quantile précédent même si > max
                break
            return TierParams(**{**params.__dict__,
                                 "brulante_seuil_d": seuil,
                                 "brulante_top_decile_d": top_dec})
    return TierParams(**{**params.__dict__,
                         "brulante_seuil_d": float(d.quantile(0.5)) if len(d) else 0.0,
                         "brulante_top_decile_d": top_dec})


def calibre_n_entree(rangs_c_ok: pd.Series, cible: int = 1150) -> int:
    """n_entree tel que |{rang ≤ n_entree ∧ plancher C}| ≈ cible (continuité
    produit ~1 100-1 200). rangs_c_ok = rangs hors copro des parcelles passant
    le plancher C, triés croissants."""
    r = rangs_c_ok.dropna().sort_values().to_numpy()
    if len(r) <= cible:
        return int(r[-1]) if len(r) else cible
    return int(r[cible - 1])
