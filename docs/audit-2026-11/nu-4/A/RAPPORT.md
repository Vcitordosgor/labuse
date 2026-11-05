# MANDAT NU4-A — La sécurité vue par un attaquant

**Registre.** Audit **LECTURE SEULE**, joué le 2026-11-04. Branche `audit/nu4-a`, worktree
`~/Desktop/labuse-nu4a` (HEAD `423106cdc`), ports réservés 9630/6830. **Aucune correction, aucun
merge.** Les démonstrations se font sur la version **locale** (base Mac `labuse`, == données prod en
lecture) ; **la prod n'a été ni touchée ni sondée en écriture** — lecture/observation uniquement, et
jamais entre 01 h et 05 h Réunion. Lu d'abord : `docs/audit-2026-11/chasse-1/B/RAPPORT.md` (branche
`audit/chasse-1-b`), §droits et §Crédits — ce rapport **prolonge** la Chasse-1-B sans la répéter.

> **Intendance méthodologique (honnêteté).** En `env=local`, l'authentification est **DÉSACTIVÉE**
> (`auth.enabled()` faux, `exiger_admin` = no-op, `/moi` = `{mode:"local"}`). Conséquence : **les
> trouvailles de droits ne se « prouvent » pas par un `curl` local** (tout y répond 200, ce qui ne
> démontre rien sur la prod). Elles sont donc établies **par le code servi** — absence de paramètre
> `request`, absence d'appel `exiger_admin`, préfixe de routeur hors segment `/admin` (le seul que le
> fail-safe du middleware couvre) — exactement la méthode de la Chasse-1-B. La trouvaille 2FA est
> **prouvée en exécutant le module `auth` réel** (logique pure, sans base, sans réseau, sans prod).
> SQLi / en-têtes / dépendances / fichiers déposés : par lecture de code. Les secrets sont vérifiés
> **sans jamais imprimer leur valeur**.

---

## Les cinq chiffres

| Chiffre | Valeur |
|---|---|
| **Surfaces jouées** | injections (SQL · chemin · en-têtes · carte · recherche) ; connexion/2FA/session/quota ; routes mutantes sans rôle ; rate-limit ; webhook Stripe (signature + rejeu) ; secrets (code/journaux/API/bundle) ; en-têtes HTTP ; dépendances ; fichiers déposés (sources manuelles, captures Radar) + SSRF/traversée. |
| **Bloquant** | **0** |
| **Majeur** | **3** (2FA-COMPTEUR · AUDIT-INGEST · PISCINE-GLOBALE) |
| **Moyen** | **3** (VEILLES-CRON · SOURCES-TEST · DESABO-TOKEN) |
| **Mineur / notes** | **6** (appends non attribués · DDL sur chemin chaud · `sleep` bloquant · en-têtes · SSRF résiduel · taille de corps) + 2 notes d'hygiène (`.env` local · dumps cadastraux) |
| **Crédits** | **13 familles de défenses qui tiennent** (voir §Crédits) |

