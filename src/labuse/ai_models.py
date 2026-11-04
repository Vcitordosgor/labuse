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
# JOHN-TAYLOR-1 — l'agent d'exploitation parle avec Vic, écrit le résumé du matin et mène les enquêtes :
# ces tâches EXIGENT le modèle le plus capable (raisonnement sur des journaux, prudence anti-invention) ;
# la veille / les lectures de masse prennent le Haiku le moins cher. Le mandat demande « Opus 5.5 » et
# « Haiku 5.5 » : VÉRIFIÉS SERVIS par l'API le 2026-11-03 (appel réel 200) → ce sont les DÉFAUTS. Si un
# jour un de ces identifiants tombe en `not_found`, on REPLIE automatiquement sur la lignée 4.x (cf.
# REPLI_MODELES + `repli_pour`/`est_not_found`, utilisés par le socle `ai.core` et les appels de John).
MODEL_OPUS = "claude-opus-5-5"                  # JOHN-TAYLOR-1 — chat/résumé/enquête (le plus capable)
MODEL_HAIKU = "claude-haiku-5-5"               # JOHN-TAYLOR-1 — veille / lectures de masse (le moins cher)
MODEL_OPUS_REPLI = "claude-opus-4-8"           # repli si opus-5-5 → not_found
MODEL_HAIKU_REPLI = MODEL_FACTUAL              # repli si haiku-5-5 → not_found (= claude-haiku-4-5)
#: repli par identifiant si l'API rend `not_found` (défensif : les 5.5 répondent aujourd'hui).
REPLI_MODELES: dict[str, str] = {MODEL_OPUS: MODEL_OPUS_REPLI, MODEL_HAIKU: MODEL_HAIKU_REPLI}
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

#: tous les modèles ACTIFS servis par LABUSE (pour la garde + le test). Inclut les 5.5 (défauts John)
#: ET leurs replis 4.x (encore servis, utilisés si le 5.5 tombe en not_found).
ACTIVE_MODELS = frozenset({MODEL_FACTUAL, MODEL_REASONING, MODEL_VISION, MODEL_OPUS, MODEL_HAIKU,
                           MODEL_OPUS_REPLI, DEFAULT_AGENT_MODEL})


def repli_pour(model: str) -> str | None:
    """Le modèle de REPLI si `model` tombe en `not_found` à l'API, sinon None (JOHN-TAYLOR-1)."""
    return REPLI_MODELES.get(model)


