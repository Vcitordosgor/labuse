"""M87 P0 — définition CANONIQUE des sources AFFICHÉES sur la page Sources & fraîcheur.

UN critère, UN endroit : le compteur d'accueil (`accueil.py`) ET la liste `/sources` lisent d'ici.
Exclusions de l'AFFICHAGE (l'ingestion et les tables restent, seul l'écran change) :
  · les DOUBLON de catalogue (même donnée qu'une ligne canonique — M71) ;
  · les sources MASQUÉES : mortes à l'affichage (arbitrage M86/M87). Office de l'eau (Chroniques) —
    lue uniquement par un contrôle QA (`/signals` retiré) — sort de la page ; sa dette reste ouverte.
"""
from __future__ import annotations

#: sources retirées de l'AFFICHAGE (jamais de l'ingestion) — arbitrage M87 P0.
SOURCES_MASQUEES: frozenset[str] = frozenset({
    "Office de l'eau Réunion — Chroniques de l'eau",
})

#: fragment SQL commun : connecte, hors DOUBLON, hors masquées. `:masquees` lié par l'appelant.
WHERE_AFFICHEES = ("status = 'connecte' AND COALESCE(technical_notes, '') NOT LIKE 'DOUBLON%' "
                   "AND name <> ALL(:masquees)")


def masquees_param() -> list[str]:
    """Valeur à lier à `:masquees` (liste des noms masqués)."""
    return list(SOURCES_MASQUEES)


def est_affichee(name: str, technical_notes: str | None) -> bool:
    """Une source data_sources est-elle AFFICHÉE (filtre Python, même règle que WHERE_AFFICHEES) ?"""
    return not (technical_notes or "").startswith("DOUBLON de") and name not in SOURCES_MASQUEES


#: sources CURÉES MANUELLEMENT (arbitrage M86/M87) : la table n'est pas lue directement, mais elle est
#: le SQUELETTE d'un registre curaté à la main qui, lui, est servi. Badge dédié (même visuel que proxy).
SOURCES_CUREES: frozenset[str] = frozenset({
    "Sudocuh (procédures d'urbanisme)",
})
CUREES_NOTE = ("Table non lue directement : le radar PLU servi lit un registre YAML curaté à la main "
               "(config/veille_plu.yaml) dont Sudocuh est le squelette. Source réelle, indirecte.")
