"""Constantes partagées."""
from __future__ import annotations

import re

#: User-Agent applicatif — requis par certaines API (Overpass renvoie 406 sinon).
USER_AGENT = "LA-BUSE/0.1 (+pre-qualification fonciere)"

# ── M103 P2 — LE pliage texte de la recherche (un critère, un endroit) ─────────────────────────
# `unaccent` n'est pas installé ; le pliage casse+accents se fait par lower(translate()). Doctrine
# M99-B (cas NDé) : LA MÊME fonction s'applique au PARAMÈTRE et à la COLONNE — jamais un pliage
# applicatif d'un côté et SQL de l'autre. Consommé par l'autocomplétion d'adresses (app.py) et la
# recherche propriétaire (modules.py — colonne MAJIC 100 % désaccentuée : sans ce pliage, toute
# saisie accentuée rendait 0 en silence, défaut M100 n°3). Table 1:1 (translate = char→char).
# M103 P6 — table COMPLÉTÉE après inventaire exhaustif des données (voies + dénominations) :
# ó (présent dans les voies), ÿ (défensif — noms propres), et l'APOSTROPHE TYPOGRAPHIQUE ’
# pliée sur ' (« l’Étang » tapé « l'Etang » ne matchait pas). Les LIGATURES œ/æ sont des
# digraphes — translate() ne mappe que char→char, elles passent par replace() dans sql_plie().
RECHERCHE_ACCENTS = ("àâäéèêëïîôöùûüçóÿ’ÀÂÄÉÈÊËÏÎÔÖÙÛÜÇÓŸ", "aaaeeeeiioouuucoy'AAAEEEEIIOOUUUCOY")


def sql_plie(expr: str) -> str:
    """Expression SQL du pliage (casse + accents + ligatures) à appliquer À L'IDENTIQUE aux deux
    côtés d'une comparaison. Requiert les binds de `params_pliage()`."""
    ligatures = expr
    for a, b in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE")):
        ligatures = f"replace({ligatures}, '{a}', '{b}')"
    return f"lower(translate({ligatures}, :fold_a, :fold_b))"


def params_pliage() -> dict:
    """Binds du pliage (:fold_a/:fold_b) — à joindre aux paramètres de la requête."""
    a, b = RECHERCHE_ACCENTS
    return {"fold_a": a, "fold_b": b}


# ── RETOURS-16 V5 — le MÊME pliage, en variantes indexables ────────────────────────────────────
def sql_plie_lit(expr: str) -> str:
    """Pliage avec les tables de translittération EN LITTÉRAL (pas de bind) : la MÊME expression
    sert à l'index GIN trigram (un index d'expression n'accepte pas de bind) et à la requête du
    suggest — le planneur ne matche l'index que si les deux expressions sont identiques."""
    ligatures = expr
    for a, b in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE")):
        ligatures = f"replace({ligatures}, '{a}', '{b}')"
    a, b = (s.replace("'", "''") for s in RECHERCHE_ACCENTS)
    return f"lower(translate({ligatures}, '{a}', '{b}'))"


def plie(s: str) -> str:
    """Miroir PYTHON de sql_plie — plier l'AIGUILLE côté application quand la colonne est déjà
    pliée par l'expression indexée (doctrine M99-B : même pliage des deux côtés, un seul dessin)."""
    for a, b in (("œ", "oe"), ("Œ", "OE"), ("æ", "ae"), ("Æ", "AE")):
        s = s.replace(a, b)
    return s.translate(str.maketrans(*RECHERCHE_ACCENTS)).lower()


# ── PERMIS-CHECK-1 P3 — adresse COLLÉE depuis une fiche ─────────────────────────────────────────
# La barre de recherche ne matchait que « numéro voie » : une adresse recopiée depuis une fiche
# (« 1 bis Chemin de la Citerne, 97417 Saint-Denis ») échouait car le REP (bis/ter) et le suffixe
# CP+commune n'étaient pas dans la colonne cherchée. On élargit le texte cherché à
# numéro+rep+voie+CP+commune (MÊME ORDRE que le libellé de fiche `_fmt_ban`) et on réduit les
# SÉPARATEURS (espaces multiples nés d'un rep vide, virgule, tiret) à une espace simple des DEUX
# côtés — l'adresse collée redevient un sous-texte de la colonne. Fold + réduction = un seul dessin.
ADRESSE_SUGGEST_EXPR = (
    "coalesce(numero,'') || ' ' || coalesce(rep,'') || ' ' || voie || ' ' || "
    "coalesce(code_postal,'') || ' ' || coalesce(commune,'')")

_SEPARATEURS = re.compile(r"[\s,\-]+")


def sql_plie_lit_suggest(expr: str) -> str:
    """`sql_plie_lit` + réduction des séparateurs [espace, virgule, tiret]+ → une espace, trimé.
    Expression LITTÉRALE : sert À L'IDENTIQUE à l'index GIN trigram étendu ET à la requête suggest
    (le planneur ne matche l'index d'expression que si les deux sont mot pour mot identiques)."""
    return f"btrim(regexp_replace({sql_plie_lit(expr)}, '[[:space:],-]+', ' ', 'g'))"


def plie_suggest(s: str) -> str:
    """Miroir PYTHON de `sql_plie_lit_suggest` pour l'aiguille : `plie` + séparateurs [espace,
    virgule, tiret]+ réduits à une espace, trimé — même dessin que la colonne étendue normalisée."""
    return _SEPARATEURS.sub(" ", plie(s)).strip()
