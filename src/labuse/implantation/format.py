"""Format des nombres de l'Étude — LE helper UNIQUE côté Python (planche + PDF), miroir de
`frontend/src/lib/format.ts` côté écran. Convention FR : virgule décimale, espace INSÉCABLE pour les
milliers et avant l'unité. « 1 746 » · « 13,00 » · « 0,57 » · « 1 746 m² ».

L'espace insécable (U+00A0) est RETIRÉ par le crible de provenance du PDF (`_canon` strippe
\\s/\\u00a0/\\u202f) : la vérification « toute ligne du PDF est une ligne de l'outil » reste valide.
"""
from __future__ import annotations

ESP = " "   # espace insécable (milliers + avant l'unité)


def groupe_fr(v) -> str:
    """Entier, milliers en espace insécable. None → « — »."""
    if v is None:
        return "—"
    return f"{int(round(float(v))):,}".replace(",", ESP)


def dec_fr(v, p: int = 2) -> str:
    """Décimal à p décimales FIXES, virgule, milliers insécables. « 13,00 » (p=2), « 0,57 »."""
    if v is None:
        return "—"
    s = f"{float(v):,.{p}f}"                       # ex. 1 746.00 → '1,746.00'
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ESP)


def dec_souple(v, p: int = 1) -> str:
    """Décimal à AU PLUS p décimales, sans zéro inutile : 2.5→« 2,5 », 5.0→« 5 » (milliers insécables)."""
    if v is None:
        return "—"
    s = f"{float(v):,.{p}f}".replace(",", "\x00")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s.replace(".", ",").replace("\x00", ESP)


def m2_fr(v) -> str:
    """Surface entière en m², unité collée par une insécable. None → « — »."""
    return "—" if v is None else f"{groupe_fr(v)}{ESP}m²"
