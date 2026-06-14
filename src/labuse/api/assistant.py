"""3.A — Assistant de fiche en langage naturel (API Anthropic).

« Expliquer cette parcelle » → une synthèse en prose française des forces/faiblesses, produite
**STRICTEMENT** à partir des données réelles de la fiche.

Garde-fou anti-hallucination : le prompt envoyé au modèle ne contient QUE des faits structurés
extraits de la fiche (`assistant_facts`, liste blanche) — le modèle REFORMULE, il n'ajoute aucun
chiffre ni verdict. Si une donnée manque, il doit le dire.

Clé API : variable d'environnement **ANTHROPIC_API_KEY** (jamais en clair dans le code, jamais
commitée). Absente → message clair, AUCUN crash. Modèle surchargeable via LABUSE_ASSISTANT_MODEL.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-6"
ENV_KEY = "ANTHROPIC_API_KEY"
ENV_MODEL = "LABUSE_ASSISTANT_MODEL"

SYSTEM = (
    "Tu es l'assistant foncier de LA BUSE. À partir UNIQUEMENT des données structurées fournies "
    "(JSON), rédige en français une explication claire et honnête de la parcelle pour un "
    "promoteur : statut, capacité constructible, contraintes, bilan, complétude des données. "
    "RÈGLES STRICTES : n'invente AUCUN chiffre, AUCUN verdict, AUCUNE donnée absente du JSON ; "
    "si une information manque ou est nulle, dis-le explicitement ; ne donne jamais de garantie "
    "réglementaire ou de rentabilité. Sois concis (4 à 8 phrases), structuré, sans jargon inutile."
)


def _num(x: Any) -> Any:
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def assistant_facts(fiche: dict) -> dict[str, Any]:
    """Liste BLANCHE des faits réels de la fiche → unique contenu du prompt (anti-hallucination).

    On ne transmet QUE des valeurs déjà calculées/sourcées : aucune reformulation, aucun ajout."""
    p = fiche.get("parcel") or {}
    v = fiche.get("verdict") or {}
    fa = fiche.get("faisabilite") or {}
    fr = (fa.get("fourchette") or {}) if fa else {}
    bil = (fa.get("bilan") or {}) if fa else {}
    v3 = (fa.get("volume3d") or {}) if fa else {}
    contraintes = [
        {"type": r.get("result"), "regle": r.get("layer_name"), "motif": r.get("detail")}
        for r in (fiche.get("cascade") or [])
        if r.get("result") in ("HARD_EXCLUDE", "SOFT_FLAG", "POSITIVE")
    ]
    return {
        "parcelle": {"idu": p.get("idu"), "commune": p.get("commune"),
                     "surface_m2": _num(p.get("surface_m2"))},
        "verdict": {"statut": v.get("status"),
                    "score_opportunite": _num(v.get("opportunity_score")),
                    "score_completude": _num(v.get("completeness_score")),
                    "motif_declassement": v.get("downgrade_reason")},
        "faisabilite": ({
            "zone_plu": fa.get("zone"), "constructible": fa.get("constructible"),
            "synthese": fa.get("verdict"),
            "niveaux": fr.get("niveaux"), "surface_plancher_m2": fr.get("surface_plancher_m2"),
            "logements_au_sol": fr.get("logements_au_sol"),
            "hauteur_m": fr.get("hauteur_m"), "volume_enveloppe_m3": v3.get("volume_m3"),
        } if fa else None),
        "bilan_promoteur": ({
            "verdict": bil.get("verdict"), "charge_fonciere": bil.get("charge_fonciere"),
            "fiable": bil.get("fiable"),
        } if bil else None),
        "contraintes_et_signaux": contraintes,
        "completude": {
            "sources_ayant_repondu": fiche.get("sources_responded"),
            "sources_muettes_donnee_manquante": fiche.get("sources_silent"),
        },
        "resume_metier": fiche.get("resume"),
    }


def _no_key(facts: dict) -> dict[str, Any]:
    return {"available": False, "reason": "no_key", "facts": facts,
            "message": "Assistant IA non configuré — définissez la variable d'environnement "
                       f"{ENV_KEY} (clé API Anthropic) pour activer « Expliquer cette parcelle »."}


def explain_parcel(fiche: dict, *, timeout: float = 25.0) -> dict[str, Any]:
    """Synthèse en prose via l'API Anthropic. Dégrade PROPREMENT : clé absente / réseau / timeout
    → `available=False` + message clair, jamais d'exception remontée à l'endpoint."""
    facts = assistant_facts(fiche)
    key = os.environ.get(ENV_KEY, "").strip()
    if not key:
        return _no_key(facts)
    model = os.environ.get(ENV_MODEL, "").strip() or DEFAULT_MODEL
    payload = {
        "model": model, "max_tokens": 700, "system": SYSTEM,
        "messages": [{"role": "user",
                      "content": "Données structurées de la fiche (n'utilise QUE ceci) :\n"
                                 + json.dumps(facts, ensure_ascii=False, indent=2)}],
    }
    try:
        r = httpx.post(API_URL, json=payload, timeout=timeout, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        r.raise_for_status()
        data = r.json()
        prose = "".join(b.get("text", "") for b in data.get("content", [])
                        if b.get("type") == "text").strip()
        if not prose:
            return {"available": False, "reason": "empty", "facts": facts,
                    "message": "Réponse vide de l'assistant — réessayez."}
        return {"available": True, "explanation": prose, "model": data.get("model", model)}
    except httpx.TimeoutException:
        return {"available": False, "reason": "timeout", "facts": facts,
                "message": "L'assistant IA n'a pas répondu à temps — réessayez."}
    except Exception as exc:  # noqa: BLE001 — jamais de 500 sur la fiche
        return {"available": False, "reason": "error", "facts": facts,
                "message": f"Assistant IA momentanément indisponible ({type(exc).__name__})."}
