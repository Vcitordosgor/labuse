"""FIX-GB-006 — sigles fonciers usuels → fragment de RAISON SOCIALE (telle qu'elle figure dans les
fichiers fonciers DGFiP / MAJIC, qui stockent le nom LÉGAL complet, jamais le sigle).

Le Scan patrimoine cherche sur la dénomination. Sans cette table, taper « SHLMR » (comme tout le monde
nomme le bailleur) renvoyait 0 alors que l'entité détient des milliers de parcelles sous
« SOCIETE ANONYME D'HABITATIONS A LOYER MODERE DE LA REUNION ». On étend donc la recherche à l'expansion
du sigle quand la saisie EST un sigle connu.

EXTENSIBLE : ajouter une entrée `SIGLE: "FRAGMENT"` suffit — aucune migration, aucun `if` codé en dur.
Chaque fragment ci-dessous a été vérifié : il matche exactement 1 siren dans `parcelle_personne_morale`.
"""
from __future__ import annotations

SIGLES_FONCIERS: dict[str, str] = {
    "SHLMR": "HABITATIONS A LOYER MODERE",                    # SA d'HLM de La Réunion
    "SAFER": "AMENAGEMENT FONCIER ET D'ETABLISSEMENT RURAL",  # Société d'aménagement foncier rural
    "SEDRE": "EQUIPEMENT DU DEPARTEMENT DE LA REUNION",       # Société d'équipement du département
}


def expand_sigle(q: str) -> str | None:
    """Si `q` (nettoyé : alphanumérique, majuscules) EST un sigle foncier connu, renvoie le fragment de
    raison sociale à chercher en plus ; sinon None (la recherche normale s'applique inchangée)."""
    key = "".join(ch for ch in q.upper() if ch.isalnum())
    return SIGLES_FONCIERS.get(key)