**Verdict de synthèse.** **Le socle de sécurité est solide** : zéro injection SQL exploitable (requêtes
paramétrées, identifiants interpolés whitelistés), webhook Stripe **signé + anti-rejeu en transaction**,
jeton de paiement **HMAC signé + TTL**, login **argon2id + verrou + messages neutres**, session
**vérifiée en base à chaque requête + logout qui révoque**, dépôts de fichiers **validés par signature
+ noms adressés-contenu + SVG désinfecté**, proxys **gardés contre la SSRF** (IP publique + allowlist +
pas de redirection), fail-safe `/admin` au middleware, cloison multi-tenant **sans IDOR** sur les routes
par-compte, et **démarrage fail-closed** (clé de signature, env, dev-mode). Les trouvailles sont de
**deux familles** : **(1)** la limite d'essais du **second facteur (TOTP) ne tient pas** — son compteur
vit dans un cookie que l'attaquant contrôle, et aucun verrou base ne gèle un compte après N échecs 2FA ;
**(2)** la **même classe de bug que la Chasse-1-B** — des routes qui **écrivent de l'état partagé**
(référentiel parcelles, exclusions globales, veilles d'autres comptes, cloche `event_log`) **montées
hors `/admin` sans `exiger_admin`** : un client payant non-admin les appelle. Six routes de plus que les
trois déjà signalées tombent dans ce trou, et deux d'entre elles ont un **effet cross-tenant persistant**.

---

## Trouvailles — MAJEUR

### NU4A-M1 — MAJEUR — Second facteur (TOTP admin) : la limite de 5 essais ne tient pas (compteur côté client) et aucun verrou base ne gèle le compte

- **Où** : jeton de défi 2FA `src/labuse/api/auth.py:273-292` (`defi_2fa` / `defi_2fa_lire`) ; boucle de
  vérification `src/labuse/api/app.py:1042-1111` (`login_2fa_submit`) ; vérif TOTP
  `src/labuse/comptes.py:539-553`.
- **Le défaut** : le nombre de tentatives consommées (`n`) vit **uniquement dans le cookie `labuse_2fa`**
  (`exp.uid.n.sig`, signé HMAC). À chaque code faux, le serveur **ré-émet** le cookie avec `n+1`
  (`app.py:1110`) et `defi_2fa_lire` refuse au-delà de `n>=5` (`auth.py:288`). Mais **c'est le client qui
  choisit quel cookie renvoyer** : il lui suffit d'**ignorer** le cookie `n+1` et de **rejouer toujours
  le cookie initial `n=0`** (valide 5 min). Le serveur ne garde **aucun état** d'essais 2FA : la vérif
  TOTP (`totp_verifier`) n'incrémente un compteur base **que sur SUCCÈS** (`dernier_pas`, anti-rejeu) —
  **un échec ne laisse aucune trace**, contrairement au login mot de passe qui, lui, a
  `echecs_login`/`verrouille_jusqu_a` (`comptes.py:384-388`). De plus `/login/2fa` est **public** → il
  **n'est même pas soumis au rate-limit 60/min** (hors `PREFIXES_PROTEGES`), et l'attaquant peut
  **re-frapper `/login`** avec le mot de passe (qu'il possède) pour **se délivrer un nouveau défi de 5 min
  à volonté**. La seule friction restante est `slow_failure()` = `time.sleep(0.4)` (cf. NU4A-m3).
- **Preuve (module réel, logique pure, sans base ni prod)** :
  ```
  $ PYTHONPATH=src python -c "from labuse.api import auth; \
      c0=auth.defi_2fa(42,0); \
      print(sum(1 for _ in range(1000) if auth.defi_2fa_lire(c0) is not None),'/1000 acceptés')"
  1000 /1000 acceptés        # la limite DEFI_2FA_ESSAIS_MAX=5 n'est JAMAIS atteinte
  ```
  (En rejouant le cookie `n=0`, `defi_2fa_lire` renvoie `(42,0)` indéfiniment ; il ne refuse que les
  cookies `n>=5` que l'attaquant n'a aucune raison de renvoyer.)
- **Repro (bout en bout)** : connexion admin `POST /login` (mot de passe correct) → cookie `labuse_2fa`
  (`n=0`). Boucler `POST /login/2fa` en **renvoyant toujours ce même cookie** et un `code` deviné ;
  quand le défi expire (5 min), re-`POST /login` pour en reprendre un neuf. Débit limité à ~2,5 essais/s
  par `slow_failure` (≈750 essais/fenêtre de 5 min), **sans jamais buter sur « 5 essais »** ni geler le
  compte.
- **Gravité** : **majeur**. C'est le **second facteur**, donc il faut déjà le mot de passe admin (verrou
  de login intact) — ce n'est pas un contournement en un coup. Mais la protection anti-force-brute du 2FA
  **annoncée (5 essais) est inopérante** : reste uniquement l'entropie TOTP (6 chiffres, fenêtre ±1 ≈ 3
  pas valides/10⁶) et les 0,4 s de délai. Aucun verrou, **aucune alerte** après des milliers d'échecs 2FA
  (le journal ne voit que des `2fa_echec` isolés). Un adversaire disposant du mot de passe peut marteler
  le TOTP en continu sans jamais être arrêté ni signalé — le coût d'une compromission du compte admin
  tombe de « impossible » à « probabiliste sur la durée ».
