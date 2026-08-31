"""SECTEUR-1 (S6) — LES NOMS DE MODÈLES, en UN seul endroit (comme les autres seuils de config).

Contexte : le 30/08/2026, Anthropic signale que la PROD (clé LABUSEVPS) appelle encore
`claude-3-5-haiku-20241022`, retiré de l'API le 19/02/2026 → `not_found_error`. L'appel échouait
DEPUIS FÉVRIER sans que rien ne le signale (try/except qui n'écrivait qu'un bandeau, cf. `core._note_error`).

Deux garde-fous ici :
  1. Les noms vivent dans CE module, pas dispersés dans le code (le routeur `core` et l'agent les lisent d'ici).
  2. `RETIRED_MODELS` + `check_model()` : un nom RETIRÉ (dans le code OU dans l'env `LABUSE_AI_MODEL`)
     est refusé BRUYAMMENT (au démarrage via le validateur config, et à l'appel via un log explicite) —
     jamais un mode dégradé invisible (même leçon que la dette anthropic 1.1.0 du 27/08).

Module SANS dépendance (import par `config` et `core` sans cycle).
"""
from __future__ import annotations

# ── Routeur par TÂCHE (jamais codé en dur chez l'appelant) ──────────────────────────────────────
MODEL_FACTUAL = "claude-haiku-4-5-20251001"     # extraction, factuel, acronymes, filtres NL (ex-3-5-haiku)
MODEL_REASONING = "claude-sonnet-4-6"           # raisonnement explicite (faisabilité expliquée, synthèse)
MODEL_VISION = "claude-haiku-4-5-20251001"      # RADAR P1 — lecture d'image (Haiku 4.5 voit)
DEFAULT_AGENT_MODEL = MODEL_REASONING           # défaut du Copilote (`config.ai_model`)

# ── Modèles RETIRÉS de l'API Anthropic — un appel les utilisant échoue en `not_found_error`. ──────
# La garde attrape aussi bien une régression dans le code qu'un env de PROD resté sur un vieux nom.
RETIRED_MODELS = frozenset({
    "claude-3-5-haiku-20241022",     # ← LE fautif du mail Anthropic 30/08 (retiré le 19/02/2026)
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-2.1", "claude-2.0", "claude-instant-1.2",
})

#: tous les modèles ACTIFS servis par LABUSE (pour la garde + le test).
ACTIVE_MODELS = frozenset({MODEL_FACTUAL, MODEL_REASONING, MODEL_VISION, DEFAULT_AGENT_MODEL})


def check_model(model: str) -> str:
    """Rend `model` s'il est servi, sinon lève BRUYAMMENT. Appelée au démarrage (validateur config) et
    utilisable à l'appel — un modèle retiré ne doit JAMAIS produire un échec prod silencieux."""
    if model in RETIRED_MODELS:
        raise ValueError(
            f"modèle RETIRÉ appelé : « {model} » — l'API Anthropic ne le sert plus "
            f"(mettre à jour ai/models.py ou l'env LABUSE_AI_MODEL). Retenus : {sorted(ACTIVE_MODELS)}")
    return model
