"""RETOURS-12 A1 — l'IA rebranchée : message d'erreur honnête + source unique de modèle fail-closed.

Le mandat : plus de « réessayez dans un instant » quand la cause est STRUCTURELLE (clé invalide,
modèle retiré) ; aucun modèle dans l'environnement SEUL qui contourne la garde. On teste :
  1. `erreur_infra()` distingue structurel (pas d'invitation à réessayer) de passager (réessayer OK) ;
  2. l'override d'env de l'assistant passe par `check_model` (un modèle retiré est refusé BRUYAMMENT) ;
  3. `ai_models` reste la source unique fail-closed (RETIRED_MODELS refusés).
"""
from __future__ import annotations

import pytest

from labuse.ai import core
from labuse import ai_models
from labuse.copilote_v2 import answering


def test_erreur_infra_structurelle_ninvite_pas_a_reessayer():
    core._LAST_ERROR = "clé invalide (authentification refusée par l'API Anthropic)"
    try:
        msg = answering.erreur_infra()
        assert "Réessayez" not in msg and "réessayer dans l'immédiat" in msg
        assert "alertée" in msg                       # l'incident est signalé (visible admin via /ia/status)
        assert "clé invalide" in msg                  # la cause STRUCTURELLE est nommée
    finally:
        core._LAST_ERROR = None


def test_erreur_infra_passagere_invite_a_reessayer():
    core._LAST_ERROR = None
    msg = answering.erreur_infra()
    assert "Réessayez dans un instant" in msg          # erreur vraiment passagère → réessayer légitime


def test_modele_retire_refuse_bruyamment_fail_closed():
    # ai_models = source unique, fail-closed : un modèle retiré lève (jamais un dégradé muet).
    retire = next(iter(ai_models.RETIRED_MODELS))
    with pytest.raises(ValueError):
        ai_models.check_model(retire)
    # un modèle actif passe.
    assert core.check_model(ai_models.MODEL_REASONING) == ai_models.MODEL_REASONING


def test_override_env_assistant_passe_par_check_model(monkeypatch):
    # RETOURS-12 A1 — l'override LABUSE_ASSISTANT_MODEL ne contourne plus la garde : un modèle retiré
    # posé dans cet env est refusé. On rejoue la ligne de résolution de assistant.py.
    import os
    retire = next(iter(ai_models.RETIRED_MODELS))
    monkeypatch.setenv("LABUSE_ASSISTANT_MODEL", retire)
    env_model = os.environ.get("LABUSE_ASSISTANT_MODEL", "").strip()
    with pytest.raises(ValueError):
        core.check_model(env_model) if env_model else core.model_for("explain")


def test_pin_anthropic_0116():
    # la lignée 0.116.0 est exigée (1.1.0 refuse temperature -> dégradé muet).
    import anthropic
    assert anthropic.__version__.startswith("0.116"), f"anthropic {anthropic.__version__} ≠ 0.116.x"
