"""RECETTE-8 W3/W18 — LE vocabulaire des scénarios de projet, un seul endroit.

Un scénario est CITÉ (le Financier, le Dossier, la fiche) par son libellé humain, jamais par son
identifiant technique (« surelevation » sans accent ni majuscule s'imprimait au client — W18). Et
un scénario retenu pour un CHIFFRE est le même dans tous les documents (« un seul scénario par
document » — W3) : le bilan du Financier chiffre une RECONSTRUCTION (il porte sur la SDP créée en
table rase), c'est donc « reconstruction » qui est cité, jamais « surélévation » (qui reste une
OPTION présentée, sans bilan chiffré propre).

Le verrou de provenance étendu aux libellés (W5) vérifie que tout libellé de scénario servi vient
d'ici.
"""
from __future__ import annotations

#: code technique → libellé humain servi au client. LE domaine des scénarios.
SCENARIOS: dict[str, str] = {
    "reconstruction": "Reconstruction (démolition-reconstruction)",
    "surelevation": "Surélévation",
    "revente": "Revente en l'état",
    "division": "Division parcellaire",
}


def libelle_scenario(code: str | None) -> str | None:
    """Le libellé humain d'un scénario, ou None si le code est nul. Un code hors domaine est
    rendu tel quel (le verrou W5 le signalera) plutôt que masqué."""
    if not code:
        return None
    return SCENARIOS.get(str(code).strip().lower(), str(code))


#: l'ensemble des libellés servis (pour le verrou W5).
LIBELLES_SERVIS = frozenset(SCENARIOS.values())
