"""M26-A · COPILOTE — socle agentique (event log + interpréteur + plans + exécuteur).

Règle absolue du mandat : le LLM ne calcule JAMAIS rien. Il n'intervient qu'à
l'interprétation du besoin (brief structuré, `interpreteur.py`). Tout chiffre servi
provient d'un moteur déterministe existant, appelé via un wrapper fin (`moteurs.py`)
qui journalise dans l'event log (`events.py`) — source de vérité unique du dossier.

Pattern : workflow déterministe avec LLM aux extrémités (12-Factor Agents),
PAS de boucle agentique libre. Les plans sont codés en dur (`plans.py`).
"""
