"""M87 P0 — définition CANONIQUE des sources AFFICHÉES sur la page Sources & fraîcheur.

UN critère, UN endroit : le compteur d'accueil (`accueil.py`) ET la liste `/sources` lisent d'ici.
Exclusions de l'AFFICHAGE (l'ingestion et les tables restent, seul l'écran change) :
  · les DOUBLON de catalogue (même donnée qu'une ligne canonique — M71) ;
  · les sources MASQUÉES : mortes à l'affichage. M97 : le mécanisme reste, l'ensemble est VIDE —
    Office de l'eau (masquée M87 comme « QA seul ») est SERVIE à la fiche depuis M95
    (anc_office_eau_commune, Sourcé commune) ; une source servie s'affiche (audit M96 G1).
"""
from __future__ import annotations

#: sources retirées de l'AFFICHAGE (jamais de l'ingestion). Vide depuis M97 (Office de l'eau
#: démasquée — servie via anc_service depuis M95). Le mécanisme reste pour un prochain arbitrage.
SOURCES_MASQUEES: frozenset[str] = frozenset()

#: fragment SQL commun. M123 — CORRECTION du piège des `manuel` : la vitrine ne filtre plus
#: `status='connecte'` STRICT (une source `manuel` CÂBLÉE ET ALIMENTÉE était invisible — cas Fichiers
#: fonciers). Elle affiche désormais `connecte` ∪ `manuel`, et exclut explicitement les DOUBLON, les
#: RETIRÉ (abandon arbitré, raison écrite) et les masquées. Une source retirée/vide porte son tag,
#: elle n'est plus exclue « par son statut » en silence.
WHERE_AFFICHEES = ("status IN ('connecte', 'manuel') "
                   "AND COALESCE(technical_notes, '') NOT LIKE 'DOUBLON%' "
                   "AND COALESCE(technical_notes, '') NOT LIKE 'RETIRÉ%' "
                   "AND name <> ALL(:masquees)")


def masquees_param() -> list[str]:
    """Valeur à lier à `:masquees` (liste des noms masqués)."""
    return list(SOURCES_MASQUEES)


def est_affichee(name: str, technical_notes: str | None) -> bool:
    """Une source data_sources est-elle AFFICHÉE (filtre Python, même règle que WHERE_AFFICHEES) ?"""
    tn = technical_notes or ""
    return not tn.startswith("DOUBLON de") and not tn.startswith("RETIRÉ") and name not in SOURCES_MASQUEES


#: sources CURÉES MANUELLEMENT (arbitrage M86/M87) : la table n'est pas lue directement, mais elle est
#: le SQUELETTE d'un registre curaté à la main qui, lui, est servi. Badge dédié (même visuel que proxy).
SOURCES_CUREES: frozenset[str] = frozenset({
    "Sudocuh (procédures d'urbanisme)",
})
CUREES_NOTE = ("Table non lue directement : le radar PLU servi lit un registre YAML curaté à la main "
               "(config/veille_plu.yaml) dont Sudocuh est le squelette. Source réelle, indirecte.")
