"""Providers IA + point d'entrée `analyze`.

- StubProvider : déterministe, hors-ligne, DÉRIVE la sortie du payload (n'invente
  jamais). Permet de faire tourner le pipeline IA sans clé ni réseau.
- AnthropicProvider : prêt à brancher (clé + réseau). Utilise l'API Messages.

Toute sortie est VALIDÉE contre AI_OUTPUT_SCHEMA avant d'être renvoyée.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from ..config import get_settings
from .prompt import SYSTEM_PROMPT
from .schema import validate_ai_output


class AIProvider(Protocol):
    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]: ...


def _confidence_from_band(band: str) -> str:
    return {"forte": "eleve", "moyenne": "moyen", "faible": "faible"}.get(band, "faible")


def _reunion_flags(verdicts: list[dict]) -> list[str]:
    """Spécificités réunionnaises — UNIQUEMENT sur contraintes/exclusions réelles.

    On ignore les verdicts PASS (« Hors Parc National », « Hors SAFER »…) : matcher
    un mot-clé dans un détail négatif produirait un faux signal (interdit, §9).
    """
    flags = []
    for v in verdicts:
        if v.get("result") not in ("SOFT_FLAG", "HARD_EXCLUDE"):
            continue
        d = (v.get("detail") or "").lower()
        if "safer" in d:
            flags.append("Risque de préemption SAFER (zone agricole).")
        if "sar" in d and "supérieur" in d:
            flags.append("SAR juridiquement supérieur au PLU.")
        if "parc national" in d:
            flags.append("Parc National (cœur exclu / adhésion contrainte).")
        if "indivision" in d:
            flags.append("Indivision successorale — bloqueur fréquent.")
        if "trait de côte" in d:
            flags.append("Recul du trait de côte.")
    return sorted(set(flags))


class StubProvider:
    """Sortie déterministe dérivée du payload — RGPD/anti-hallucination safe."""

    name = "stub"

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        verdicts = payload.get("cascade_verdicts", [])
        scores = payload.get("computed_scores", {})
        status = scores.get("cascade_status", "a_creuser")
        band = scores.get("completeness_band", "faible")

        confirmed, positives, risks, false_pos = [], [], [], []
        for v in verdicts:
            src = v.get("source") or "n/d"
            res = v.get("result")
            if res == "POSITIVE":
                positives.append({"signal": v["detail"], "source": src})
                confirmed.append({"fact": v["detail"], "source": src})
            elif res == "SOFT_FLAG":
                risks.append({"risk": v["detail"], "severity": v.get("severity") or "moyen", "source": src})
            elif res == "HARD_EXCLUDE":
                false_pos.append({"risk": v["detail"], "reason": "Couche éliminatoire de la cascade."})
            elif res == "PASS" and v.get("detail"):
                confirmed.append({"fact": v["detail"], "source": src})

        missing = payload.get("missing_data_families", [])
        must_check = []
        if "proprietaire" in missing:
            must_check.append("Confirmer le propriétaire et l'indivision via les Fichiers fonciers (sous convention).")
        if any(v.get("layer") == "zonage_plu_gpu" for v in verdicts):
            must_check.append("Vérifier les règles détaillées au règlement PLU (PDF).")
        must_check.append("Vérifier l'assainissement (collectif/SPANC) auprès de l'EPCI.")

        out = {
            "executive_summary": f"Statut cascade : {status}. Complétude {scores.get('completeness')}/100, "
                                 f"opportunité {scores.get('opportunity')}/100.",
            "data_completeness_comment": f"Complétude {band}. Familles manquantes : {', '.join(missing) or 'aucune'}.",
            "confirmed_facts": confirmed,
            "positive_signals": positives,
            "blocking_or_risk_signals": risks,
            "false_positive_risks": false_pos,
            "why_land_might_be_empty": [],
            "developer_interest_hypothesis": "",
            "possible_project_types": [],
            "market_context_summary": next((v["detail"] for v in verdicts if v.get("layer") == "dvf"), ""),
            "regulatory_context_summary": next((v["detail"] for v in verdicts if v.get("layer") in ("sar", "zonage_plu_gpu")), ""),
            "environmental_risk_summary": next((v["detail"] for v in verdicts if v.get("layer") == "risques"), ""),
            "reunion_specific_flags": _reunion_flags(verdicts),
            "missing_data": missing,
            "must_check_before_showing_developer": must_check,
            "recommended_status": status,
            "opportunity_score_adjustment": 0,  # le stub ne corrige pas le score
            "confidence_level": _confidence_from_band(band),
            "developer_pitch": "",
            "warnings": ["Analyse générée hors-ligne (provider stub) : aucune interprétation libre."],
        }
        errors = validate_ai_output(out)
        if errors:  # pragma: no cover - le stub doit toujours être valide
            raise ValueError(f"Sortie stub invalide : {errors}")
        return out


class AnthropicProvider:
    """Provider réel (API Messages). Nécessite `anthropic` + ANTHROPIC_API_KEY + réseau."""

    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or get_settings().ai_model
        self._api_key = api_key

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Le paquet `anthropic` n'est pas installé.") from exc

        client = anthropic.Anthropic(api_key=self._api_key)
        user = (
            "Voici le payload de données de la parcelle (raisonne UNIQUEMENT là-dessus) :\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + "\n\nRéponds en JSON strict conforme au schéma."
        )
        resp = client.messages.create(
            model=self.model, max_tokens=1800, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
        data = _extract_json(text)
        errors = validate_ai_output(data)
        if errors:
            raise ValueError(f"Sortie IA non conforme au schéma : {errors}")
        return data


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start : end + 1])


def get_provider(provider: str | None = None) -> AIProvider:
    provider = provider or get_settings().ai_provider
    if provider == "anthropic":
        return AnthropicProvider()
    return StubProvider()


def analyze(payload: dict[str, Any], provider: AIProvider | None = None) -> dict[str, Any]:
    return (provider or get_provider()).analyze(payload)
