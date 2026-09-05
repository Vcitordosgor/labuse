"""CIRCUIT-2 lot 1.1 — ALIAS DE COMPATIBILITÉ : `registre/chiffres.py` est devenu
`registre/donnees.py` (le registre couvre toute donnée affichée, pas seulement les nombres).
Ce module réexporte tout — aucun import existant ne casse. Nouvelle écriture : donnees.py.
"""
from __future__ import annotations

from .donnees import (  # noqa: F401
    ALIAS_TRANSITION,
    C,
    CHIFFRES,
    DONNEES,
    Chiffre,
    Donnee,
    TYPES,
    VERSION_DEF,
    resoudre,
)
