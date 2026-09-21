"""Signal de mutation V2 — restitution client (SCORING-6 lot D).

Le modèle (recette q_v15 = q_v14 moins piscine/pv_candidat, `p_v2/qv15.py`) produit `signal_p` =
P(vente L2-F dans les 12 mois suivant la date du score). Ce module traduit `signal_p` en un
NIVEAU à trois classes aux **seuils ABSOLUS de PALIERS-1** (pas de percentile, pas de quota) :

    fort   : p ≥ 0,20      moyen : 0,10 ≤ p < 0,20      faible : p < 0,10

Ces seuils sont ceux de `config/scoring_client.yaml › paliers` (source unique, déjà décidés et
mesurés — SCORING-RAPPORT §3). Le Signal est SECONDAIRE : il départage à l'intérieur des bandes
du Score (combinaison V3, lot E), il n'ouvre ni ne ferme une bande.
"""
from __future__ import annotations

from ..scoring.p_v2.statuts import PaliersConfig, charger_paliers_config

SIGNAL_VERSION = "signal_v2"          # recette q_v15 ; le run_label porte le millésime du fit

NIVEAU_FORT = "fort"
NIVEAU_MOYEN = "moyen"
NIVEAU_FAIBLE = "faible"


def signal_niveau(p: float | None, cfg: PaliersConfig | None = None) -> str | None:
    """`signal_p` → niveau fort/moyen/faible (seuils absolus PALIERS-1). None si p indéfini."""
    if p is None:
        return None
    try:
        pv = float(p)
    except (TypeError, ValueError):
        return None
    if pv != pv:                        # NaN
        return None
    cfg = cfg or charger_paliers_config()
    if pv >= cfg.entree_priorite:
        return NIVEAU_FORT
    if pv >= cfg.entree_a_suivre:
        return NIVEAU_MOYEN
    return NIVEAU_FAIBLE


def signal_version(recette: str = "q_v15") -> str:
    """Version du Signal, portée dans la sortie (traçabilité) : `signal_v2+<recette>`."""
    return f"{SIGNAL_VERSION}+{recette}"
