"""Constantes partagées."""
from __future__ import annotations

#: User-Agent applicatif — requis par certaines API (Overpass renvoie 406 sinon).
USER_AGENT = "LA-BUSE/0.1 (+pre-qualification fonciere)"

# ── M103 P2 — LE pliage texte de la recherche (un critère, un endroit) ─────────────────────────
# `unaccent` n'est pas installé ; le pliage casse+accents se fait par lower(translate()). Doctrine
# M99-B (cas NDé) : LA MÊME fonction s'applique au PARAMÈTRE et à la COLONNE — jamais un pliage
# applicatif d'un côté et SQL de l'autre. Consommé par l'autocomplétion d'adresses (app.py) et la
# recherche propriétaire (modules.py — colonne MAJIC 100 % désaccentuée : sans ce pliage, toute
# saisie accentuée rendait 0 en silence, défaut M100 n°3). Table 1:1 (translate = char→char).
RECHERCHE_ACCENTS = ("àâäéèêëïîôöùûüçÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ", "aaaeeeeiioouuucAAAEEEEIIOOUUUC")


def sql_plie(expr: str) -> str:
    """Expression SQL du pliage (casse + accents) à appliquer À L'IDENTIQUE aux deux côtés d'une
    comparaison. Requiert les binds de `params_pliage()`."""
    return f"lower(translate({expr}, :fold_a, :fold_b))"


def params_pliage() -> dict:
    """Binds du pliage (:fold_a/:fold_b) — à joindre aux paramètres de la requête."""
    a, b = RECHERCHE_ACCENTS
    return {"fold_a": a, "fold_b": b}
