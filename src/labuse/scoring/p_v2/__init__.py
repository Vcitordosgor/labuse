"""Scoring v2 produit (M5) — P (modèle M3.6 gelé) × C (capacité PLU existante).

Surface produit du modèle P promu en M3.6. Ce paquet IMPORTE p_model sans jamais
le modifier ; aucun ré-entraînement, aucun re-binning : l'artifact gelé
(reports/m36-foncier/artifacts-m36-scoring2026.joblib, sha256 au manifeste
FREEZE-scoring2026.json) seul fait foi.

Décisions produit gravées (mandat M5) :
- jamais de probabilité brute affichée : « ×N vs moyenne » + percentile + rang
  (p_raw stocké, non montré par défaut — saturation isotonique en tête) ;
- univers produit par défaut HORS copro (badge + toggle, jamais dans le ranking) ;
- « à surveiller » → « réserve foncière » (C fort, P faible), vitrine capacité,
  jamais présentée comme pipeline ;
- une brûlante exige une contribution non-zone minimale ; un événement daté
  prime (bypass d'hystérésis à l'entrée).
"""

SEED = 974
MODEL_ARTIFACT = "reports/m36-foncier/artifacts-m36-scoring2026.joblib"
MODEL_FREEZE = "reports/m36-foncier/FREEZE-scoring2026.json"
MODEL_VERSION = "m36-l2f-2026"

__all__ = ["SEED", "MODEL_ARTIFACT", "MODEL_FREEZE", "MODEL_VERSION"]
