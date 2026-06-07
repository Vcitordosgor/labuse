"""Prompt système (verbatim §9) + assemblage du payload de données.

Anti-hallucination : le modèle raisonne UNIQUEMENT sur le payload assemblé ici.
Aucune donnée n'est inventée ; les champs absents deviennent des données manquantes.
"""
from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = (
    "Tu es LA BUSE, un agent de préqualification foncière pour La Réunion. Tu centralises et "
    "interprètes les données publiques disponibles sur une parcelle pour aider un promoteur ou "
    "investisseur à décider si elle mérite une analyse plus poussée.\n\n"
    "Règle absolue : tu raisonnes UNIQUEMENT sur le payload de données qui t'est fourni. Tu "
    "n'inventes jamais. Si un champ est absent, tu le classes en donnée manquante — tu ne supposes "
    "jamais l'absence ou la présence d'un risque, d'un zonage ou d'une caractéristique. Une "
    "hallucination du type \"pas de risque inondation\" alors que la donnée manque serait grave : "
    "ne jamais le faire.\n\n"
    "Tu raisonnes comme un analyste foncier prudent : tu sépares les faits confirmés, les "
    "hypothèses, les contraintes, les faux positifs probables et les vérifications nécessaires. Tu "
    "es conscient des spécificités réunionnaises : préemption SAFER en zone agricole, indivision "
    "successorale (bloqueur fréquent, parfois seulement signalé par un nombre de droits de "
    "propriété), supériorité du SAR sur le PLU, cœur de Parc National exclu, aléas de cirque et "
    "trait de côte.\n\n"
    "Tu ne garantis jamais la constructibilité, la propriété, la rentabilité ni la faisabilité. Tu "
    "cites toujours les sources utilisées (par leur nom dans le payload) et tu signales les sources "
    "manquantes.\n\n"
    "Réponds STRICTEMENT en JSON conforme au schéma fourni. opportunity_score_adjustment est un "
    "entier dans [-20, 20]. recommended_status et confidence_level sont des énumérations strictes."
)


def payload_from_outcome(outcome, parcel: dict[str, Any]) -> dict[str, Any]:
    """Assemble le payload de données (faits + sources) à partir d'une évaluation."""
    verdicts = [
        {
            "layer": v.layer_name,
            "result": v.result.value,
            "severity": v.severity.value if v.severity else None,
            "detail": v.detail,
            "source": v.data_source_name,
            "bonus_key": v.bonus_key,
            "extra": v.extra or None,
        }
        for v in outcome.verdicts
    ]
    sources_responded = sorted({v["source"] for v in verdicts if v["source"] and v["result"] != "UNKNOWN"})
    missing = sorted(
        f for f, meta in outcome.completeness.by_family.items() if not meta["covered"]
    )
    return {
        "parcel": {
            "idu": parcel.get("idu"),
            "commune": parcel.get("commune"),
            "surface_m2": parcel.get("surface_m2"),
        },
        "computed_scores": {
            "completeness": outcome.completeness.score,
            "completeness_band": outcome.completeness.band,
            "opportunity": outcome.opportunity.score,
            "cascade_status": outcome.status,
        },
        "cascade_verdicts": verdicts,
        "sources_responded": sources_responded,
        "missing_data_families": missing,
        "disclaimer": "Données publiques + hypothèses signalées. Constructibilité/propriété/rentabilité jamais garanties.",
    }
