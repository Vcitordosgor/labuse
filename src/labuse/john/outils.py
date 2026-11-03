"""JOHN-TAYLOR-1 — les OUTILS DE LECTURE exposés au modèle (schémas Anthropic + aiguillage).

Le modèle ne reçoit JAMAIS de SQL ni de shell : il choisit un outil dans cette liste fermée, John
exécute la lecture (déterministe, 100 % lecture seule, cf. `contexte.py`) et lui rend le JSON. C'est
le socle de l'anti-invention : toute affirmation de John doit s'appuyer sur un résultat d'outil réel.

`TOOLS` = les définitions passées à `client.messages.create(tools=…)`. `dispatch(db, nom, entree)`
exécute l'outil nommé et rend un dict JSON-sérialisable (jamais une exception non rattrapée).
"""
from __future__ import annotations

from typing import Any

from . import carnet, contexte

#: Les outils de LECTURE. `name` == la clé d'aiguillage ; `input_schema` minimal (la plupart sans arg).
TOOLS: list[dict] = [
    {"name": "lire_jobs",
     "description": "L'état de tous les jobs planifiés : dernier passage, en échec, en retard, bloqué.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_job",
     "description": "L'historique récent d'UN job précis (par son nom technique, ex. 'backup-postgres').",
     "input_schema": {"type": "object", "properties": {"nom": {"type": "string"}}, "required": ["nom"]}},
    {"name": "lire_incidents",
     "description": "Les incidents ouverts et ceux rentrés dans l'ordre depuis 26 h.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_sources",
     "description": "Toutes les sources de données : statut, millésime servi, fraîcheur, veille (version "
                    "amont vue), classe A/B. Dit lesquelles ont une nouvelle version ou une veille en panne.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_runs",
     "description": "Le run servi aux clients, le précédent, les trois pointeurs et leur cohérence, le "
                    "candidat calculé non encore promu.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_controles",
     "description": "Le dernier passage de la suite de cohérence (le banc) : écarts, faux-client, "
                    "lecteurs en erreur, écarts tolérés, et s'il est vert.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_sauvegardes",
     "description": "Le dernier dump (nom, taille, âge) et la copie hors-VPS (marqueur de copie externe).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_radar",
     "description": "La dernière passe Radar (pige) : quand, combien de pages, et si le Radar est muet.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_journaux",
     "description": "Les derniers jobs en échec avec leur message d'erreur + l'état du fournisseur IA.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_carnet",
     "description": "Le carnet de bord : décisions de Vic, incidents passés avec cause et correction, "
                    "doctrines (classes A/B, rien d'inventé).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_rapports",
     "description": "La liste des comptes-rendus des mandats récents (titre + chemin).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "lire_rapport",
     "description": "Le texte d'un rapport précis du dépôt (chemin relatif en .md sous docs/… ou reports/…).",
     "input_schema": {"type": "object", "properties": {"chemin": {"type": "string"}}, "required": ["chemin"]}},
]

#: noms d'outils connus (pour la garde — un nom hors liste est refusé).
NOMS = frozenset(t["name"] for t in TOOLS)


def dispatch(db, nom: str, entree: dict[str, Any] | None) -> dict:
    """Exécute l'outil `nom` avec `entree`. 100 % lecture seule ; jamais d'exception sortante
    (un échec devient un dict `{"erreur": ...}` que le modèle peut lire et expliquer)."""
    entree = entree or {}
    try:
        if nom == "lire_jobs":
            return contexte.jobs_etat(db)
        if nom == "lire_job":
            return contexte.job_detail(db, str(entree.get("nom", "")))
        if nom == "lire_incidents":
            return contexte.incidents(db)
        if nom == "lire_sources":
            return contexte.sources(db)
        if nom == "lire_runs":
            return contexte.runs_etat(db)
        if nom == "lire_controles":
            return contexte.controles(db)
        if nom == "lire_sauvegardes":
            return contexte.sauvegardes(db)
        if nom == "lire_radar":
            return contexte.radar(db)
        if nom == "lire_journaux":
            return contexte.journaux(db)
        if nom == "lire_carnet":
            return {"carnet": carnet.lignes_actives(db)}
        if nom == "lire_rapports":
            return contexte.rapports(db)
        if nom == "lire_rapport":
            return contexte.rapport_texte(db, chemin=str(entree.get("chemin", "")))
    except Exception as exc:  # noqa: BLE001 — un outil ne doit jamais tuer la boucle de chat
        return {"erreur": f"{type(exc).__name__}: {exc}"}
    return {"refuse": f"outil inconnu « {nom} » (hors liste de lecture)"}
