"""EXPORTS-2 lot 1.1 — LA COLLECTE : le SEUL endroit qui touche la donnée (moteurs, SQL, ou la
fiche déjà assemblée — point d'appel unique). Elle produit {id → Valeur} pour un IDU ; les blocs
ne reçoivent QUE ces Valeur et n'ont ni calcul ni requête.

Chaque id a un COLLECTEUR `(db, idu, fiche) → valeur brute | None`. `None` = la donnée n'est pas
servie (l'id n'entre pas dans la map ; le bloc imprimera « non chiffré » ou omettra la ligne).
Réutiliser la fiche `/parcels/{idu}` garantit « écran = PDF » (recette point 2) pour les données
qui y vivent ; les collecteurs du bilan (lot 5) appelleront le moteur avec les saisies du projet.
"""
from __future__ import annotations

from typing import Any, Callable

from ..registre.valeur import Valeur, valeurs_pour

#: registre des collecteurs : id → (db, idu, fiche) → valeur brute | None.
COLLECTEURS: dict[str, Callable[[Any, str, dict], Any]] = {}


def collecteur(*ids: str):
    """Décore une fonction collecteur et l'enregistre pour un ou plusieurs ids."""
    def deco(fn: Callable[[Any, str, dict], Any]):
        for cid in ids:
            COLLECTEURS[cid] = fn
        return fn
    return deco


def collecte(db, idu: str, ids: list[str], *, fiche: dict | None = None) -> dict[str, Valeur]:
    """Assemble {id → Valeur} pour les ids demandés qui ont un collecteur et une valeur servie."""
    f = fiche or {}
    brut: dict[str, Any] = {}
    for cid in ids:
        fn = COLLECTEURS.get(cid)
        if fn is None:
            continue
        val = fn(db, idu, f)
        if val is not None:
            brut[cid] = val
    return valeurs_pour(db, brut)


# ── collecteurs — section 1 (Identité) : lecture de la fiche (point d'appel unique) ──────────

@collecteur("surface_parcelle_m2")
def _c_surface(db, idu, fiche):
    s = fiche.get("surface_m2")
    return round(float(s)) if s is not None else None


@collecteur("adresse_ban")
def _c_adresse(db, idu, fiche):
    return fiche.get("adresse") or None


@collecteur("type_proprietaire")
def _c_type_proprietaire(db, idu, fiche):
    pm = fiche.get("proprietaire_moral")
    if pm in (None, "", False):
        return None
    if isinstance(pm, dict):
        return "Personne morale"
    return "Personne morale" if pm else "Personne physique"
