# Audit de sécurité — checklist OWASP

> **Audit `audit/panorama` · M3 · Lecture seule · 2026-07-23**
> Application du référentiel OWASP Top 10 + fondamentaux, poste par poste. **Ce mandat CONSTATE et RECOMMANDE — il ne corrige rien** (les fixes seront un mandat dédié). Aucun secret imprimé en clair. Périmètre : FastAPI `src/`, front Vite/React `frontend/`.

---

## Synthèse exécutive

| # | Domaine OWASP | Verdict |
|---|---|---|
| 1 | Secrets dans le bundle (A05/A02) | **PASS** — aucun secret côté client |
| 2 | Injections (A03) | **PASS** — aucune injection SQL/commande/template exploitable |
| 3 | Auth & session (A07) | **Bon** — argon2id, tokens CSPRNG ; 1 point moyen→haut, 3 moyens |
| 4 | Contrôle d'accès / IDOR (A01) | **Sain sur ressources privées** ; 1 faille moyenne (gating plan) |
| 5 | Exposition de données (A04/A05) | **Bon** — pas de trace 500, pas de carte ; lacune = **pas de CSP, HSTS commentée** |
| 6 | Exfiltration en masse | **⚠ Risque principal** — 3 findings hauts (tuiles/geojson non throttlés, abuse-scan aveugle) |
| 7 | Dépendances (A06) | **PASS** — npm 0 vuln ; pip-audit indisponible, versions récentes |

---

## 1) Secrets dans le bundle client — **PASS**

- **Scan `frontend/dist`** (patterns `sk_live|sk_test|whsec_|sk-ant-|rk_live|AKIA|SG.|xoxb-|ghp_|pk_live|pk_test`) : **0 correspondance**. Le seul hit `password` est la détection `input type="password"` de maplibre (faux positif).
- **Vars `VITE_` référencées** : une seule, `VITE_RUN_LABEL` (libellé de run, non sensible). Aucune clé `pk_`/`sk_`.
- **`vite.config.ts`** : pas de `define` injectant un secret ; API en dur sur `http://127.0.0.1:8000` (proxy dev, prod = même origine). Aucun token hardcodé.

**Gravité : n/a (PASS).** Le « clic droit → inspecter » de Vic est propre. Reco : conserver la discipline « `pk_` uniquement » si Stripe.js est intégré au front un jour.

---

## 2) Injections — **PASS** (aucune exploitable)

Modèle défensif cohérent : **toute valeur utilisateur passe en paramètre lié** (`:param`, `ANY(:x)`) ; les seuls fragments interpolés en f-string sont des identifiants **internes** (registres, constantes, whitelists), annotés `# noqa: S608`.