def est_not_found(exc: Exception) -> bool:
    """Vrai si l'exception d'appel modèle est un « modèle introuvable » (404 / not_found_error)."""
    name = type(exc).__name__
    s = str(exc)
    return "NotFound" in name or "not_found" in s or "404" in s


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
    # COPILOTE-2 lot 6 — UN SEUL MODÈLE, le moins cher (Haiku), sur les trois chemins (FICHE/OUTIL/WEB).
    # Le chemin FICHE ne calcule rien (résumé déterministe, le modèle tourne la phrase) ; OUTIL route +
    # extrait des paramètres ; WEB cite ses sources. Haiku suffit partout. Le seul doute de qualité est
    # la synthèse WEB : Haiku PAR DÉFAUT, relevée à Sonnet via `LABUSE_IA_MODELE_COPILOTE_WEB` SI la
    # mesure l'exige (mandat : « Sonnet seulement si la qualité du chemin WEB l'exige, mesuré » — mesure
    # différée, clé à créditer). Router inchangé (Haiku).
    # COPILOTE-5 — le ROUTAGE passe à `claude-haiku-5-5` (repli auto `claude-haiku-4-5` si not_found,
    # via REPLI_MODELES ; `temperature` omise, haiku-5-5 ∈ NO_TEMPERATURE_MODELS). Le tri reste une
    # EXTRACTION (intent + params), pas de la rédaction — Haiku, mais la génération 5.5. Overridable env.
    "copilote-route":    {"label": "Copilote v2 — routage (3 chemins)",     "model": MODEL_HAIKU},
    "copilote-select":   {"label": "Copilote v2 — chemin OUTIL (sélection)", "model": MODEL_FACTUAL},
    # COPILOTE-5 — la FORMULATION (la phrase servie au client, par-dessus des faits déjà calculés)
    # prend le modèle le plus capable, comme John : `claude-opus-5-5` (VÉRIFIÉ servi, défaut John),
    # repli automatique `claude-opus-4-8` si not_found (REPLI_MODELES, câblé core.complete). Opus
    # REFUSE `temperature` → omis via NO_TEMPERATURE_MODELS (opus-5-5 ET opus-4-8 y sont). Le modèle
    # ne CALCULE ni ne CHOISIT aucun chiffre (verrou anti-invention COPILOTE-3 inchangé) : il tourne la
    # phrase. Routage/sélection restent sur Haiku (extraction, pas rédaction). Overridable env.
    "copilote-formule":  {"label": "Copilote v2 — formulation (phrase servie)", "model": MODEL_OPUS},
    "copilote-general":  {"label": "Copilote v2 — chemin WEB (connaissance)", "model": MODEL_FACTUAL},
    "copilote-prepare":  {"label": "Copilote v2 — préparer un script",       "model": MODEL_FACTUAL},
    "copilote-web":      {"label": "Copilote v2 — chemin WEB (recherche)",    "model": MODEL_FACTUAL},
    "copilote-heros":    {"label": "Copilote v2 — accroche du jour",         "model": MODEL_FACTUAL},
    "traducteur-plu":    {"label": "Traducteur PLU (règlement)",         "model": MODEL_REASONING},
    "synthese-banquier": {"label": "Synthèse banquier",                  "model": MODEL_REASONING},
    "promo_collecte":    {"label": "Parseur programmes promoteur",       "model": MODEL_FACTUAL},
    "vision_pige":       {"label": "Radar — lecture d'image (PIGE)",     "model": MODEL_VISION},
    # CIRCUIT-1 lot 6 — l'agent de veille d'une source (web_search natif, JSON strict 6.2).
    # CORRECTIFS-1 B4 — le MOINS CHER du registre (Haiku) : la tâche est factuelle (trouver une
    # date/version et la citer), pas du raisonnement. Lecture resserrée (max_uses) + plafond tokens
    # côté agent_source.py. Relevable à Sonnet via LABUSE_IA_MODELE_AGENT_SOURCE si la mesure l'exige.
    "agent_source":      {"label": "Agent de source (veille amont)",      "model": MODEL_FACTUAL},
    # CIRCUIT-4 lot 2 — l'agent « règle » : va lire la référence d'un calcul (Légifrance, INSEE,
    # service-public, ADEME, DEAL…) et ramène l'extrait daté ; même anti-invention qu'agent_source.
    "agent_regle":       {"label": "Agent de règle (références des calculs)", "model": MODEL_REASONING},
    "juge_vlm":          {"label": "Juge VLM (ML, hors service)",        "model": MODEL_VISION},
    # JOHN-TAYLOR-1 — le second de bord. Chat/résumé/enquête = raisonnement sur l'exploitation →
    # Opus (le plus capable) ; la veille de nuit et les lectures de masse = Haiku (factuel, pas cher).
    # Overridables par surface (LABUSE_IA_MODELE_JOHN_CHAT, …) comme le reste.
    "john-chat":         {"label": "John Taylor — chat d'exploitation",  "model": MODEL_OPUS},
    "john-resume":       {"label": "John Taylor — résumé du matin",       "model": MODEL_OPUS},
    "john-enquete":      {"label": "John Taylor — enquête sur incident",  "model": MODEL_OPUS},
    "john-veille":       {"label": "John Taylor — veille de nuit",        "model": MODEL_HAIKU},
}


# CORRECTIFS-1 B2 — répartition des coûts IA en DEUX blocs DISJOINTS (jamais un total mélangé) :
#  · interne = ce que LABUSE dépense pour SON fonctionnement — agents de vérification des sources
#    (agent_source, agent_regle) + outils lancés par le dashboard (collecte programmes, lecture
#    d'image Radar/pige, juge VLM) ;
#  · clients = ce que DÉCLENCHE un client — Recherche NL, Copilote /ask (ses chemins), missions,
#    et toutes les surfaces de fiche (synthèse, explication…).
# Le `kind` journalisé dans `ia_log` est la clé : facturation et registre parlent le même langage.
INTERNE_KINDS = frozenset({
    "agent_source", "agent_regle", "promo_collecte", "vision_pige", "juge_vlm",
    # JOHN-TAYLOR-1 — John sert l'EXPLOITATION (Vic), jamais un client : tout son coût est « interne ».
    "john-chat", "john-resume", "john-enquete", "john-veille",
})


def bloc_ia(kind: str | None) -> str:
    """« interne » (fonctionnement LABUSE) ou « clients » (déclenché par un client)."""
    return "interne" if (kind in INTERNE_KINDS) else "clients"


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
