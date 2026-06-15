"""Chargement de la configuration : variables d'environnement + fichiers YAML.

Les règles et poids de la cascade/scoring vivent en YAML (brief §2/§7 : « règles
et poids en config », tunables, nourris par le feedback). Le code ne hardcode pas
de seuil métier.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    # src/labuse/config.py -> remonter à la racine du dépôt
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Réglages d'environnement (préfixe LABUSE_)."""

    model_config = SettingsConfigDict(env_prefix="LABUSE_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"

    # ── Mode de déploiement : local (démo dev) | pilot (client encadré) | production ──
    # Pilote/production : cookies Secure, CORS restreint, /docs protégés, auth OBLIGATOIRE
    # (sans LABUSE_AUTH_PASSWORD, les routes métier répondent 503 — fail-closed, jamais ouvert).
    env: str = "local"
    # Authentification pilote (compte unique) : mot de passe en clair OU "sha256:<hexdigest>".
    # JAMAIS en dur dans le code ; activer en local en posant simplement la variable.
    auth_password: str | None = None
    # Clé de signature des cookies de session ; absente → clé éphémère (sessions perdues au
    # redémarrage — acceptable en local, à définir en pilote).
    secret_key: str | None = None
    session_hours: float = 12.0
    # Origine publique (https://…) autorisée en CORS hors local ; vide = même origine seulement.
    public_url: str | None = None

    # Commune pilote — paramétrable (brief §12 : Saint-Paul par défaut).
    pilot_commune_insee: str = "97415"
    pilot_commune_name: str = "Saint-Paul"

    config_dir: str = "config"
    http_timeout_s: float = 20.0

    # Agent IA (post-cœur) — provider "stub" par défaut (aucun appel réseau).
    ai_provider: str = "stub"
    ai_model: str = "claude-sonnet-4-6"

    @property
    def config_path(self) -> Path:
        p = Path(self.config_dir)
        return p if p.is_absolute() else _repo_root() / p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=None)
def load_yaml_config(name: str) -> dict[str, Any]:
    """Charge un fichier de config YAML par nom (sans extension), avec cache.

    Ex. load_yaml_config("cascade_rules") -> config/cascade_rules.yaml
    """
    path = get_settings().config_path / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config introuvable : {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config {name} : racine YAML attendue = mapping, obtenu {type(data)}")
    return data


def cascade_rules() -> dict[str, Any]:
    return load_yaml_config("cascade_rules")


def completeness_weights() -> dict[str, Any]:
    return load_yaml_config("completeness_weights")


def opportunity_weights() -> dict[str, Any]:
    return load_yaml_config("opportunity_weights")


def wfs_layers() -> dict[str, Any]:
    return load_yaml_config("wfs_layers")


def pipeline() -> dict[str, Any]:
    """Colonnes & priorités du Kanban de prospection (config/pipeline.yaml)."""
    return load_yaml_config("pipeline")


def shortlist() -> dict[str, Any]:
    """Pondérations de la shortlist promoteur (config/shortlist.yaml) — calibration métier."""
    return load_yaml_config("shortlist")


@lru_cache(maxsize=1)
def rules_version() -> str:
    """Empreinte courte des configs de règles (pour estampiller les évaluations)."""
    import hashlib

    h = hashlib.sha1()
    for name in ("cascade_rules", "completeness_weights", "opportunity_weights"):
        h.update(yaml.safe_dump(load_yaml_config(name), sort_keys=True).encode("utf-8"))
    return h.hexdigest()[:12]


def reset_config_cache() -> None:
    """Vide les caches (utile en tests quand on bascule de config)."""
    load_yaml_config.cache_clear()
    get_settings.cache_clear()
    rules_version.cache_clear()


# Permet de surcharger le répertoire de config via env même quand .env absent.
if os.environ.get("LABUSE_CONFIG_DIR"):
    get_settings.cache_clear()
