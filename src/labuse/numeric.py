"""Petits utilitaires numériques partagés (factorisation — safe-bugfix #11)."""
from __future__ import annotations


def clamp(x: float, lo: float, hi: float) -> float:
    """Borne `x` dans l'intervalle [lo, hi]."""
    return max(lo, min(hi, x))
