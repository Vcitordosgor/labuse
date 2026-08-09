"""M54-AB C7 — conversion UNIQUE de la pente : une seule mesure (RGE ALTI 5 m, parcel_terrain),
servie en degrés ET en pourcentage, avec le même qualificatif, partout (premium, dossier, flash).

Fin du « ~10 % » (relief coarse du scoring) vs « 11,4° » (RGE ALTI) : un seul chiffre client.
"""
from __future__ import annotations

import math


def pente_pct(deg: float) -> int:
    """Degrés → pente en % (tan). 11,4° ≈ 20 %."""
    return round(math.tan(math.radians(deg)) * 100)


def pente_label(pct: float) -> str:
    """Qualificatif client de la pente (accent demandé : « modérée »)."""
    if pct < 10:
        return "faible"
    if pct < 25:
        return "modérée"
    if pct < 40:
        return "forte"
    return "très forte"


def pente_texte(deg: float) -> str:
    """Phrase client complète : « 11,4° ≈ 20 % (modérée) »."""
    p = pente_pct(deg)
    return f"{deg:.1f}".replace(".", ",") + f"° ≈ {p} % ({pente_label(p)})"