- **Ce qu'un attaquant en fait** : prise de contrôle **administrateur** (tout l'app, John, ops, gel de
  clients, re-scoring, config bilan…) par force brute soutenue du seul facteur TOTP, sous le radar.
- **Correctif de principe (hors mandat)** : compter les échecs 2FA **en base** par `uid` (comme
  `echecs_login`) avec verrou + alerte, et/ou soumettre `/login/2fa` au rate-limit — ne jamais faire
  reposer la limite sur une valeur portée par le client.

### NU4A-M2 — MAJEUR — `POST /audit/{reference,adresse,polygone}` : ingestion dans le référentiel `parcels` PARTAGÉ et cascade de scoring, SANS aucune garde

- **Où** : `src/labuse/api/app.py:9425-9444` (3 routes montées **directement sur `app`**, **sans
  paramètre `request`**, donc **aucune garde possible**, et **hors segment `/admin`**) →
  `src/labuse/audit.py:_evaluate` (`audit.py:52-62`).
- **Ce que ça écrit** : crée un `IngestionRun` (`audit.py:52`), appelle `ingest_parcels(..., origine="audit")`
  qui **INSÈRE dans la table globale `parcels`** (`audit.py:55`), puis `evaluate_parcels(ids, db,
  persist=True)` — une cascade DELETE+INSERT de scoring dans les tables partagées
  (`parcel_evaluations`/scores). **Aucun `compte_id` nulle part.** `/audit/polygone` accepte en plus une
  **géométrie GeoJSON arbitraire** (`AuditPolygonIn.geometry`) et ingère toutes les parcelles qu'elle
  recouvre.
- **Qui peut l'appeler** : tout compte **authentifié non-admin** (et tout le monde en `env=local`).
- **Pourquoi c'est une vraie trouvaille** : la route **sœur** `POST /parcels/{idu}/evaluate` fait la
  **même classe** d'écriture globale lourde et est **explicitement `auth.exiger_admin`** (`app.py:9394`,
  docstring « GATE ADMIN … écrivain lourd »). Ces trois-là ont été **laissées ouvertes** — oubli du même
  garde, pas un choix.
- **Repro** : `curl -b 'labuse_session=u.<sess-client>' -XPOST https://host/audit/adresse -H 'content-type:
  application/json' -d '{"q":"3 chemin de la Citerne 97417"}'` → ingestion + cascade, idu renvoyé.
- **Ce qu'un attaquant en fait** : **polluer le référentiel partagé** (`origine='audit'`) et les runs de
  scoring **vus par tous les tenants** ; forcer des **fetchs externes IGN/BAN + une cascade de scoring
  complète par requête** (amplification de ressources, scriptable). Devrait porter `exiger_admin` comme
  `/parcels/{idu}/evaluate`.

### NU4A-M3 — MAJEUR — `POST /modules/prospection-piscines/pas-une-piscine` : suppression de parcelle GLOBALE et cross-tenant, `idu` attaquant, sans garde ni contrôle d'appartenance

- **Où** : `src/labuse/api/modules.py:1475-1489` (préfixe routeur `/modules`, **hors `/admin`**, pas de
  `exiger_admin`).
- **Ce que ça écrit** : `INSERT INTO piscine_corrections (idu, motif, compte_id) … ON CONFLICT (idu) DO
  UPDATE SET motif = EXCLUDED.motif` — la clé de conflit est **`idu` SEUL** ; `compte_id` n'est qu'une
  **trace d'audit**, jamais un filtre. La docstring l'assume : « retire la parcelle du service (compteur,
  carte) **DÈS maintenant** » et « l'exclusion est **GLOBALE** ». `idu` vient du corps, **aucune
  vérification d'existence ni d'appartenance**.
