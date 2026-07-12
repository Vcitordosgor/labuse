"""Modèle P — probabilité calibrée de mutation L2 (Vente + Vente terrain à bâtir) à 12 mois.

Mandat M3 (Scoring v2, phases 1-2) : blocs Z (zone) + D (dormance parcelle, sans identité).
Le bloc O (propriétaire) attend M2 — il n'est PAS inclus ici.

Module ISOLÉ : ne modifie ni V v1.3, ni Q/A, ni la matrice, ni l'étage 0, ni les snapshots.
Toutes les tables créées sont préfixées `p_model_` (jamais les tables de prod).

Grain : parcelle × année. Observation 2023 (train), 2024 (val), 2025 (test, lu une seule
fois), 2021-2022 = burn-in features. Features au 01/01/Y STRICT (fenêtres se terminant
au 31/12/Y-1) — voir reports/m3-p-model/dictionnaire-features.md pour chaque feature :
source, fenêtre, date de disponibilité.

Interdits comme features : statut matrice, computed_at, score V (baseline uniquement),
tout calcul daté de 2026 hors couches statiques consignées.
"""

P_MODEL_VERSION = "m3-phase1"
SEED = 974

__all__ = ["P_MODEL_VERSION", "SEED"]
