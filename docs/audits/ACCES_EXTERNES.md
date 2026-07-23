# Cartographie des accès extérieurs

> **Audit `audit/panorama` · M1 · Lecture seule · 2026-07-23**
> Tout ce qui entre ou sort de LABUSE vers le monde. App FastAPI `labuse.api.app:app`, servie par Uvicorn sur `127.0.0.1:8000`, derrière Caddy (ou nginx). Aucun secret en clair : seuls les **noms** de variables d'environnement sont cités.

---

## 1. Entrées — routes & authentification

### Middlewares globaux (du plus externe au plus interne)

| Ordre | Middleware | Fichier | Rôle |
|--:|---|---|---|
| 1 | `_no_cache_html` | `app.py:3217` | `Cache-Control: no-store` sur HTML/`/socle` |
| 2 | `_auth_guard` | `app.py:171` | garde d'authentification + pose `request.state.compte_id` |
| 3 | `_garde_protection` | `app.py:168` → `protection.py:227` | anti-scraping : rate-limit + quota fiches (trafic authentifié) |
| 4 | `_fix_double_encoded_query` | `app.py:147` | répare `%25` double-encodé par les tunnels |
| 5 | `_security_headers` | `app.py:136` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` |
| 6 | `GZipMiddleware` | `app.py:133` | gzip ≥ 1024 o |
| 7 | `CORSMiddleware` | `app.py:127` | `*` **si `env=local`**, sinon `[LABUSE_PUBLIC_URL]` (ou `[]`) |

**Auth (`src/labuse/api/auth.py`)** — cookie de session `labuse_session` (httpOnly, SameSite=Lax, `Secure` hors local). Deux régimes de token :
- **Pilote** `v1.<expiry>.<sig>` signé HMAC-SHA256 avec `LABUSE_SECRET_KEY` (clé éphémère de secours si absente → sessions perdues au reboot).
- **Utilisateur** `u.<token>` → vérité **en base à chaque requête** (`session_info`).

**Fail-closed** : hors `local`, si `LABUSE_AUTH_PASSWORD` absent → toutes les routes métier renvoient **503** (`app.py:192`). Anti-force-brute : délai 0,4 s sur échec (`auth.py:205`), message neutre. Login compte = argon2id + verrou après N échecs.

**Routes publiques** (`_PUBLIC`, `auth.py:35`) : `/health`, `/healthz`, `/healthz/crons`, `/readyz`, `/login`, `/logout`, `/favicon.ico`, `/invitation`, `/reset`, `/reset-demande`, `/cgv`, `/mentions-legales`, `/confidentialite`, `/onboarding/retour`, `/onboarding/paiement`, `/stripe/webhook`, `/guide`, `/flash`, `/flash/retour`, `/flash/statut`, `/flash/telecharger`. `/docs`,`/redoc`,`/openapi.json` : publics **en local uniquement**.

### Table des routes notables

| Route | Méthode | Auth | Exposition |
|---|---|---|---|
| `/health`, `/healthz` | GET | aucune | public (process) |
| `/healthz/crons` | GET | aucune | public (âges des crons + sentinelle webhook) |
| `/readyz` | GET | aucune (détails réduits sans session) | public |
| `/login`, `/logout` | GET/POST | cycle de connexion | public |
| `/invitation`, `/reset`, `/reset-demande` | GET/POST | **token signé** (invitation/reset) | public (`onboarding.py:41-221`) |
| `/cgv`, `/mentions-legales`, `/confidentialite`, `/guide` | GET | aucune | public (pages légales) |
| `/onboarding/paiement` | GET/POST | **jeton HMAC signé** (`coffre_ui.py:27`, TTL 30 min) | public |
| `/onboarding/retour` | GET | aucune | public (retour Checkout) |
| **`/stripe/webhook`** | POST | **signature Stripe** (§3) | webhook |
| `/flash` | GET/POST | aucune | public (tunnel Flash) |
| `/flash/statut`, `/flash/telecharger` | GET | **session_id / token DB** (30 j) | public |
| `/` (racine), `/socle/*` | GET | **session** → sinon 302 `/login` | authentifié |
| `/parcels`, `/map/*.geojson`, `/ia/*`, `/moteurs/*`, `/projets/*`, `/modules/*`, `/pipeline/*`… | GET/POST | **session** + rate-limit/quota | authentifié |
| `/protection/admin`, `/admin/gel/{sujet}`, `/admin/degel/{sujet}` | GET/POST | session (auth globale — **pas de rôle admin distinct**) | authentifié (Vic) |
| **`/p/{token}`** | GET | **token de partage en base** (share_links) | **public** (pack apporteur lecture seule, `partners.py:302`) |
| **`/api/v1/parcels`** | GET | **clé API `?key=`** + quota/jour (`partners.py:381`) | public/clé (B2B2C) |
| `/api/v1/docs` | GET | aucune | public (doc API partenaire) |

**28 routers inclus** (`app.py:3180`) : `/ia`, `/segments`, `/moteurs`, `/projets`, `/modules`, `/events`, `/protection`, `/dossier-banquier`, `/pre-dossier`, `/courrier`, `/tension-fonciere`, `/comparateur-communes`, `/carnet-secteur`, `/ortho`, `/partners`, `/onboarding`, etc. Tous sous l'auth guard sauf `_PUBLIC`.

**Points d'attention exposition** :
- `/p/{token}` et `/api/v1/parcels` sont **publics par conception** (partage externe / robinet B2B2C), protégés par un token/clé en base, **hors garde de session** — mais aujourd'hui masqués par le **basic_auth Caddy global** (rideau pilote, tombera à la bascule auth comptes).
- `/protection/admin*` couvert seulement par l'auth **globale** (pas de séparation de rôle — assumé pilote).

---

## 2. Sorties — appels sortants

Client HTTP = **httpx** (sync + async) ; SDK **anthropic** et **stripe** officiels. Tous en **HTTPS**.

### Services authentifiés (secret requis — nom de variable seul)

| Service | Fichier | Variable(s) |
|---|---|---|
| **Anthropic / Claude API** (Messages) | `ai/agent.py:128`, `ai/core.py:38` | `ANTHROPIC_API_KEY` |
| **Anthropic (Async, VLM piscines)** | `ml/juge_vlm.py:133` | `ANTHROPIC_API_KEY` |
| **Stripe API** | `facturation.py:36` | `STRIPE_SECRET_KEY` |
| **Merci Facteur** (courrier postal) | `courrier.py:88` | `LABUSE_MERCIFACTEUR_API_KEY`, `LABUSE_MERCIFACTEUR_API_SECRET` |
| **INPI RNE** (JWT bearer) | `connectors/inpi_rne.py:36` | `INPI_API_USERNAME`, `INPI_API_PASSWORD` |
| **SMTP** (config seulement, provider `console` par défaut — aucun envoi auto) | `config.py:116` | `LABUSE_SMTP_HOST/PORT/USER/PASSWORD` |

Modèles Anthropic : `claude-haiku-4-5` (factuel) et `claude-sonnet-4-6` (raisonnement). Sans clé → mode stub déterministe, **zéro réseau**.

### APIs open data (sans authentification)

IGN apicarto Cadastre/GPU · IGN Géoplateforme WFS/WMS/WMTS + altimétrie (`data.geopf.fr`) · BAN (`api-adresse.data.gouv.fr`) · Recherche-entreprises DINUM · BODACC DILA · Géorisques (`georisques.gouv.fr/api/v1`) · DPE ADEME (`data.ademe.fr`) · Mérimée (`data.culture.gouv.fr`) · Cartofriches Cerema · QPV (`static.data.gouv.fr`) · SDES/Sitadel Dido · DVF/Cadastre Etalab (`files.data.gouv.fr`, `cadastre.data.gouv.fr`) · DGFiP personnes morales (`data.economie.gouv.fr`) · Data Région Réunion · OSM tiles · Overpass.
Throttles polis intégrés (INPI 0,5 s ; recherche-entreprises 0,2 s ; Géorisques 0,15 s ; BODACC 0,25 s).

---

## 3. Webhooks

**Un seul handler** : `POST /stripe/webhook` (`onboarding.py:226`) → `traiter_webhook` (`facturation.py:237`).

- **Validation de signature** (`facturation.py:244`) : `stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)`. Secret absent → **503** ; signature absente/invalide → **400**. **Fail-closed** (webhook non signé refusé).
- **Anti-rejeu** : déduplication par `event["id"]` dans la table `stripe_events` (`facturation.py:250`).
- **Événements écoutés** (`facturation.py:279-323`) :
  - `checkout.session.completed` (mode `payment`) → fulfillment **Flash** (génère le PDF).
  - `checkout.session.completed` (abonnement) → compte `actif` (+ anti-doublon).
  - `invoice.paid` → réactivation si `paiement_requis`/`suspendu`.
  - `invoice.payment_failed` → statut `paiement_requis`.
  - `customer.subscription.deleted` → `suspendu`.

**Aucun autre webhook.** Merci Facteur = POST sortant (pas un webhook). Aucun callback entrant hors Stripe.

---

## 4. Réseau / pare-feu / TLS

### ufw (`deploy/scripts/ufw_setup.sh`)
Ouvre uniquement **22/tcp** (SSH, `ufw limit`), **80/tcp** (redir HTTPS), **443/tcp** (HTTPS). `default deny incoming` / `allow outgoing`. **API 8000 et PostgreSQL restent internes** (jamais exposés). SSH vérifié avant `--force enable` (anti-lock-out).

### Caddy prod (`deploy/Caddyfile.prod`) — actif en prod (M7)
- Domaine `app.labuse.immo`, HTTPS auto Let's Encrypt, `encode gzip`.
- **`basic_auth` devant TOUT le trafic** (user `labuse`, hash `CADDY_BASIC_HASH`) — rideau temporaire pilote, healthz compris.
- `root /opt/labuse/app/frontend/dist` (React statique) ; `/app*` → 301 vers `/` (vieille UI Vue jamais exposée) ; `/` sans cookie → 302 `/login`.
- Reste → `reverse_proxy 127.0.0.1:8000`.
- Headers : `X-Robots-Tag noindex,nofollow`, `X-Content-Type-Options nosniff`, `Referrer-Policy same-origin`, `-Server`. Cache 1 an immutable sur `/assets/*`, `no-cache` sur le shell.

### nginx (`deploy/nginx/labuse.conf`) — variante alternative
80 → 301 HTTPS ; 443 TLSv1.2/1.3 → `proxy_pass 127.0.0.1:8000`. Apex → 301 vers app. `client_max_body_size 25m`. Headers `always` mais **HSTS commenté**.

### systemd (`deploy/systemd/labuse.service`)
Uvicorn `--host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips 127.0.0.1`. `EnvironmentFile=/etc/labuse/labuse.env` (secrets hors git). Durcissement : `NoNewPrivileges`, `ProtectSystem=full`, `ProtectHome`, `PrivateTmp`.

### docker-compose
- `docker-compose.yml` (dev) : Postgres avec **`5432:5432` exposé** — dev local uniquement.
- `docker-compose.pilot.yml` : DB **sans `ports:`** (réseau compose fermé) ; app bind `127.0.0.1:8000` par défaut.
- `docker-compose.caddy.yml` : Caddy expose **80 + 443** uniquement.

### Confiance proxy (`protection.py:90`)
`X-Forwarded-For` cru seulement si le pair ∈ `LABUSE_TRUSTED_PROXIES`. Exemptions rate-limit : `LABUSE_DEV_MODE=1` + `LABUSE_QA_ALLOWLIST`.

---

## Synthèse des surfaces

- **Publiques hors session** : Flash, onboarding (tokens signés), pages légales, `/stripe/webhook` (signé), `/p/{token}` (token DB), `/api/v1/parcels` (clé+quota), `/healthz*`, `/readyz` — **toutes masquées par le basic_auth Caddy global** aujourd'hui (rideau pilote, tombera à la bascule auth comptes).
- **Webhook Stripe** : signature obligatoire, dédup rejeu, fail-closed — solide.
- **Réseau** : seuls 22/80/443 exposés ; API + PG en loopback ; Uvicorn ne fait confiance qu'à 127.0.0.1 pour les headers forwarded.
- **À noter** : CORS `*` si `env=local` ; HSTS désactivé (commenté) dans nginx ; `/protection/admin*` sans rôle admin distinct ; `docker-compose.yml` (dev) expose 5432.

*Fin M1.*
