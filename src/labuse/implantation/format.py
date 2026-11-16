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


def m2_borne_fr(v, bornes=()) -> str:
    """ETUDE-STATIONNEMENT-FIX-9 (point 3) — surface en m², mais PRÈS D'UNE BORNE (seuil de barème) on montre
    assez de décimales pour que la position par rapport au seuil se LISE : 29,999 ne s'affiche plus « 30 m² »
    (qui masquerait le côté du seuil) mais « 29,999 m² ». Même quantification (millième) que la détection."""
    if v is None:
        return "—"
    import math
    vq = math.floor(float(v) * 1000.0 + 1e-6) / 1000.0
    # proche d'une borne ET l'arrondi entier franchirait le seuil (le masquerait) → afficher les décimales
    if any(abs(vq - float(b)) < 0.5 and round(vq) != vq for b in (bornes or ())):
        s = f"{vq:.3f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{s}{ESP}m²"
    return m2_fr(v)
