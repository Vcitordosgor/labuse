# Cartographie des secrets — LABUSE

> **Mandat `infra/charge-et-secrets` · M5 · LECTURE SEULE · 2026-07-23**
> Carte de chaque secret : **nom**, **où il vit**, **usage**, **consommateur**, **émetteur**. **Aucune valeur de secret n'apparaît ici** (présence = `<set>`). Tu fais tourner les clés toi-même — voir [`RUNBOOK_ROTATION_CLES.md`](../RUNBOOK_ROTATION_CLES.md). Je n'ai touché à aucune clé.

---

## 1. Inventaire

### Mac local — `~/Desktop/labuse/.env` (gitignoré, jamais commité)
| Variable | Usage | Consommateur | Émetteur |
|---|---|---|---|
| `LABUSE_DATABASE_URL` | DSN Postgres (mot de passe embarqué) | `config.database_url`, tout le code DB | Postgres |
| `LABUSE_STRIPE_SECRET_KEY` | Paiements Stripe (Intégral/Flash) | `config.stripe_secret_key`, `facturation.py` | Stripe |
| `LABUSE_STRIPE_WEBHOOK_SECRET` | Vérif signature webhook Stripe | `config.stripe_webhook_secret` | Stripe |
| `LABUSE_STRIPE_PRICE_INTEGRAL` / `_FLASH` | IDs de prix (pas des secrets, mais sensibles) | checkout | Stripe |
| `ANTHROPIC_API_KEY` | IA copilote (recherche NL, explication fiche) | couche IA (`ai/core.py`, `ml/juge_vlm.py`) | Anthropic |
| `INPI_API_USERNAME` / `INPI_API_PASSWORD` | API RNE (dirigeants) | `connectors/inpi_rne.py` | INPI |
| `INPI_SFTP_USER` / `INPI_SFTP_PASSWORD` | Flux SFTP INPI (bulk) | scripts d'ingestion INPI | INPI |

### Mac local — `~/labuse-backups/M7_SECRETS.txt` (clair, chmod 600, PAS un repo git)
Clés présentes (valeurs masquées) : `PG_LABUSE_PASSWORD`, `LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY`, `CADDY_BASIC_AUTH_USER`, `CADDY_BASIC_AUTH_PASSWORD`. En-tête auto-déclaré « JAMAIS EN GIT ». **C'est la liste-maître locale = les bijoux de la couronne.**

### VPS `labuse-vps` — `/etc/labuse/labuse.env` (perms `-rw-r----- root:labuse`)
| Variable | Usage | Consommateur | Émetteur |
|---|---|---|---|
| `LABUSE_DATABASE_URL` | DSN Postgres prod | uvicorn (`labuse.service`) | Postgres |
| `LABUSE_AUTH_PASSWORD` | Mot de passe pilote (fail-closed 503 sans lui) | `config.auth_password`, `auth.py` | LABUSE |
| `LABUSE_SECRET_KEY` | Clé HMAC de signature (session, jeton paiement, filigrane) | `auth.cle_signature()` | LABUSE (`openssl rand -hex 32`) |
| `ANTHROPIC_API_KEY` | IA (vide au jour 1 → repli stub) | couche IA | Anthropic |
| *(non-secrets)* `LABUSE_PUBLIC_URL`, `LABUSE_SERVED_RUN`, `LABUSE_QA_ALLOWLIST`, `LABUSE_TRUSTED_PROXIES`, `LABUSE_ENV`, `LABUSE_BACKUP_*` | config | app | — |

### VPS — `/etc/caddy/labuse.env` (perms `-rw------- root:root`)
| Variable | Usage | Consommateur | Émetteur |
|---|---|---|---|
| `CADDY_BASIC_HASH` | hash bcrypt du rideau basic_auth `labuse` | Caddy (`basic_auth { labuse {$CADDY_BASIC_HASH} }`) | Caddy/bcrypt |

Le Caddyfile ne référence le hash **que** via le placeholder `{$CADDY_BASIC_HASH}` — **aucun hash en dur** dans le Caddyfile (bon).

### VPS — `/home/labuse/.pgpass` (perms `-rw------- labuse:labuse`)
Une entrée `localhost:5432:labuse:labuse:<masqué>`. Consommateur : `pg_dump` / scripts de backup (user `labuse`). Émetteur : Postgres.

### Mac — SSH & automatisation
| Élément | Chemin | Note |
|---|---|---|
| Clé SSH Mac→VPS | `~/.ssh/labuse_vps_ed25519` (perms 600) | Consommateur : `ssh labuse-vps`, deploy, pull backups. Émetteur : SSH ed25519 |
| Config SSH | `~/.ssh/config` Host `labuse-vps` | User `ubuntu`, ControlMaster — aucun secret |
| LaunchAgent | `~/Library/LaunchAgents/immo.labuse.pull-backups.plist` | **Ne porte aucun secret** (auth = clé SSH) |
| `~/.pgpass` (Mac) | — | **N'existe pas** sur le Mac |

### Réglages `config.py` porteurs de secret (préfixe `LABUSE_`, défaut `None`/stub)
`auth_password`, `secret_key`, `stripe_secret_key`, `stripe_webhook_secret`, `mercifacteur_api_key`, `mercifacteur_api_secret`, `smtp_password`, `database_url`. **Rien n'est en dur** — tout passe par l'environnement.

---

## 2. Mauvais emplacements — findings

| # | Constat | Emplacement | Gravité | Reco |
|---|---|---|---|---|
| **F1** | Secrets en **clair** au repos sur le Mac | `.env` (gitignoré ✓), `M7_SECRETS.txt` (chmod 600, hors git ✓) | **Moyenne** | Acceptable vu perms + gitignore. Long terme : coffre chiffré (Bitwarden, `age`) plutôt qu'un `.txt` clair |
| **F2** | Secret dans l'historique git ? | commit touchant `.env.pilot.example`, `deploy/env/labuse.env.example` | **FAUX POSITIF (info)** | Les lignes `+…=` sont des **placeholders / commandes de génération** (`openssl…`, `CHANGE_MOI`, `<…>`), pas des valeurs réelles. `.env` réel **jamais tracké** (`git ls-files .env` = vide, gitignoré). **Aucune rotation requise de ce fait.** |
| **F3** | Secrets dans `~/.zsh_history` | Mac | **AUCUN** | 0 occurrence de `sk_live/sk_test/whsec/sk-ant/*_PASSWORD=/PGPASSWORD/SECRET_KEY=`. Propre. |
| **F4** | Secrets en dur dans le code | `src/`, `frontend/` | **AUCUN** | 0 occurrence de `sk_live_/sk_test_/whsec_/sk-ant-/AKIA`. Tout passe par env/`config.py`. |
| **F5** | Secrets dans les logs | logs app/backup | **Faible** | Pas de journalisation de token/clé trouvée près des lectures de secret. |
| **F6** | `.env.*.example` non gitignorés (trackés) | repo | **Info** | Correct par conception (exemples) — restent placeholder-only, à garder ainsi. |

**Net** : aucun secret réel exposé dans git, le code ou l'historique shell. Les seuls secrets en clair au repos sont les fichiers opérateur volontaires (`.env` gitignoré, `M7_SECRETS.txt` chmod 600).

> ⚠ **Nuance transverse pour la rotation** : le **mot de passe Postgres** et le **hash basic_auth** vivent chacun à **deux endroits qui doivent bouger ensemble** — Postgres : `LABUSE_DATABASE_URL` (Mac + VPS) **et** `/home/labuse/.pgpass` ; basic_auth : `/etc/caddy/labuse.env`. Voir le runbook.

*Fin M5-B1/B2.*
