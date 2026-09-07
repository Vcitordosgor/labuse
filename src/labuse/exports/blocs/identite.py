"""EXPORTS-2 — bloc « 1. Identité et situation ». Exemplaire du lot 1 : il ne lit QUE des Valeur
du registre, pose la pastille de nature de chacune, et son pied de section vient des réservoirs
lus. Aucun calcul, aucune requête. Une donnée non servie s'imprime « non chiffré » (jamais un zéro,
jamais un défaut silencieux). Le lot 2 complètera cette section (forme, propriétaire nominatif,
historique, contiguës) ; le lot 1 en pose la mécanique.
"""
from __future__ import annotations

from ..nature import chip
from ..pieds import pied_section
from ..registre_fmt import fmt_m2
from ..rendu import ligne_kv, section, table_kv
from ...registre.valeur import Valeur

#: les ids que ce bloc lit (union déclarée : sert la collecte et le pied).
IDS = ("surface_parcelle_m2", "adresse_ban", "type_proprietaire")

_NON_CHIFFRE = '<span class="none">non chiffré</span>'


def _ligne(valeurs: dict[str, Valeur], cle: str, cid: str, rendu_valeur) -> str:
    """Une ligne : la Valeur si servie (avec sa pastille), sinon « non chiffré » (sans pastille —
    aucun chiffre imprimé sans id du registre)."""
    v = valeurs.get(cid)
    if v is None or v.valeur in (None, ""):
        return ligne_kv(cle, _NON_CHIFFRE, "")
    return ligne_kv(cle, rendu_valeur(v.valeur), chip(v))


def rendu(valeurs: dict[str, Valeur]) -> str:
    lignes = [
        _ligne(valeurs, "Contenance cadastrale", "surface_parcelle_m2", fmt_m2),
        _ligne(valeurs, "Adresse", "adresse_ban", lambda a: str(a)),
        _ligne(valeurs, "Propriétaire", "type_proprietaire", lambda t: str(t)),
    ]
    lus = [valeurs[c] for c in IDS if c in valeurs]
    return section("1. Identité et situation", table_kv(lignes) + pied_section(lus))
