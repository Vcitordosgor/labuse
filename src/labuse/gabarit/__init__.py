"""Gabarit réglementaire — moteur pur + validation + raccordement.

Flux imposé (CDC) : SOURCE → VALIDATION → CALCUL → AFFICHAGE. Jamais
SUPPOSITION → ESTIMATION. Le moteur ne fait QUE traduire graphiquement et
mathématiquement des données réglementaires sourcées et vérifiées.

- `contract`  : modèles pydantic (contrat d'entrée/sortie unique, CDC §2).
- `validate`  : validation stricte AVANT tout calcul (CDC §3).
- `engine`    : moteur géospatial pur et déterministe (CDC §4).
- `builder`   : LE point de raccordement unique des vraies données (cadastre,
                PLU, PPR, multi-zones). Le moteur ne distingue jamais réel/fictif.

Le contrat est identique pour les fixtures et pour le réel : brancher les vraies
données ne demande aucune réécriture du moteur, de la carte, du panneau ou de la 3D.
"""
from .contract import (
    ApplicableRule,
    Coverage,
    Exclusion,
    GabaritInput,
    GabaritResult,
    MaxFootprint,
    MaxHeight,
    ParcelInput,
    RegulatorySource,
    Setback,
)
from .engine import INCOMPLETE_MESSAGE, compute_gabarit
from .validate import GabaritValidationError, validate_input

__all__ = [
    "ApplicableRule",
    "Coverage",
    "Exclusion",
    "GabaritInput",
    "GabaritResult",
    "MaxFootprint",
    "MaxHeight",
    "ParcelInput",
    "RegulatorySource",
    "Setback",
    "compute_gabarit",
    "INCOMPLETE_MESSAGE",
    "validate_input",
    "GabaritValidationError",
]
