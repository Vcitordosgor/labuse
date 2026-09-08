"""EXPORTS-2 — aides de ligne partagées par les blocs. Une ligne dont la Valeur est absente est
OMISE (aucun ◌, aucune valeur d'exemple — décision Vic lot 2). Chaque ligne servie porte la
pastille de nature de son id.
"""
from __future__ import annotations

from typing import Callable

from ..registre.valeur import Valeur
from .nature import chip
from .pieds import pied_section
from .rendu import ligne_kv


def val(valeurs: dict[str, Valeur], cid: str):
    v = valeurs.get(cid)
    return v.valeur if v is not None else None


def a(valeurs: dict[str, Valeur], cid: str) -> bool:
    """L'id est-il servi (Valeur présente et non vide) ?"""
    v = valeurs.get(cid)
    return v is not None and v.valeur not in (None, "")


def ligne(valeurs: dict[str, Valeur], cle: str, cid: str,
          rendu_fn: Callable = str, *, derive: bool = False) -> str:
    """Une ligne clé/valeur/nature, ou '' si l'id n'est pas servi (omise)."""
    if not a(valeurs, cid):
        return ""
    return ligne_kv(cle, rendu_fn(valeurs[cid].valeur), chip(valeurs[cid], derive=derive))


def pied(valeurs: dict[str, Valeur], ids) -> str:
    """Pied de section depuis les réservoirs des ids RÉELLEMENT servis dans ce bloc."""
    return pied_section([valeurs[c] for c in ids if c in valeurs])