- **Qui** : tout authentifié non-admin ; `idu` arbitraire.
- **Repro** : boucler `curl -b 'u.<sess>' -XPOST .../modules/prospection-piscines/pas-une-piscine
  -d '{"idu":"974...","motif":"x"}'` sur une liste d'IDU.
- **Ce qu'un attaquant en fait** : **retirer scriptablement des parcelles arbitraires** de la
  fonctionnalité « prospection piscines » (payante) **pour tous les tenants**, et **écraser le `motif`**
  d'une correction d'un autre compte. **Empoisonnement de données cross-tenant persistant** d'une
  fonctionnalité vendue. Devrait être `exiger_admin` (signal de qualité de donnée = décision opérateur).

---

## Trouvailles — MOYEN

### NU4A-Y1 — MOYEN — `POST /api/copilote-v2/veilles/evaluer` : exécute le CRON sur les veilles de TOUS les comptes, sans garde

- **Où** : `src/labuse/api/copilote_v2.py:182-187` (sans `request`, sans garde) → `copilote_v2/veilles.py`
  `evaluer_toutes(db)`. La docstring dit : « le CRON J+1 de prod appellera ceci ».
- **Le défaut** : `evaluer_toutes` balaie `veilles WHERE actif AND type = ANY(:t)` **sans filtre
  `compte_id`**, écrit des notifications (`creer_notification` → `event_log`) et **avance
  `last_evaluated_at`** sur les lignes d'**autres tenants**.
- **Repro** : `curl -b 'u.<sess-nonadmin>' -XPOST https://host/api/copilote-v2/veilles/evaluer`.
- **Ce qu'un attaquant en fait** : déclencher à volonté l'évaluation de **toutes** les veilles et
  **avancer les filigranes** d'autres comptes — ce qui peut **étouffer leurs futures alertes** (fenêtre
  de notification consommée) — et **déverser en masse** des notifications dans `event_log`. Job global à
  effet cross-tenant ; devrait être `exiger_admin` ou scopé au compte appelant.

### NU4A-Y2 — MOYEN — `POST /sources/{source_id}/test` : énumère le catalogue de sources GLOBAL et déclenche des appels sortants de connecteur, sans garde

- **Où** : `src/labuse/api/app.py:1592-1602` (monté sur `app`, **sans `request`**, hors `/admin`).
  `db.get(models.DataSource, source_id)` → `get_connector(src.name)` → `connector.test_connection()`.
- **Le défaut** : **toutes** les autres routes de gestion de sources vivent sous `/admin/sources/*`
  (`dashboard.py`) et sont donc fail-safe-gardées ; **celle-ci est la route égarée**, directement sur
  `app`. `source_id` entier → **énumération** (404 « Source inconnue » vs résultat distingue les sources
  existantes), et chaque appel **fait tirer un `test_connection()` sortant** côté serveur.
- **Repro** : `for i in $(seq 1 200); do curl -b 'u.<sess>' -XPOST https://host/sources/$i/test; done`.
- **Ce qu'un attaquant en fait** : cartographier le **registre `DataSource`** et son état (up/down =
  fuite d'info sur l'infrastructure d'ingestion), et provoquer des **requêtes sortantes** (effet de bord
  type SSRF, selon le connecteur). Pas d'écriture base — d'où « moyen » et non « majeur » —, mais c'est
  une surface **admin** ouverte à tout client.

### NU4A-Y3 — MOYEN — `POST /events/desabonner` + `/events/preferences` : écriture cross-tenant gardée par un seul jeton, comparé en clair (non temps-constant)

- **Où** : `src/labuse/api/events.py:1593` (`/events/desabonner`) et `:1660` (`/events/preferences`),
  garde `_token_ok` (`events.py:1571-1573`).
