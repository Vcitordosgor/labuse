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
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    # src/labuse/config.py -> remonter à la racine du dépôt
    return Path(__file__).resolve().parents[2]


# ── .env ROBUSTE au mode de lancement (correctif C1, revue Vic 07/07) ──
# Chargé par l'APPLICATION elle-même, chemin résolu depuis la RACINE DU DÉPÔT — plus jamais
# dépendant du cwd ni de qui lance quoi d'où (une relance nue du serveur avait privé le
# copilote d'ANTHROPIC_API_KEY → stub alors que la clé existait). override=False : un
# environnement explicitement posé par l'opérateur garde la priorité.
load_dotenv(_repo_root() / ".env", override=False)


class Settings(BaseSettings):
    """Réglages d'environnement (préfixe LABUSE_)."""

    model_config = SettingsConfigDict(env_prefix="LABUSE_", env_file=str(_repo_root() / ".env"),
                                      extra="ignore")

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

    # ── Wave adresses/courrier/IA : protection & plans (Phase 0 : PAS de système de
    # comptes — quotas au niveau session/IP, gating par plan STUBBÉ ; le « mandat
    # Auth & Plans » remplacera plan_defaut par le plan du compte connecté) ──
    quota_fiches_jour: int = 300          # consultations de fiches parcelle / jour / sujet
    rate_limit_rpm: int = 60              # requêtes / minute / sujet (endpoints métier)
    rate_burst_gel: int = 3               # bursts le même jour avant gel + alerte admin
    abuse_alert_seuil: int = 60           # score abuse_scores déclenchant l'alerte
    nl_quota_jour: int = 30               # requêtes de recherche NL / jour / sujet (Lot 6)
    dossier_quota_mois: int = 20          # Dossiers parcelle / mois (plan Essentiel, Lot 4)
    plan_defaut: str = "integral"         # stub : essentiel | integral (pilote = intégral)
    raison_sociale: str = "Pilote LA BUSE"  # mention « Généré via LABUSE pour … » (Lot 4)
    etiquettes_format: str = "63.5x38.1"  # planche d'étiquettes du publipostage (Lot 2A)

    # ── Module Flash : rapport parcelle à l'unité (mandat module-flash) ──
    # Prix TTC affiché/facturé. La valeur de LANCEMENT est décidée par Vic au moment de
    # créer le produit Stripe — 79 € est la suggestion du mandat, jamais une décision.
    flash_price_eur: float = 79.0
    # Stockage local des PDF générés (relatif à la racine du dépôt si non absolu).
    flash_storage_dir: str = "outputs/flash"
    # Validité du lien de téléchargement signé (jours) — re-téléchargeable jusque-là.
    flash_token_days: int = 30
    # Stripe — clés JAMAIS committées ; mode test (sk_test_…) en dev, bascule documentée.
    # Sans clé : la page d'achat affiche « bientôt disponible », AUCUN bouton de paiement
    # factice (leçon P0 TANIA, non négociable).
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id: str | None = None
    # SMTP (livraison des rapports) — provider en config ; sans hôte configuré, provider
    # « console » (le mail est journalisé, jamais envoyé) : acceptable en dev seulement.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "LA BUSE <no-reply@labuse.immo>"
    smtp_starttls: bool = True
    # Alertes exploitation (génération en échec après paiement, etc.).
    admin_email: str | None = None

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


def plh() -> dict[str, Any]:
    """Orientations habitat du PLH du TCO (config/plh_tco.yaml) — LOT 4.1, données extraites."""
    return load_yaml_config("plh_tco")


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
