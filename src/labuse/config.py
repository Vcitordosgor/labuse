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
from pydantic import model_validator
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
    # AUDIT COMPTES · A5 — seuil du SIGNAL de partage de compte (dashboard admin) : nombre d'IP
    # distinctes actives simultanément au-delà duquel un compte est signalé (jamais bloqué).
    # 1 licence = 1 accès ; 3 postes simultanés = partage probable. Purement informatif.
    sessions_signal_seuil: int = 3
    # K1 (rattrapage KelFoncier) — DRAPEAU RGPD : le filtre par ÂGE du dirigeant (INPI RNE) reste
    # FERMÉ par défaut. L'âge est une donnée personnelle sensible, question ouverte pour l'avocat
    # (diffusibilité INPI). Tant que ce drapeau est false, l'endpoint refuse toute clé `age_*` et
    # l'UI ne montre pas le contrôle. Ne PAS activer sans arbitrage juridique.
    filtre_age_dirigeant: bool = False
    # Origine publique (https://…) autorisée en CORS hors local ; vide = même origine seulement.
    public_url: str | None = None

    # Commune pilote — paramétrable (brief §12 : Saint-Paul par défaut).
    pilot_commune_insee: str = "97415"
    pilot_commune_name: str = "Saint-Paul"

    config_dir: str = "config"
    http_timeout_s: float = 20.0

    # RADAR (pige) — répertoire PRIVÉ des captures : hors racine publique, jamais servi par le web,
    # inclus au backup (mandat RADAR V0 §2). Surchargé par LABUSE_PIGE_CAPTURES_DIR en dev/tests.
    pige_captures_dir: str = "/srv/labuse/pige/captures"

    # Agent IA (post-cœur) — provider "stub" par défaut (aucun appel réseau).
    ai_provider: str = "stub"
    ai_model: str = "claude-sonnet-4-6"

    # ── Wave adresses/courrier/IA : protection & plans (Phase 0 : PAS de système de
    # comptes — quotas au niveau session/IP, gating par plan STUBBÉ ; le « mandat
    # Auth & Plans » remplacera plan_defaut par le plan du compte connecté) ──
    quota_fiches_jour: int = 300          # consultations de fiches parcelle / jour / sujet
    rate_limit_rpm: int = 60              # requêtes / minute / sujet (endpoints métier)
    # Carto de masse (P0 « avant multi-comptes ») — les tuiles vectorielles z≥12 portent le
    # référentiel scoré (idu + q/a + flags) et le geojson île peut renvoyer 200k parcelles :
    # deux canaux d'exfiltration. On NE met PAS les tuiles sous le rate-limit 60/min (une carte
    # qui panne charge des dizaines de tuiles/s — ce n'est pas du scraping) : quota JOURNALIER
    # généreux à la place. Calibrage : usage humain intense (heures de navigation z9-16, cache
    # navigateur 1 h) reste < ~15-20k tuiles/j ; l'île scorée entière ne fait que quelques
    # milliers de tuiles → 40k laisse re-parcourir l'île plusieurs fois avant de gêner, mais
    # une boucle de moisson multi-zoom trippe. Dépassement → 429 « reprend à minuit » (throttle,
    # jamais un gel auto). Le geojson île (dump massif) : quota d'appels/jour (un humain en charge
    # une poignée par session ; 400 est large, une boucle de moisson par commune/bbox trippe).
    quota_tuiles_jour: int = 40000        # tuiles vectorielles /map/tiles / jour / sujet
    quota_carto_jour: int = 400           # dumps geojson carto (/map/parcels.geojson) / jour / sujet
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
    # DASHBOARD-V1 · D1 — quota Copilote PAR LICENCE (comptes connectés) : défaut 80/jour,
    # surchargeable par compte (comptes.copilote_quota_jour, éditable au dashboard). Le quota
    # historique nl_quota_jour reste celui des sujets SANS compte (pilote/anonyme).
    copilote_questions_jour_defaut: int = 80
    dossier_quota_mois: int = 20          # Dossiers parcelle / mois (plan Essentiel, Lot 4)
    plan_defaut: str = "integral"         # stub : essentiel | integral (pilote = intégral)
    raison_sociale: str = "Pilote LABUSE"  # mention « Généré via LABUSE pour … » (Lot 4)
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

    # ── Offre INTÉGRAL — abonnement mensuel (parcours d'entrée · E1) ──
    # Prix mensuel TTC. SOURCE DE VÉRITÉ UNIQUE du prix Intégral : lu par src/labuse/offres.py,
    # jamais réécrit en dur ailleurs (front compris). Changer le prix = changer CETTE ligne.
    integral_prix_eur_mois: int = 349
    # ── Module Flash : rapport parcelle à l'unité (mandat module-flash) ──
    # Prix TTC affiché/facturé. SOURCE DE VÉRITÉ UNIQUE du prix Flash (lu par offres.py).
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
    # DASHBOARD-V1 · D2 — clé RESTREINTE lecture seule (Tour de contrôle) : jamais la clé
    # complète, jamais en dur. Absente → le dashboard affiche « non configuré » proprement.
    # Posée LABUSE_STRIPE_RESTRICTED_KEY (ou STRIPE_RESTRICTED_KEY nu, lu en repli au module).
    stripe_restricted_key: str | None = None
    # DASHBOARD-V1 · D3 — répertoire des dumps de backup (GB-054) : la tuile « dernier backup »
    # lit le mtime du .dump le plus récent (ambre ≥ 2 j, rouge ≥ 7 j, « absent » honnête sinon).
    backup_dir: str = "/var/backups/labuse"
    # VP-001 (mandat VPS) — dossier des binaires pg_dump/pg_restore quand le PATH sert une
    # MAUVAISE version (Mac : Homebrew 16 devant le client 18). Absent → PATH, avec garde de
    # version (backup-db refuse un pg_dump plus vieux que le serveur au lieu d'échouer cryptique).
    pg_bin_dir: str | None = None
    # DASHBOARD-V1 · MAILS (Brevo) — templates du cycle de vie client, référencés PAR ID en .env
    # (mandat). Absents → mode « non configuré » propre (bouton visible, raison servie, zéro
    # envoi silencieux). Aucun envoi automatique en V1 : l'app rappelle, Vic déclenche.
    # DASHBOARD-V1 · D9 — durée par défaut d'un compte d'essai (paramétrable, mandat : 48 h).
    essai_duree_heures: int = 48
    brevo_api_key: str | None = None
    brevo_tpl_essai: str | None = None
    brevo_tpl_souscription: str | None = None
    brevo_tpl_onboarding_1: str | None = None
    brevo_tpl_onboarding_2: str | None = None
    brevo_tpl_onboarding_3: str | None = None
    brevo_tpl_relance_carte: str | None = None
    brevo_tpl_suspension: str | None = None
    brevo_tpl_retablissement: str | None = None
    brevo_tpl_radar: str | None = None                 # RADAR (legacy) — ID 12
    brevo_tpl_radar_digest: str | None = None          # RADAR-DIGESTS — digest quotidien (ID 12)
    brevo_tpl_radar_alerte: str | None = None          # RADAR-DIGESTS — alerte de veille (ID 13)
    # SMTP (M21 — transport e-mail unique) — env LABUSE_SMTP_* + LABUSE_MAIL_FROM.
    # Sans hôte configuré : le mail est JOURNALISÉ et marqué non-envoyé (jamais « envoyé »).
    # Le mot de passe (mot de passe d'application Gmail) vit dans le .env, JAMAIS dans le code.
    smtp_host: str | None = None                 # LABUSE_SMTP_HOST (ex. smtp.gmail.com)
    smtp_port: int = 587                         # LABUSE_SMTP_PORT (587 = STARTTLS)
    smtp_user: str | None = None                 # LABUSE_SMTP_USER (ex. contactlabuse@gmail.com)
    smtp_password: str | None = None             # LABUSE_SMTP_PASSWORD (mot de passe d'application, 16 c.)
    smtp_starttls: bool = True                   # LABUSE_SMTP_STARTTLS
    # Expéditeur AFFICHÉ (alias vérifié Google) — jamais l'adresse Gmail brute.
    mail_from: str = "LABUSE <contact@labuse.immo>"   # LABUSE_MAIL_FROM
    smtp_from: str = "LABUSE <contact@labuse.immo>"   # rétro-compat (déprécié — utiliser mail_from)
    # Alertes exploitation (génération en échec après paiement, etc.).
    admin_email: str | None = None
    # O4 — adresse de contact HUMAINE affichée aux prospects (écran « paiement interrompu » :
    # « Écrivez à … — je réponds moi-même »). Adresse personnelle assumée, distincte de l'expéditeur
    # transactionnel `mail_from`. À CONFIRMER par Vic (défaut = valeur de la maquette validée).
    contact_email: str = "victor@labuse.immo"

    # ── PREMIER EURO (commerce/premier-euro) — auth réelle + abonnements ──
    # Base publique des liens signés (invitation, reset, retour Checkout).
    # ENV-AWARE : en local, ces URLs doivent pointer sur le serveur LOCAL — sinon après un
    # paiement de test on est renvoyé sur la PROD (app.labuse.immo) et la page /flash/retour
    # tourne dans le vide. Résolu par le validateur ci-dessous : None → localhost en 'local',
    # prod sinon. Un LABUSE_PUBLIC_BASE_URL explicite prime toujours.
    public_base_url: str | None = None
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
    # VPS · go-live — MORT du login pilote PARTAGÉ : à False, le chemin « identifiant vide »
    # de POST /login répond en échec NEUTRE (401, même page — rien ne révèle que la voie
    # existe). Défaut True pour la compat locale/QA ; la prod pose LABUSE_LOGIN_PILOTE_ACTIF=0.
    login_pilote_actif: bool = True

    # ── M26-A — Copilote (socle agentique) ──
    # Quota provisoire (la vraie valeur sera fixée avec l'offre) ; compté kind='agent'
    # dans usage_compteurs, même scope que la propriété du run (compte, sinon session/IP).
    copilote_quota_jour: int = 10          # runs Copilote / jour / sujet
    copilote_timeout_run_s: float = 120.0  # budget global d'exécution d'un run
    copilote_max_appels_moteurs: int = 12  # plafond d'appels moteurs (retries inclus)
    # Garde-fou de DERNIER RECOURS sur le nombre de parcelles instruites (arbitrage Vic,
    # revue plafond M26-A — 5 000 validé sur mesure : exhaustif run 1 = 56,8 s < 120 s).
    # TOUJOURS un plafond en PARCELLES, jamais un budget en temps : un seuil temporel
    # rendrait le même brief non reproductible d'un jour à l'autre. S'il mord, la
    # requalification s'applique intégralement (« N examinées sur M candidates »).
    copilote_max_candidats: int = 5000
    copilote_top_restitution: int = 20     # top-N restitué (toutes missions M26-A)
    copilote_sessions_paralleles: int = 4  # faisabilité/charge : pool borné (arbitrage Vic)
    # M78 · 1f — plafonds Copilote v2 (VALEURS EN CONFIG, jamais en dur ; au plafond : message clair,
    # jamais un échec silencieux). Sonnet partout (Opus interdit sans justification). Chaque appel
    # modèle est déjà journalisé dans ia_log (kind copilote-route|select|formule). Valeurs proposées :
    copilote_v2_missions_jour: int = 40        # missions Copilote v2 / jour / compte
    copilote_v2_tokens_mission: int = 40_000   # plafond de tokens par mission (routage+outils+formulation)
    copilote_v2_instructions_lourdes_max: int = 1  # RECHERCHE/VERIFICATION simultanées / utilisateur (le reste en file)
    copilote_v2_retention_jours: int = 90      # historique conversations/missions conservé N jours (§2b)
    copilote_v2_veilles_max: int = 20          # plafond de veilles actives par compte (§4)
    copilote_v2_contexte_ttl_minutes: int = 10   # M107 (arbitrage Vic) : 10 min d'INACTIVITÉ → le
                                                 # fil repart de zéro (M102-B1 posait 120). Le front
                                                 # lit cette valeur (servie par /ask) et ANNONCE
                                                 # l'expiration — jamais un fil vidé en silence.
                                                 # ATTENTION mesuré : 10 min est court pour qui
                                                 # réfléchit à sa réponse — ajustable ICI.

    @model_validator(mode="after")
    def _base_url_selon_env(self) -> "Settings":
        # public_base_url non posée → localhost en 'local' (retours Checkout/liens pointent sur
        # le serveur LOCAL), prod sinon. Un LABUSE_PUBLIC_BASE_URL explicite prime (déjà non-None).
        if not self.public_base_url:
            self.public_base_url = ("http://127.0.0.1:8000" if self.env == "local"
                                    else "https://app.labuse.immo")
        return self

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


def seuils_geometrie() -> dict[str, Any]:
    """M129 P1.4 — seuils géométriques sortis du dur (bati / etage0_ext / division_or)."""
    return load_yaml_config("seuils_geometrie")


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