- **Le défaut** : la route accepte un `c` (n'importe quel `compte_id`) **choisi par l'appelant** et
  modifie l'abonnement e-mail / les préférences de **ce** compte. Le seul contrôle est
  `SELECT token FROM notif_prefs WHERE compte_id=:c` puis **`tok == t`** — comparaison **en clair, non
  temps-constant** — et le `c` **n'est jamais recoupé** avec le `request.state.compte_id` de la session.
- **Nuance honnête** : ce sont des liens de désinscription **RFC-8058** (un clic, sans session) — leur
  sécurité EST le jeton, par conception, comme `/events/desabonner` est d'ailleurs **public**
  (`auth._PUBLIC`). Mais `/events/preferences`, lui, **n'est pas public** : en prod, la garde globale
  exige donc une session, et **tout utilisateur authentifié** qui obtient/forwarde/devine le `token`
  d'un autre compte (lien de désinscription fuité, ou timing sur la comparaison non temps-constant) peut
  **désabonner ce compte et réécrire ses préférences**.
- **Ce qu'un attaquant en fait** : intégrité/disponibilité cross-tenant (la victime cesse de recevoir les
  mails LABUSE ; ses préférences sont réécrites). Atténué par le secret du jeton. Correctif : lier `c` à
  la session quand elle existe, et comparer avec `hmac.compare_digest`.

---

## Trouvailles — MINEUR & notes

### NU4A-m1 — MINEUR — Appends globaux non attribués / usurpables
- `POST /feedback` (`app.py:9563`) : `ParcelFeedback` global, **`user_id` pris verbatim du corps** →
  attribution forgeable, spam de signaux QA, tout IDU, tout authentifié.
- `POST /onboarding/suggestions` (`onboarding.py:876`) : append global dans une boîte, sans scope compte.
- `POST /api/copilote-v2/feedback` (`copilote_v2.py:236`) : append non scopé dans `copilote_telemetrie`
  (visible admin), `commentaire` jusqu'à 8000 car. Même classe « append non gardé », faible impact.

### NU4A-m2 — MINEUR — `POST /partners/share/{idu}` : DDL (`ALTER TABLE … ADD COLUMN IF NOT EXISTS` ×3) sur le chemin de requête
- `partners.py:207-219` (`_share_colonnes`) exécuté **à chaque appel**, déclenchable par tout authentifié
  non-admin. Idempotent, pas de perte de donnée, mais du **schéma modifié sur chemin chaud** → à déplacer
  au boot/migration.

### NU4A-m3 — MINEUR (disponibilité) — `slow_failure()` = `time.sleep(0.4)` BLOQUANT dans des handlers `async`
- Appelé dans `login_submit` (`app.py:944, 999`) et `login_2fa_submit` (`app.py:1095`), tous deux
  `async def`, via `auth.slow_failure()` → **`time.sleep` sur l'event-loop** : chaque échec de connexion
  **gèle le worker 0,4 s pour tout le monde** (sérialise aussi, incidemment, la force brute 2FA de M1).
  Marteler les échecs de login dégrade la latence de toutes les requêtes du worker. À déporter en
  thread/`anyio.to_thread` (comme le fait déjà `garde_protection`).

