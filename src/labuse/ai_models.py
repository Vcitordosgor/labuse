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

import os

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


# ── RETOURS-7 Z7 — LE MODÈLE PAR USAGE (surface), en UN seul endroit ─────────────────────────────
# Vic veut savoir quel modèle sert CHAQUE surface IA — et pouvoir le régler sans chasser un littéral
# dans le code. Chaque surface est identifiée par son `kind` (celui journalisé dans `ia_log`, donc la
# facturation et ce registre parlent le même langage). Elle porte ici SON modèle par défaut (une des
# 3 familles ci-dessus, jamais un littéral neuf) et un libellé lisible. Le défaut par usage vit DONC
# à cet unique endroit ; un override par surface reste possible via l'env
# `LABUSE_IA_MODELE_<KIND>` (tirets → underscores, majuscules), validé comme le reste.
# Ce tableau est lu par le dashboard admin (section IA, « surface → modèle ») ET par chaque appelant
# (`model_for(kind)`), de sorte que le tableau du dashboard EST la vérité servie, pas une doc à part.
SURFACES: dict[str, dict] = {
    # kind (ia_log)      : {libellé client,                              modèle par défaut}
    "search":            {"label": "Recherche en langage naturel",       "model": MODEL_FACTUAL},
    "ia-aggregate":      {"label": "Recherche NL — agrégat/classement",  "model": MODEL_FACTUAL},
    "entretien":         {"label": "Entretien (dialogue guidé)",         "model": MODEL_FACTUAL},
    "synthese":          {"label": "Synthèse IA de la fiche",            "model": MODEL_REASONING},
    "pourquoi":          {"label": "Explication du score (fiche)",       "model": MODEL_REASONING},
    "fiche-ask":         {"label": "Question sur la fiche (routée)",     "model": MODEL_REASONING},
    "explain":           {"label": "Assistant — expliquer",             "model": MODEL_REASONING},
    "explain-faisa":     {"label": "Faisabilité — expliquer",           "model": MODEL_REASONING},
    # SUITE-1 S9 — un seul Copilote (v2). La surface des MISSIONS LOURDES (RECHERCHE/VERIFICATION,
    # interprétation du brief par le moteur run-scopé) porte son propre `kind` `copilote_mission`
    # (l'ancienne ligne « Copilote v1 (missions) » disparaît). Modèle : sonnet (raisonnement).
    "copilote_mission":  {"label": "Copilote — missions lourdes (RECHERCHE/VERIFICATION)", "model": MODEL_REASONING},
    "copilote-route":    {"label": "Copilote v2 — routage",              "model": MODEL_FACTUAL},
    "copilote-select":   {"label": "Copilote v2 — sélection d'outil",    "model": MODEL_REASONING},
    "copilote-formule":  {"label": "Copilote v2 — formulation",          "model": MODEL_REASONING},
    "copilote-general":  {"label": "Copilote v2 — réponse générale",     "model": MODEL_REASONING},
    "copilote-prepare":  {"label": "Copilote v2 — préparer un script",   "model": MODEL_REASONING},
    "copilote-web":      {"label": "Copilote v2 — renseigner par le web","model": MODEL_REASONING},
    "copilote-heros":    {"label": "Copilote v2 — accroche du jour",     "model": MODEL_REASONING},
    "traducteur-plu":    {"label": "Traducteur PLU (règlement)",         "model": MODEL_REASONING},
    "synthese-banquier": {"label": "Synthèse banquier",                  "model": MODEL_REASONING},
    "promo_collecte":    {"label": "Parseur programmes promoteur",       "model": MODEL_FACTUAL},
    "vision_pige":       {"label": "Radar — lecture d'image (PIGE)",     "model": MODEL_VISION},
    "juge_vlm":          {"label": "Juge VLM (ML, hors service)",        "model": MODEL_VISION},
}


def _surface_env_key(kind: str) -> str:
    """`copilote-select` → `LABUSE_IA_MODELE_COPILOTE_SELECT` (override par surface)."""
    return "LABUSE_IA_MODELE_" + kind.upper().replace("-", "_")


def model_for(kind: str) -> str:
    """Le modèle SERVI par la surface `kind` : défaut du registre `SURFACES`, sauf override env par
    surface (`LABUSE_IA_MODELE_<KIND>`). Toujours passé par `check_model` — un modèle retiré (dans le
    registre OU dans l'env) lève au lieu d'échouer en silence en prod. `kind` inconnu → défaut agent."""
    entry = SURFACES.get(kind)
    default = entry["model"] if entry else DEFAULT_AGENT_MODEL
    return check_model(os.environ.get(_surface_env_key(kind), "").strip() or default)


def surfaces_table() -> list[dict]:
    """Le tableau « surface → modèle » servi tel quel (dashboard admin + compte-rendu), modèle LU
    depuis la config (défaut registre + override env résolu par `model_for`), jamais un nom en dur."""
    return [{"kind": k, "label": v["label"], "model": model_for(k)} for k, v in SURFACES.items()]
