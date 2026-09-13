"""CIRCUIT-6 lot 0 — vocabulaires d'affichage RATTACHÉS (un littéral, un endroit).

Règle mère : tout ce qui s'affiche à un client vient du registre ou casse la CI.
Ce module porte les libellés qui vivaient en dur au milieu du code (inventaire
CONTOURNEMENTS.md) : chaque consommateur les IMPORTE d'ici, et un test de parité
(tests/verrous/test_lot0_contournements.py) casse si un littéral réapparaît ailleurs.

Même doctrine que scoring/tiers_client.py (paliers) : un point de vérité, des miroirs testés.
"""
from __future__ import annotations

#: Libellés de fiabilité des sources (manifeste de fiche + page Sources).
#: Clé = data_sources.reliability_level ; valeur = libellé client.
#: « suivie », jamais « vérifiée » (M70 décision 4 : source_checks est vide, rien ne
#: l'adosse — le libellé reste honnête).
FIABILITE_LIBELLES: dict[str, str] = {
    "verifie": "surveillée",
    "estime": "estimée",
    "declaratif": "déclarative",
    "a_confirmer": "à confirmer",
}

#: Les trois scénarios du bloc « Potentiel constructible » (fiche, PDF exports).
#: Ordre d'affichage garanti. Les fonctions de rendu (exports/blocs/potentiel.py)
#: n'écrivent plus ces libellés en littéral.
SCENARIO_AU_SOL = "Au sol, bâti conservé"
SCENARIO_EN_HAUTEUR = "En hauteur, bâti conservé"
SCENARIO_RECONSTRUCTION = "Reconstruction après démolition"
SCENARIOS_POTENTIEL: tuple[str, ...] = (
    SCENARIO_AU_SOL, SCENARIO_EN_HAUTEUR, SCENARIO_RECONSTRUCTION,
)