### NU4A-m4 — MINEUR — En-têtes HTTP : solides, deux durcissements manquants
- `_security_headers` (`app.py:531-562`) pose `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, HSTS (si HTTPS), et une **CSP raisonnable sans `unsafe-eval`** (`script-src 'self'`).
  Manquent : **`Permissions-Policy`**, **COOP/COEP** ; `style-src 'unsafe-inline'` (toléré pour
  React/maplibre, mais élargit un peu la surface XSS si un jour une injection HTML passe) ; le HSTS n'est
  posé qu'en HTTPS (correct) mais est **commenté côté nginx** (`deploy/`) — l'app le rattrape, ne pas le
  retirer de l'app.

### NU4A-m5 — MINEUR — SSRF résiduel (TOCTOU / DNS-rebinding) sur `/admin/radar/depot-agence/analyser`
- `pige/api.py:_resout_public` (`:1047`) résout l'hôte et rejette les IP privées, mais `requests.get`
  **re-résout** indépendamment → fenêtre de rebinding théorique. **Atténué** par l'allowlist stricte de
  domaines de portails (il faudrait contrôler le DNS d'un domaine famille leboncoin/bien'ici). Résiduel,
  pas exploitable en l'état ; noté pour durcissement (résoudre une fois puis se connecter à l'IP validée).

### NU4A-m6 — MINEUR — Pas de plafond de taille de corps applicatif
- Les dépôts Radar (image/HTML base64) et `/moi/logo` lisent `request.body()` entier ; seul `/moi/logo`
  cape (512 Ko, `marque.py`). Le reste s'en remet au reverse-proxy (`client_max_body_size`). Admin-only →
  faible ; poser un cap explicite sur le dépôt Radar.

### Notes d'hygiène (hors « vulnérabilité de code »)
- **`.env` local** : un fichier `.env` **gitignoré et NON suivi** (`git check-ignore` = `.gitignore:13` ;
  absent de `git ls-files`) contient des clés **d'allure vivante** (`rk_live_` Stripe, `sk-ant-`
  Anthropic, Brevo/INPI/SMTP). **Aucun secret n'est commité** (vérifié : `git grep` des motifs
  haute-entropie sur `HEAD` = vide ; seuls des `*.env.example` versionnés, avec placeholders). C'est une
  **note de poste de travail** : si ce Mac n'est pas de pleine confiance, **faire tourner ces clés** — la
  valeur n'a volontairement pas été imprimée ici.
- **Dumps cadastraux versionnés** : deux dumps SQL commités portent `siren`/`dirigeant_age` (donnée
  nominative). Note RGPD/PII, faible ; à sortir du dépôt si possible.

---

## Crédits — ce qui tient (défenses vérifiées, à NE PAS re-signaler)

1. **Injection SQL : clean.** Balayage complet (f-strings/`.format`/`%` dans `text()`, paramètres
   carte/recherche/tri) → toutes les **valeurs** sont **paramétrées** (`:t{i}`, `:lim/:off`, `:c`…), et
   les **identifiants interpolés** (colonnes, `ORDER BY`) viennent de **constantes/whitelists** serveur
   (`orders[sort]`, `_Q_V2_ORDERS_PAGE[...]`, `col` = expression pliée constante, `ordre` construit de
   littéraux) — jamais de l'entrée client. Vérifié sur `recherche.py`, `tiles.py`, `couches_tuyau.py`,
   `moteurs.py`, `app.py`.
2. **Webhook Stripe : signature OBLIGATOIRE + anti-rejeu en transaction** (`facturation.py:381-412`) :
   secret absent → `ConfigError` (refus) ; `construct_event` lève sur signature fausse ; dédup par
   `event_id` (PK `stripe_events`) **committée AVEC l'effet** (si le traitement rollback, la marque
   disparaît → Stripe rejoue → exactly-once). Le `client_reference_id` n'est lu que **dans l'événement
   signé**. Solide.
3. **Jeton de paiement** (`coffre_ui.pay_token`) : `compte_id.exp.HMAC`, TTL 30 min, `compare_digest`,
   non forgeable ; le Checkout est créé **serveur** avec le `cid` vérifié → pas d'activation d'un compte
   tiers.
4. **Login** (`comptes.verifier_login`) : **argon2id**, verrou `echecs_login`/`verrouille_jusqu_a`,
   message **neutre** (anti-énumération), rehash opportuniste. Reset : jeton haché, 1 h, anti-énumération.
5. **Session** (`comptes.session_utilisateur`) : vérifiée **en base à chaque requête** (suspension/essai
   échu/fin de période coupent au rechargement) ; logout **révoque** côté serveur ; cookie `httpOnly`,
   `SameSite=Lax`, `Secure` hors local. CSRF largement couvert par `SameSite=Lax` (POST cross-site non
   envoyés).
6. **Fail-safe `/admin` au middleware** (`app.py:651`, `_est_chemin_admin`) : tout chemin à segment
   `/admin` est forcé `role==admin`, indépendamment du garde en ligne.
7. **Cloison multi-tenant sans IDOR** : `projets` (12 routes), `crm_columns` (5), `watch-zones`,
   `pipeline`, `filters`, `financier`, `documents_bibliotheque`, `bilan_ratios`, `missions`/`veilles
   DELETE` — **tous filtrés par `compte_id`** avec 404 propres. Lecture directe confirmée (pas supposée).
8. **Dépôts de fichiers** (logo, Radar image/HTML) : validation **par signature** (pas le MIME déclaré),
   SVG **désinfecté** (`<script>`/`onX=`/`javascript:` rejetés), noms **adressés-contenu** (`sha256`),
   extensions whitelistées, jamais servis avec un Content-Type attaquant, jamais sur le FS depuis l'entrée.
9. **Proxys & SSRF** : `ortho_proxy` (couche whitelistée + `z/x/y` entiers bornés, hôte IGN fixe),
   `leboncoin` **fermé** (lookup DB only), `depot-agence` **gardé** (schéma + allowlist domaines + IP
   publique + `allow_redirects=False`). Pas de traversée (`FileResponse` par token→chemin DB, basename).
10. **Jeton Radar** (`auth.radar_token_header_ok`) : `hmac.compare_digest`, fail-closed, n'ouvre que
    4 endpoints de capture — jamais les routes de dépôt/validation (qui gardent `exiger_admin`).
11. **Anti-scraping** (`protection.py`) : rate-limit 60/min + défi, quotas fiches/tuiles/carto par
    jour/compte, filigrane d'export (HMAC + canaris), scan d'abus — gel **manuel** (pas d'auto-blocage).
12. **CORS non permissif** : `allow_credentials` défaut `False` (Starlette refuserait `*`+credentials) ;
    pas de secret dans les réponses/journaux/bundle front (vérifié).
13. **Démarrage fail-closed** : `exiger_secret_prod` (clé signature obligatoire hors local),
    `exiger_env_deploiement` (clé posée + `env=local` = refus), `exiger_pas_de_dev_mode_deploiement`
    (dev-mode hors local = refus).

---

## Classe systémique & dette

La racine commune de **NU4A-M2/M3, Y1/Y2** et des **trois déjà signalées en Chasse-1-B**
(`/partners/match/run`, `/events/detect`, `/events/demo`, routeurs `partners`/`events` **hors `/admin`**)
est **une seule** : *des routes montées hors du segment `/admin` qui écrivent de l'état partagé/global
mais n'ont jamais reçu le `exiger_admin` en ligne.* Le fail-safe du middleware ne couvre que `/admin` ;
les gardes corrects existants (`/bilan/params`, `/parcels/{idu}/evaluate`, `/partners/profiles`,
`/modules/division/compute`) montrent le motif attendu — ces routes-ci l'ont perdu. **Un correctif
structurel** (registre des « routes à mutation globale » vérifié au démarrage, ou **default-deny** sur
toute écriture hors `/admin` touchant une table partagée) fermerait la **classe entière** plutôt que
route par route.

**Dette / non testé** :
- Expiration de session réelle, verrou de login en direct, et le comportement live des routes gardées
  **ne sont pas démontrables en local** (auth off) — à rejouer en pilot/prod avec un compte de test
  non-admin (hors fenêtre 01–05 h Réunion).
- Les sévérités supposent la **prod** (auth active) ; en local tout répond 200 par conception.
- Aucune écriture prod, aucune attaque prod : les confirmations ci-dessus sont **par code** (routes) et
  **par exécution du module `auth`** (2FA), jamais par un tir sur la prod.
