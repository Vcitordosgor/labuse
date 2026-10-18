"""FIX-PRIX-ET-OPPORTUNITES (lot 1) — fourchette d'incertitude UNIQUE pour toute valeur de parcelle ESTIMÉE.

Suite de VERITE-TERRAIN-2 (volet E, `docs/audit-2026-10/verite-terrain-2/`). Le backtest prix (sans
fuite, coupe 2024, 3 581 ventes DVF) a mesuré ce que vaut une estimation « médiane du secteur ×
surface » face au prix réellement constaté :

  · écart absolu médian estimé ↔ réel : **27,4 %** ;
  · part des ventes à ±10 % : **17,5 %** ; à ±20 % : **36,5 %** ;
  · biais médian signé : **−5,6 %** (estimateur volontairement sobre — majore l'erreur, jamais l'inverse).

Conséquence produit (consignée dans le rapport : « NE PAS vendre la précision du prix ») : aucune
valeur de parcelle estimée ne doit plus s'afficher en **chiffre sec**. Elle s'affiche en **fourchette**
avec une **mention d'incertitude courte et vraie, fondée sur ces chiffres mesurés**.

Demi-largeur retenue : **±30 %**. Choix volontairement **au moins aussi large que l'écart médian
mesuré** (27,4 %) : le backtest porte sur l'estimateur sobre, qui majore l'erreur du vrai produit — la
fourchette est donc **prudente** (elle sur-dit l'incertitude plutôt que de la sous-dire). Le backtest a
été conduit sur le bâti (maison + appartement ; le terrain nu, sous le filtre mono-mutation, n'avait pas
assez de ventes pour un verdict propre) — c'est pourquoi la mention dit « ce type d'estimation » et non
« cette parcelle » : on cite la méthode mesurée, on n'invente pas une validation par bien.

POINT DE CALCUL UNIQUE (Python). Le miroir TypeScript est `frontend/src/lib/fourchette.ts` — les deux
doivent rester synchrones (même demi-largeur, même mention).
"""
from __future__ import annotations

#: demi-largeur de la fourchette d'estimation (±), en fraction. Voir docstring pour la justification.
DEMI_LARGEUR = 0.30
DEMI_LARGEUR_PCT = round(DEMI_LARGEUR * 100)

#: mention d'incertitude complète (survol / détail / PDF / Copilote) — une phrase, chiffres mesurés.
MENTION = (
    f"Estimation indicative, pas une valeur vénale : fourchette ±{DEMI_LARGEUR_PCT} %. Au dernier "
    "backtest (ventes DVF, VERITE-TERRAIN-2), ce type d'estimation s'écarte en médiane de 27 % du "
    "prix réel et seulement 37 % des ventes tombaient à ±20 %."
)
#: mention courte (chip / inline, quand la place manque).
MENTION_COURTE = f"estimation ±{DEMI_LARGEUR_PCT} % (écart médian mesuré 27 %)"


def _eur_fr(n: float | int) -> str:
    """Entier groupé à la française avec « € » collé (espace fine insécable). Repli par défaut."""
    return f"{round(float(n)):,}".replace(",", " ") + " €"


def _pas_arrondi(v: float) -> int:
    """Pas d'arrondi LISIBLE selon l'ordre de grandeur (jamais une borne à l'euro près sur une
    estimation : « 390 000 » dit plus honnêtement l'incertitude que « 398 882 »)."""
    a = abs(v)
    if a >= 1_000_000:
        return 50_000
    if a >= 100_000:
        return 10_000
    if a >= 10_000:
        return 1_000
    if a >= 1_000:
        return 100
    return 50


def _arrondir(v: float, sens: str) -> int:
    """Arrondit une borne à son pas lisible : `bas` vers le bas, `haut` vers le haut → la fourchette
    ENCADRE la valeur (arrondi prudent, jamais resserré)."""
    import math
    pas = _pas_arrondi(v)
    return int((math.floor(v / pas) if sens == "bas" else math.ceil(v / pas)) * pas)


def fourchette(valeur: float | int | None) -> dict | None:
    """Fourchette d'incertitude autour d'une valeur de parcelle estimée (euros).

    Renvoie None si `valeur` est None (on ne fabrique jamais une fourchette sur une absence). Les bornes
    sont ARRONDIES à un pas lisible (bas vers le bas, haut vers le haut — la fourchette encadre la
    valeur, l'arrondi ne resserre jamais). `bas`/`haut` ordonnés même si la valeur est négative.
    """
    if valeur is None:
        return None
    v = float(valeur)
    b1 = _arrondir(v * (1 - DEMI_LARGEUR), "bas")
    b2 = _arrondir(v * (1 + DEMI_LARGEUR), "haut")
    bas, haut = (b1, b2) if b1 <= b2 else (b2, b1)
    return {
        "centre": round(v),
        "bas": bas,
        "haut": haut,
        "demi_largeur_pct": DEMI_LARGEUR_PCT,
        "mention": MENTION,
        "mention_courte": MENTION_COURTE,
    }


def fourchette_libelle(valeur: float | int | None, fmt=None) -> str | None:
    """« 260 000 – 480 000 € » (tiret demi-cadratin). `fmt` = formateur €/surface du contexte (ex.
    `exports.registre_fmt.fmt_eur`) ; par défaut, formatage fr collé au « € »."""
    f = fourchette(valeur)
    if f is None:
        return None
    fmt = fmt or _eur_fr
    return f"{fmt(f['bas'])} – {fmt(f['haut'])}"
