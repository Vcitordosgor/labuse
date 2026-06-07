"""Schéma JSON borné de la sortie de l'agent (brief §9).

On VALIDE toute sortie IA contre ce schéma avant de l'enregistrer dans
parcel_evaluations.ai_payload — garde-fou anti-hallucination structurel.
"""
from __future__ import annotations

from jsonschema import Draft202012Validator

_STATUS = ["opportunite", "a_creuser", "faux_positif_probable", "exclue"]
_SEVERITY = ["faible", "moyen", "fort"]
_CONFIDENCE = ["faible", "moyen", "eleve"]

AI_OUTPUT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "executive_summary", "confirmed_facts", "positive_signals", "blocking_or_risk_signals",
        "false_positive_risks", "missing_data", "must_check_before_showing_developer",
        "recommended_status", "opportunity_score_adjustment", "confidence_level",
    ],
    "properties": {
        "executive_summary": {"type": "string"},
        "data_completeness_comment": {"type": "string"},
        "confirmed_facts": {
            "type": "array",
            "items": {"type": "object", "required": ["fact", "source"],
                       "properties": {"fact": {"type": "string"}, "source": {"type": "string"}},
                       "additionalProperties": False},
        },
        "positive_signals": {
            "type": "array",
            "items": {"type": "object", "required": ["signal", "source"],
                       "properties": {"signal": {"type": "string"}, "source": {"type": "string"}},
                       "additionalProperties": False},
        },
        "blocking_or_risk_signals": {
            "type": "array",
            "items": {"type": "object", "required": ["risk", "severity", "source"],
                       "properties": {"risk": {"type": "string"}, "severity": {"enum": _SEVERITY},
                                       "source": {"type": "string"}},
                       "additionalProperties": False},
        },
        "false_positive_risks": {
            "type": "array",
            "items": {"type": "object", "required": ["risk", "reason"],
                       "properties": {"risk": {"type": "string"}, "reason": {"type": "string"}},
                       "additionalProperties": False},
        },
        "why_land_might_be_empty": {"type": "array", "items": {"type": "string"}},
        "developer_interest_hypothesis": {"type": "string"},
        "possible_project_types": {"type": "array", "items": {"type": "string"}},
        "market_context_summary": {"type": "string"},
        "regulatory_context_summary": {"type": "string"},
        "environmental_risk_summary": {"type": "string"},
        "reunion_specific_flags": {"type": "array", "items": {"type": "string"}},
        "missing_data": {"type": "array", "items": {"type": "string"}},
        "must_check_before_showing_developer": {"type": "array", "items": {"type": "string"}},
        "recommended_status": {"enum": _STATUS},
        "opportunity_score_adjustment": {"type": "integer", "minimum": -20, "maximum": 20},
        "confidence_level": {"enum": _CONFIDENCE},
        "developer_pitch": {"type": "string"},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
}

_validator = Draft202012Validator(AI_OUTPUT_SCHEMA)


def validate_ai_output(payload: dict) -> list[str]:
    """Renvoie la liste des erreurs (vide = valide)."""
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in _validator.iter_errors(payload)]
