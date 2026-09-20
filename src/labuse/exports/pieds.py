"""EXPORTS-2 lot 1.5 — LES PIEDS DE SECTION, générés depuis les réservoirs des ids EFFECTIVEMENT
lus (mécanisme EXPORTS-1 lot 6.1, généralisé). On ne liste jamais une source qu'on n'a pas servie :
le pied est la réunion des réservoirs des Valeur du bloc, avec leur millésime quand il est connu.

Le nom affiché d'un réservoir vient de `reservoirs.csv` (nom_affiche) — le catalogue du Circuit.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from ..registre.valeur import Valeur

_RESERVOIRS_CSV = Path(__file__).resolve().parents[3] / "docs" / "CIRCUIT" / "inventaire" / "reservoirs.csv"


@lru_cache(maxsize=1)
def _noms_reservoirs() -> dict[str, str]:
    """id de réservoir → nom affiché (reservoirs.csv). Repli : l'id lui-même si le csv manque."""
    out: dict[str, str] = {}
    if _RESERVOIRS_CSV.exists():
        with _RESERVOIRS_CSV.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter=";"):
                rid = (row.get("id") or "").strip()
                if rid:
                    out[rid] = (row.get("nom_affiche") or rid).strip()
    return out


#: RECETTE-11 D6 — réservoirs enregistrés mais absents de reservoirs.csv : sans nom affiché, leur
#: id technique (« rpls_sdes ») fuyait au client dans le pied « Sources : … ». On donne le nom public.
_NOMS_REPLI = {"rpls_sdes": "RPLS — logements locatifs sociaux (SDES)",
               # EXPORTS-REBRANCHEMENT-1 lot 1 — réservoirs du miroir sans nom au catalogue.
               "rnb": "RNB — Référentiel national des bâtiments (IGN)",
               "ban_plus": "BAN PLUS — liens adresse-bâtiment (IGN)",
               "taxe_amenagement": "Taxe d'aménagement — barème public (DGFiP/DELTA)"}


def sources_lues(valeurs: Iterable[Valeur]) -> list[tuple[str, str | None]]:
    """Les réservoirs (nom affiché, millésime) réunis des Valeur données, dans l'ordre de première
    apparition, sans doublon — vide si aucun id lu ne porte de réservoir."""
    noms = _noms_reservoirs()
    vus: dict[str, str | None] = {}
    for v in valeurs:
        for rid, mill in (v.reservoirs or {}).items():
            if rid not in vus:
                vus[rid] = mill
    return [(noms.get(rid) or _NOMS_REPLI.get(rid, rid), mill) for rid, mill in vus.items()]


def pied_section(valeurs: Iterable[Valeur]) -> str:
    """Le fragment HTML du pied d'une section : « Sources : Nom · Nom · … » — noms seuls.
    Rien (chaîne vide) si aucune source n'est en jeu (bloc purement interne)."""
    sources = sources_lues(valeurs)
    if not sources:
        return ""
    # EXPORTS-REBRANCHEMENT-1 lot 2 — NOMS seuls, aucun millésime ni date côté client
    # (doctrine PAGE-SOURCES-1 18/09) ; le millésime reste lisible côté admin (Circuit, trace=1).
    parts = [nom for nom, _mill in sources]
    from .rendu import note
    return note("Sources : " + " · ".join(parts))
