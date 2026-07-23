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
    # Exemption DEV de la protection (audit local, crawl QA). ⚠ JAMAIS d'exemption
    # « localhost » : derrière nginx sur un VPS, TOUT le trafic arrive en 127.0.0.1 et une
    # telle exemption tuerait la protection en prod. En prod derrière proxy de confiance,
    # l'IP réelle vient de X-Forwarded-For (voir trusted_proxies).
    dev_mode: bool = False                # LABUSE_DEV_MODE=1 → quotas/rate-limit désactivés
    # IPs des proxys de confiance (séparées par des virgules, ex. "127.0.0.1"). Quand le
    # pair TCP est l'un d'eux, le sujet anti-scraping = 1er hop non-proxy de X-Forwarded-For
    # (en partant de la droite : la partie gauche de l'en-tête est forgeable par le client).
    trusted_proxies: str = ""
    rate_burst_gel: int = 3               # bursts le même jour avant gel + alerte admin
    # M7 — voie QA du golden en PROD : IPs (CSV) exemptées de rate-limit/quotas, à la manière
    # de dev_mode mais CIBLÉE (jamais globale). Ex. l'IP publique du Mac. Vide = personne.
    qa_allowlist: str = ""                # LABUSE_QA_ALLOWLIST=ip1,ip2
    abuse_alert_seuil: int = 60           # score abuse_scores déclenchant l'alerte
    nl_quota_jour: int = 30               # requêtes de recherche NL / jour / sujet (Lot 6)
    dossier_quota_mois: int = 20          # Dossiers parcelle / mois (plan Essentiel, Lot 4)
    plan_defaut: str = "integral"         # stub : essentiel | integral (pilote = intégral)
    raison_sociale: str = "Pilote LA BUSE"  # mention « Généré via LABUSE pour … » (Lot 4)
    etiquettes_format: str = "63.5x38.1"  # planche d'étiquettes du publipostage (Lot 2A)

    # ── Courrier postal par API (Lot 2B) — prestataire retenu : Merci Facteur
    # (couverture DOM confirmée, API publique v1.2, sandbox). Sans clé → provider
    # « stub » : les endpoints répondent, AUCUN envoi ni bouton côté front. ──
    courrier_provider: str = "stub"       # stub | mercifacteur
    mercifacteur_api_key: str | None = None
    mercifacteur_api_secret: str | None = None
    courrier_cout_lettre_eur: float = 2.69   # lettre verte 3 pages Merci Facteur (grille 2026)
    courrier_marge: float = 1.5              # prix client = coût prestataire × marge
    courrier_max_jour: int = 100             # plafond anti-abus d'envois / jour / sujet

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

    # ── PREMIER EURO (commerce/premier-euro) — auth réelle + abonnements ──
    # Base publique des liens signés (invitation, reset, retour Checkout).
    public_base_url: str = "https://app.labuse.immo"
    # Refonte 22/07 : AUCUN email automatique (Resend supprimé) — les liens d'invitation
    # et de reset s'affichent en CLI/admin, Vic les envoie à la main.
    # Produits créés par `labuse stripe-provisionne` — les IDs reviennent en .env.
    stripe_price_integral: str | None = None   # Intégral 349 €/mois · 1 licence = 1 accès
    stripe_price_flash: str | None = None      # Flash 79 € · paiement unique, un rapport
    # Version des CGV en vigueur — l'acceptation est horodatée AVEC cette version.
    # Bump 2026-07-23 : retrait du sous-traitant « Resend » de l'art. 8 (aucun email auto ;
    # la version DOIT suivre tout changement du texte pour garder l'unicité version→texte).
    cgv_version: str = "2026-07-23"
    # LEX-D — mention fiscale du pied de facture Stripe. DÉFAUT = franchise en base (art. 293 B
    # du CGI) ; à BASCULER par Vic dès l'assujettissement TVA (décision comptable). Signalé au
    # rapport : le MRR visé dépasse le seuil de franchise dans l'année.
    facture_mention: str = ("TVA non applicable, art. 293 B du CGI. "
                            "LABUSE — pré-analyse foncière sur données publiques.")
    # Verrouillage login : N échecs → verrou temporaire (minutes).
    login_echecs_max: int = 5
    login_verrou_minutes: int = 15

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