- **`/ia/search`** : le texte NL n'atteint jamais le SQL. `nl_aggregate.py:97` n'interpole que des constantes ; `commune`/`tier_codes` résolus contre listes fermées et passés liés. Socle `strict_numbers=True`/`require_sources=True`. `nl_semantics.py` = pur/regex.
- **Moteur segments** (`segments/engine.py:129`) : valeurs liées, enums validés (`FiltreInvalide`), colonnes export whitelistées.
- **Identifiants interpolés tous internes** : `tenant.py:35`, `projets.py:617`, `cascade/context.py:388` (whitelist 2 tables), `app.py:633` `_ban_lateral` (3 appelants passent des littéraux, jamais d'entrée client).
- **Commande** : tous les `subprocess.run` en liste, pas de `shell=True`/`os.system`/`eval`/`exec` sur donnée user.
- **Template** : Jinja Flash `autoescape=True` ; pas de SSTI.

**Gravité : faible.** Durcissement optionnel : filet de test avec payloads d'injection sur `/ia/search` et `/courriers`, validation du `dbname` CLI.

---

## 3) Auth & session — **bon**, 1 point moyen→haut

Deux régimes : **PILOTE** (mot de passe global HMAC, transitoire) et **COMPTES** (cible multi-user).

**Points forts** :
- **Hash** argon2id (`comptes.py:28`) + rehash auto + min 10 car.
- **Tokens** session/invitation/reset : `secrets.token_urlsafe(32)` (~256 bits), **stockés en SHA-256** (clair jamais persisté). Session 12 h, invitation 7 j (single-use), reset 60 min (single-use + invalide toutes les sessions).
- **Cookie** : `HttpOnly`, `SameSite=Lax`, `Secure` hors local.
- **Lockout login** (`comptes.py:196`) : 5 échecs → verrou 15 min + `sleep(0.4s)` + message neutre.
- **HMAC paiement** (`coffre_ui.py:22`) : HMAC-SHA256, `compare_digest`, signe `compte_id.expiry`, TTL 1800 s. **Webhook Stripe** signé + dédup + fail-closed.
- `.env` gitignoré et non tracké.

**Findings** :

| Constat | Gravité | Lieu |
|---|---|---|
| Fallback en dur `"labuse-dev-secret"` si `LABUSE_SECRET_KEY` absente → jeton paiement **forgeable** pour tout `compte_id` (secret non forcée en prod) | **moyenne→haute** | `coffre_ui.py:23`, `config.py:49` |
| `/logout` supprime le cookie mais **n'appelle pas `detruire_session`** → token valide en base jusqu'à `expire_at` | moyenne | `app.py:331` |
| Pas de rate-limit **par IP** sur `/login` (verrou par compte seulement ; pilote sans lockout) | moyenne | `protection.py:128` |
| Session pilote non révocable (HMAC sans état) | moyenne (transitoire) | `auth.py:83` |
| Pas de token CSRF applicatif (repose sur SameSite=Lax) | faible | POST `/login`, `/onboarding/*` |

**Reco prioritaire** : **forcer `LABUSE_SECRET_KEY` en prod** (refus de boot hors local) et supprimer les littéraux de repli.

---

## 4) Contrôle d'accès / IDOR — sain sur le privé, 1 faille moyenne

- **SEC-IDOR (correctif antérieur)** confirmé sain : `_auth_guard` résout `request.state.compte_id` ; `_projet_or_404(db, pid, cid)` (`projets.py:509`) renvoie **404** (pas 403). Les routes `/projets/*` + CRM `pipeline_entries` filtrent par compte. *(NB : voir M7 — 5 surfaces annexes `signalements`/`saved_filters`/`event_log`/`watched_parcels` ignorent `compte_id` : croisé dans CLOISONNEMENT.md.)*
- **5 statuts de COMPTE** (`comptes.py:44`) : `invite` (login OK, app fermée → Checkout), `actif` (plein accès), `paiement_requis` (orphelin, jamais posé), `suspendu` (coupé + sessions détruites), `resilie`. Revérifiés à chaque requête (fail-closed).
- **Faux positifs écartés** : `/dossier/{idu}.pdf` et `/pre-dossier/{idu}.zip` **ne sont pas des IDOR** — `parcels` est du référentiel public, plan-gatés + quota.

**Finding réel (moyen)** : le gating par plan est un **stub process-global**. `plans.plan_courant()` (`plans.py:33`) lit `LABUSE_PLAN_DEFAUT` (`config.py:86`), **pas le plan du compte connecté** → tout « réservé Intégral » est ouvert à tout compte authentifié. Impact nul tant que tous les comptes sont Intégral ; **élevé si des plans différenciés partent en prod**. Reco : brancher sur `request.state.compte_id → comptes.plan`.

---

## 5) Exposition de données

- **Pas de fuite de stack** : aucun `@app.exception_handler(Exception)`, pas de `debug=True`/`traceback` exposé. Handler 404 custom, sinon `{"detail": ...}` standard. Pas de `--reload` en prod.
- **Pas de logs sensibles** : grep logging près de token/secret/key/email = 0 hit exploitable.
- **Pas de données carte** : aucun `card_number/cvv/pan` stocké — Stripe Checkout hébergé + webhook signé uniquement.
- **En-têtes de sécurité** :
  - App (`app.py:141`) : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`.
  - Caddy prod / nginx : idem + `X-Robots-Tag`, `-Server` ; nginx ajoute `X-XSS-Protection`.
  - **Lacunes** : **aucune CSP nulle part** (grep Content-Security-Policy = vide) ; **HSTS commentée** (nginx `labuse.conf:62`, absente de Caddy prod).
- **CORS** : `*` seulement en `env==local` ; prod = origine unique. OK.

**Gravité** : moyenne (absence de CSP sur une SPA carto à ressources externes), faible pour HSTS. Reco : CSP (au moins `default-src 'self'` + allowlist fonts/maplibre) ; activer HSTS une fois HTTPS stable.

---

## 6) Exfiltration en masse — **⚠ risque principal** (3 findings hauts)

| Finding | Gravité | Lieu |
|---|---|---|
| **Tuiles `/map/tiles/*` hors rate-limit / quota / log** — absentes de `PREFIXES_PROTEGES` ET de `consultation_log`. À z12+ chaque tuile porte `idu, surface_m2, q_score, a_score, flags, zone, tier_v2` → balayage bbox = tout le référentiel scoré, **invisible à l'abuse-scan** | **haute** | `protection.py:128`, `tiles.py:185` |
| **`/map/parcels.geojson` cap 200 000 + colonnes `proprio`/`owner_type`** — `commune=NULL` → île entière (431k) en ~3 requêtes ; le quota « fiche » ne matche pas le bulk | **haute** | `app.py:1140,1263` |
| **abuse-scan aveugle au bulk + tuiles** — les signaux reposent sur `consultation_log` alimenté **seulement par la fiche unitaire** `/parcels/{idu}` ; un scraper 100 % bulk laisse le score à 0 | **haute** | `protection.py:132,289` |
| `/parcels` **offset non borné** → énumération bouclable | moyenne | `app.py:789` |
| `/parcels/export.csv` cap 5000 + colonne `proprio`, **non watermarké** (contrairement à segments) | moyenne | `app.py:857` |
| Aucun rate-limit au **bord** (Caddy/nginx) ; `LABUSE_TRUSTED_PROXIES` vide non documenté → sujets IP s'effondrent en 127.0.0.1 derrière Caddy | moyenne | `Caddyfile.prod`, `config.py:78` |

**Mécanisme abuse-scan** (`deploy/cron.d/abuse`, 6 h quotidien, **gel manuel** via `acces_gels`) : quota 300 fiches/j/sujet, rate-limit 60 req/min, `scan_abus` (séquences IDU, régularité machinale, volume nocturne, ratio conso/export), watermarking exports segments. **⚠ Piège prod** : `dev_mode` court-circuite tout le rate-limit (`protection.py:234`).

**Point positif** : `/segments/export` est le bon patron — capé 10 000, **watermarké** (HMAC `ref` + canaris), jamais de personne physique (RGPD « À l'occupant »). Les identités exposées sont des **personnes morales** (open data DGFiP, sensibles surtout par agrégation).

**Reco** : ajouter `/map/tiles` aux préfixes protégés + journaliser le volume tuiles ; compter le bulk dans les quotas ; retirer `proprio`/`owner_type` du geojson bulk ; documenter `LABUSE_TRUSTED_PROXIES=127.0.0.1` ; rate-limit Caddy en défense de bord.

---

## 7) Dépendances — **PASS**

- **npm audit** (`frontend`, `--omit=dev`) : **0 vulnérabilité** (tous niveaux à 0).
- **pip-audit indisponible** (binaire absent de l'env). Versions installées **récentes**, aucune notoirement vulnérable : fastapi 0.136.3, starlette 1.2.1, uvicorn 0.49.0, Jinja2 3.1.6, pydantic 2.13.4, SQLAlchemy 2.0.50, psycopg 3.3.4, requests 2.34.2, urllib3 2.7.0, weasyprint 69.0, pillow 12.3.0, stripe 15.3.0.
- **Réserve** : `requirements.txt` épingle en `>=` (non figé) → reproductibilité/supply-chain non garantie. Reco : `pip install pip-audit` + scan CI ; figer les versions (`==`/lockfile).

---

## Findings à traiter en priorité (décision Vic — non implémentés)

1. **Haute** — throttler/journaliser `/map/tiles` et le bulk geojson : **c'est le trou d'exfiltration réel** (un client authentifié peut aspirer tout le scoring sans déclencher l'abuse-scan).
2. **Moyenne→haute** — forcer `LABUSE_SECRET_KEY` en prod + supprimer le fallback `"labuse-dev-secret"` (jeton paiement forgeable).
3. **Moyenne** — ajouter une CSP ; brancher `plans` sur le compte avant tout multi-plan ; révoquer la session en base au `/logout`.

*Fin M3. Constats et recommandations uniquement — aucune correction appliquée.*
