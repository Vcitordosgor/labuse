"""EXPORTS-2 lot 1.3 — LA NATURE DE CHAQUE DONNÉE, dérivée du registre (jamais écrite à la main
dans un gabarit). Quatre natures, quatre pastilles (DA v3) :

  · sourcé  (mint) — vient d'une source publique servie telle quelle (passe-plat/constante) ou
    d'un moteur qui SERT un fait de source (zonage, marché observé, risques, bâti relevé) ;
  · estimé  (gris) — un calcul LABUSE (moteur de calcul : potentiel, bilan, taxe, solaire…) ;
  · dérivé  (gris, ƒ) — déduit d'autres données par une formule affichée par le bloc
    (décision de présentation du bloc, déterministe — pas un chip écrit dans un gabarit) ;
  · projet  (ambre) — saisi par le client (portée `projet`).

La règle est portée + calcul + moteur : `projet` prime, puis passe-plat/constante = sourcé,
puis on distingue les moteurs qui CALCULENT (estimé) des moteurs qui SERVENT une source (sourcé).
"""
from __future__ import annotations

from ..registre.valeur import Valeur

#: classes CSS de theme.css (.chip.s/.e/.d/.p) et le libellé imprimé.
CLASSE = {"source": "s", "estime": "e", "derive": "d", "projet": "p"}
LIBELLE = {"source": "sourcé", "estime": "estimé", "derive": "dérivé", "projet": "projet"}

#: moteurs de CALCUL — leur sortie est un estimé LABUSE (les autres moteurs servent un fait de
#: source : zonage, marché observé, risques, bâti relevé, proximités, compteurs…).
MOTEURS_ESTIMES: frozenset[str] = frozenset({
    "potentiel", "bilan_promoteur", "taxe_amenagement", "solaire", "division_or",
    "score_e", "scoring_p_v2", "renouvellement",
})


def nature_de(v: Valeur) -> str:
    """La nature (`source|estime|derive|projet`) d'une Valeur, du registre seul."""
    from ..registre.donnees import DONNEES
    d = DONNEES.get(v.chiffre_id)
    if d is None:
        return "estime"
    if d.portee == "projet":
        return "projet"
    if d.calcul in ("passe_plat", "constante"):
        return "source"
    if d.calcul == "moteur":
        return "estime" if d.moteur in MOTEURS_ESTIMES else "source"
    return "estime"      # sql_propre / front (ne devrait plus exister) → prudence : estimé


def chip(v: Valeur, *, derive: bool = False) -> str:
    """Le fragment HTML de la pastille de nature d'une Valeur. `derive=True` : le bloc présente
    cette ligne comme une formule visible entre données (nature `dérivé`, décision du bloc)."""
    nat = "derive" if derive else nature_de(v)
    return f'<span class="chip {CLASSE[nat]}">{LIBELLE[nat]}</span>'
