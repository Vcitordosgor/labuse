"""EXPORTS-2 — formatage des grandeurs à la française (espace fine insécable comme séparateur de
milliers, virgule décimale), partagé par les blocs. De la mise en forme : aucun calcul.
"""
from __future__ import annotations

_FINE = " "      # espace fine insécable (séparateur de milliers)


def groupe(n: float | int, decimales: int = 0) -> str:
    """Nombre groupé par milliers, virgule décimale. 1234.5 → « 1 234,5 »."""
    s = f"{float(n):,.{decimales}f}"
    return s.replace(",", _FINE).replace(".", ",")


def fmt_m2(v) -> str:
    return f"{groupe(round(float(v)))}{_FINE}m²"


def fmt_eur(v) -> str:
    return f"{groupe(round(float(v)))}{_FINE}€"


def fmt_eur_m2(v) -> str:
    return f"{groupe(round(float(v)))}{_FINE}€/m²"


def fmt_pct(v, decimales: int = 1) -> str:
    return f"{groupe(float(v), decimales)}{_FINE}%"


def fmt_m(v, decimales: int = 1) -> str:
    return f"{groupe(float(v), decimales)}{_FINE}m"
