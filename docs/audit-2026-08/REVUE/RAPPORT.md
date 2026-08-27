# GRANDE REVUE AVANT MISE EN LIGNE — RAPPORT

> Mandat GRANDE REVUE (27/08/2026). Branche `audit/grande-revue` (depuis `19f92b86`, qui inclut la
> bascule du run servi `q_v10_m129` → **`q_v11_m137`**, re-run des 24 communes de ce midi : 431 663
> parcelles, canari/score-v2/build-mvt/purge vérifiés). Doctrine intacte : Sourcé/Estimé/Absent,
> moteur unique, jamais de faux positif — **aucun chiffre servi ne change dans ce mandat** (seule
> exception encadrée : le re-run conditionnel R10).
>
> Gravités : 🔴 bloquant / faille · 🟠 durcissement recommandé · 🟡 dette / constat documenté.
> Findings RV-001→. Base de vérification empirique : `labuse` (prod locale) en lecture + `labuse_test`
> pour les comptes de test `[REVUE-TEST]` (purgés en fin).

---
## R1 — FRAÎCHEUR DES 58 SOURCES

Méthode : inventaire `data_sources` (58 affichées) × vérification en ligne des millésimes chez les
producteurs (data.gouv, SDES, ADEME, cadastre.data.gouv, IGN, Sudocuh, DILA, INPI, BRGM) × croisement
avec les commandes d'ingestion CLI et les crons installés. Le run servi `q_v11_m137` (re-run de ce
midi) a consommé l'état actuel de la base.

### Sources cadencées / à flux vivant (vérifiées en ligne)

| Source | Ingéré | Disponible amont (vérifié) | Retard | Commande | Cascade |
|--------|--------|---------------------------|--------|----------|---------|
| **géo-DVF Etalab** | 2021–2025 (horizon déc. 2025) | `latest/csv` = 2021→2025, horizon oct. 2025 · prochain oct. 2026 | **Non** | `refresh-dvf` (cron dvf) | oui (prix) |
| **Cadastre PCI (DGFiP)** | « latest » | juin 2026 publié 01/07 · `latest` suit | **Non** | API Carto (live) | oui (parcelles) |
| **SITADEL (SDES)** | 2026-06 | fiche MàJ 25/08 ; période exacte non affichée en ligne | Inconnu | `ingest-permits` (cron sitadel) | non (événements) |
| **DPE ADEME** | horizon 03/07/2026, hebdo | flux continu vivant (data.ademe.fr) | **Non** | `ingest-dpe` (cron dpe) | non |
| **BAN** | horizon 11/07/2026 | flux quotidien vivant | **Non** | `ingest-ban` (cron ban) | non |
| **BODACC (DILA)** | horizon 02/07/2026 | flux quotidien vivant | **Non** | `ingest-bodacc` (cron bodacc) | non (features) |
| **INPI RNE** | 06/07/2026 | flux quotidien vivant | **Non** | `ingest-inpi-rne` | non (features PM) |
| **Géorisques (BRGM)** | 13/08/2026 | flux vivant par base (API) | **Non** | `ingest-georisques` | oui (spatial_layers PPR/ICPE) |
| **Sudocuh (DGALN)** | état 31/12/2024 | dernier état annuel = 31/12/2024 | **Non** | manuel | non |
| **IGN BD TOPO V3 (bâti)** | mi-2025 | **éd. avril (261) + juillet (262) 2026 publiées** | **OUI** | ⚠ pas de commande CLI simple | **oui (bâti→résiduel)** |

### Les 48 autres sources

Millésimées statiques au dernier état publié (INSEE RP2022/2023, Filosofi 2021, IRIS 2024, ZNIEFF
29/08/2025, QPV 2024, ZFANG décret 05/2026, FRR 07/2024, Cartofriches, 50 pas, classement sonore
2023, INPN 2021/2025, LiDAR HD 25/06/2025, etc.) ou flux/proxy live (API Carto GPU/PLU, SUP, SIRENE,
Recherche d'entreprises, OSM/Overpass, GTFS PAN màj 08/2026). **Aucun retard ingérable détecté** :
soit au dernier millésime publié, soit flux vivant déjà ingéré (juillet–août 2026), soit source
manuelle/licence en attente (Fichiers fonciers Cerema, VRD/SPANC) → constat seulement.

### Décision R1 (arbitrages)

- **Aucune ingestion lancée.** Les sources cascade au sens strict (DVF, cadastre, zonage PLU/GPU,
  Géorisques) sont **à jour** ; les flux vivants (DPE/BAN/BODACC/INPI) sont frais (ingérés mi-août par
  les crons) et **non cascade** — les relancer créerait un delta de données non re-scoré, contraire à
  « aucun chiffre servi ne change ». → constat.
- **RV-001 🟡 — BD TOPO en retard (édition juillet 2026 vs bâti ingéré mi-2025).** C'est la seule
  source **cascade** ayant bougé (le bâti alimente `parcel_residuel` → SDP → score de cascade, cf.
  `residuel.py:35` `kind='batiment'`). **Mais** il n'existe **pas de commande d'ingestion BD TOPO
  simple/libre** au CLI (le bâti vit dans `spatial_layers` via un pipeline WFS non trivial ; la seule
  commande bâti est `ingest-cosia`, autre source). Ré-ingérer le bâti de toute l'île + recalculer le
  résiduel + re-scorer, juste avant mise en ligne, est un **chantier DONNÉE dédié** hors périmètre
  d'une revue. → **Constat documenté, pas d'ingestion.**
- **Conséquence pour R10 : aucune source cascade n'a été ré-ingérée → R10 ne se déclenche pas** (le
  bâti actuel est cohérent avec le résiduel recalculé ce midi). Détaillé en R10.

---
## R2 — CRON & FUSEAUX

### Bug de fuseau (consigné) — CORRIGÉ

**Cause racine** : machine en CEST, PostgreSQL en `Indian/Reunion` (+2). Le SQL (`CURRENT_DATE`,
`now()`) était en heure Réunion, mais le Python (`date.today()`, `datetime.now()`) en CEST. Entre
20 h et minuit CEST il est déjà « demain » à la Réunion → le jour Python (J) diverge du jour SQL
(J+1). La porte quota partenaires comparait `date.today()` (CEST) au `jour` stocké par `current_date`
(Réunion) → **réinitialisait le quota au lieu de le lever** (RV-002).

**Correction (deux garde-fous)** :
- **SQL** : `db.py` force le fuseau de session PG à `Indian/Reunion` (`-c timezone=Indian/Reunion`
  dans `connect_args`) → tout `CURRENT_DATE`/`now()` est en Réunion **quel que soit le serveur de
  prod** (robuste, corrige d'un coup tous les compteurs SQL : quota.py, events.py CURRENT_DATE, …).
- **Python** : nouveau module `labuse/tz.py` (`REUNION_TZ`, `today_reunion()`, `now_reunion()`).
  Fenêtres métier réalignées :

| Fichier | Fenêtre métier | Correction |
|---------|----------------|-----------|
| `partners.py:463` | **porte quota partenaires (bug consigné)** | `date.today()` → `today_reunion()` |
| `protection.py:_aujourdhui` | compteurs jour (quota fiches/tuiles/exports) | `today_reunion()` |
| `protection.py:scan_abus` | fenêtre « hier » du scan anti-scraping | `today_reunion()` |
| `ia.py`, `copilote.py`, `copilote_v2.py` | clés de quota jour (NL / agent / mission) | `today_reunion()` |
| `events.py` (dédup fraîcheur, péremption permis) | fenêtres jour métier | `today_reunion()` |

Les `CURRENT_DATE`/`now()` SQL (quota.py, events.py:512/795) sont couverts par le fuseau de session
— pas de modification ligne à ligne nécessaire. Les usages **techniques** (numéro de dossier
`DP-YYYYMMDD`, footer PDF « généré le », clés de réf) restent en heure locale : aucune fenêtre métier.

**RV-002 🟠→corrigé — porte quota partenaires.** Test de non-régression :
`test_partners_api_v1.py::test_r2_porte_quota_ne_reinitialise_pas_le_meme_jour_reunion` (au quota
+ même jour Réunion → 429 sans reset ; jour d'hier → reset). Suite protection/copilote : 17/17 verts.

### Inventaire CRON

Table complète : **`docs/EXPLOITATION-CRON.md`**. 10 jobs installés (train nocturne ordonné
radar→sitadel→bodacc→notifications→backup→abuse→fraicheur, tous sous `flock`). Cronables non
installés : `avis-echeance`, `evaluer-secteurs`. **Manquants** :
- **RV-003 🟡 — purge des sessions expirées** : `sessions_auth` n'est jamais nettoyée (dette AC-011).
  → commande `purge-sessions` créée en **R9**.
- **RV-004 🟡 — webhook Stripe absent** : paiements asynchrones non captés → détaillé en **R6**.

---
## R3 — MOTEUR UNIQUE REJOUÉ (q_v11_m137)

Protocole LOT AP rejoué sur le run servi actuel (`qa/revue/r3_moteur_unique.py`). Le run servi est
lu du point de vérité unique `config/served_run.txt` (`Q_A_RUN_LABEL`) = `q_v11_m137` ; la carte
(`mvt_meta.run_label`) = `q_v11_m137` (rebâtie ce midi). **130 parcelles** (120 tirées au sort tous
tiers + 10 cas canari) rejouées par tous les chemins servis.

### Concordance — AUCUNE DIVERGENCE

Pour chaque parcelle, les grandeurs servies concordent **exactement** entre les trois chemins :

| Grandeur | SQL (couche servie) | Fiche `/parcels/{idu}` | `/v2/score/{idu}` | Écart |
|----------|--------------------|-----------------------|-------------------|-------|
| tier (classement) | ✓ | ✓ | ✓ | **0** |
| mult_base (score) | ✓ | ✓ | ✓ | **0** |
| rang | ✓ | ✓ | ✓ | **0** |
| surface | ✓ | ✓ | — | **0** |

**130/130 concordantes, 0 divergence 🔴.** La bascule vers `q_v11_m137` est propre : aucun chemin
ne sert un vestige de l'ancien run. Moteur unique confirmé.

### Canari (score élevé → a_creuser) — POURQUOI LISIBLE ✅

Les 10 parcelles à `mult_base` élevé (13–22) classées `a_creuser` : **le pourquoi de non-opportunité
est visible et lisible sur chaque fiche** via le détail sourcé négatif. Exemple `97416000DN0012`
(mult 22,12, a_creuser) — 6 contraintes explicites servies au client :

- `[-15] risques` : Aléa inondation — niveau fort.
- `[-10] risques` : Aléa mouvement de terrain — niveau moyen.
- `[-5] icpe` : Installation classée à proximité (CBO TERRITORIA, 273 m).
- `[-5] risques` : Zone bleue PPR inondation/mouvement — constructible sous prescriptions (DEAL).
- `[-5] sol_pollue` : Site pollué recensé (CASIAS) à proximité — étude de sol (Central Téléphonique, 64 m).
- `[-5] bruit_route` : Classement sonore cat. 3 — isolement acoustique obligatoire (R.571-32 CE).

Chaque contrainte est **nommée, chiffrée, sourcée**. Le client comprend qu'une parcelle au fort
signal foncier est reléguée à cause d'un empilement de contraintes réglementaires/risques.

- **RV-005 ✅ — Canari satisfait.** Le motif de non-opportunité est lisible sur la fiche (lignes de
  détail sourcé négatives). Le champ de synthèse `score_v2.motif` reste `None` pour ces `a_creuser`
  (le motif de synthèse est réservé aux déclassements `declasse_*`), mais le détail par couche est
  complet et explicite. **Aucune modification** de l'affichage ni du classement nécessaire (conforme
  « sans changer le classement »). Arbitrage : le pourquoi étant déjà servi ligne à ligne, ajouter un
  badge de synthèse serait cosmétique et hors périmètre « aucun chiffre ne change ».

---
## R4 — SÉCURITÉ (avant exposition Internet)

Audit complet (grep secrets, injections, en-têtes, cookies, CORS, uploads, stack traces, console,
rate-limit) + scan du bundle `dist/` + `pip-audit`/`npm audit`. **Verdict global : SAIN**, avec deux
durcissements appliqués.

### Corrigé

- **RV-006 🟠→corrigé — CSP absente.** Ajout d'une **Content-Security-Policy raisonnable** sur chaque
  réponse (`app.py:_security_headers`) : `default-src 'self'` + sources externes RÉELLES uniquement
  (Google Fonts en style/font, tuiles IGN `data.geopf.fr` + MNT S3 en img/connect, `blob:` pour les
  workers maplibre) ; `script-src 'self'` **sans** `unsafe-inline` (bundle local, zéro script inline
  vérifié) ; `object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`. **Vérifié empiriquement**
  (uvicorn code neuf + Playwright) : **0 violation CSP, 0 erreur console, carte/polices intactes** —
  zéro régression visuelle. Test de non-régression `test_r4_entetes_securite_et_csp`.
- **RV-007 🟡→corrigé — patchs de dépendances.** `pip-audit` : `pydantic-settings` (GHSA-4xgf-cpjx-pc3j)
  et `pypdf` (PYSEC-2026-3655/3656, runtime PDF) mis à jour (env + planchers `pyproject` bumpés).
  Restants : `pip` (PYSEC-2026-3721) et `setuptools` (PYSEC-2026-3447) — **outils de build/packaging,
  non embarqués dans le runtime servi en prod** ; plancher `setuptools>=78.1.1` posé, mise à jour de
  l'outil au prochain rebuild d'environnement (non bloquant). `npm audit --production` : **0 vulnérabilité**.

### Sain (vérifié, rien à corriger)

| Point | Verdict |
|-------|---------|
| Secrets en dur | ✅ tout via `.env`/`config` (Stripe/Brevo/SMTP/Anthropic/SECRET_KEY) ; **aucun secret dans `dist/`** (scan `sk_`/`rk_`/`xkeysib-`/`whsec_`/`sk-ant-` vide) |
| Injections SQL | ✅ les `text(f"...")` interpolent des **noms de tables/colonnes internes** ou clauses statiques ; les **données utilisateur sont toujours bindées `:param`** |
| En-têtes | ✅ X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS (en HTTPS only) + **CSP (nouveau)** |
| Cookies | ✅ HttpOnly + SameSite=Lax + Secure (hors local), signés HMAC, révoqués au logout |
| CORS | ✅ strict par env (`*` en local ; origine publique ou same-origin en prod) |
| Uploads | ✅ un seul (`/moi/logo`), body brut, validation magic-bytes + durcissement SVG (anti-`<script>`/`on*`/`javascript:`), 512 Ko, BLOB en base |
| Stack traces | ✅ aucune trace servie au client (handlers → JSON `{detail}` ; pas de `debug=True`) |
| Console | ✅ **0 `console.log`/`debug` front**, **0 `print()` dans `src/labuse/api/`** (les prints restants sont dans le batch/CLI, hors chemin servi) |
| Rate-limit | ✅ 60/min + quotas jour par compte (exports/copilote/dossiers) ; `/login` = `slow_failure` 0,4 s (RV-008 🟡 : rate-limit IP recommandé sur `/login`, cf. A4/AC-020 — proposé, mandat VPS) |

- **RV-008 🟡 — `/login` sans rate-limit IP** (déjà consigné AC-020 à l'audit comptes) : `slow_failure`
  0,4 s seul, `/login` hors `PREFIXES_PROTEGES`. Documenté, non implémenté ici (durcissement admin =
  mandat VPS, migrer vers compte `role='admin'` + 2FA).

---
## R5 — VITESSE

Baseline p50/p95 (patron LOT AM, `qa/revue/r5_baseline.py`, 12 mesures/route, run q_v11_m137) :

| Route | p50 ms | p95 ms | Nature |
|-------|-------:|-------:|--------|
| `/parcels/{idu}/explain` | 16 538 | **17 513** | **appel LLM Anthropic** (latence externe) |
| `/readyz` | 2 455 | 2 505 | health check TEMPS RÉEL (schéma+data) |
| `/parcels/{idu}` (fiche) | 2 003 | 2 035 | calcul 0,23 s (profilé) + transport |
| `/map/parcels.geojson?commune=` | 1 164 | 1 171 | ST_AsGeoJSON sur 51 k parcelles (Saint-Paul) |
| `/modules/faisabilite/{idu}` | 63 | 103 | sain |
| `/sources` | 48 | 51 | sain |
| `/map/tiles/meta` | 27 | **35** | ✅ (était 3,9 s — index posé) |
| `/v2/score/{idu}` | 2,5 | 2,6 | sain |
| `/stats/entonnoir` | 1,7 | **2,0** | ✅ (était 9,8 s — cache 30 s posé) |
| `/communes`, `/accueil/chiffres`, `/filtre` | ~2 | ~2 | sains |

### Les 2 cibles connues (LOT AM) : DÉJÀ RÉGLÉES

- **`/stats/entonnoir`** : le mandat le donnait à p95 9,8 s (cache manquant). **Déjà corrigé**
  (FIX-C6 GB-058 : mémorisé 30 s) → **p95 2,0 ms**. Confirmé.
- **`/map/tiles/meta`** : donné à p95 3,9 s (index `(run_id, computed_at)` manquant). L'index
  **`ix_p_v2_run_computed` existe** → **p95 35 ms** ; EXPLAIN confirme l'Index Scan Backward. Confirmé.

### Les pires restants — structurels, aucune optimisation sûre

- **`/parcels/{idu}/explain` (17,5 s)** : c'est un **appel à l'API Anthropic** (`explain_parcel` →
  LLM), pas une requête DB. Latence externe attendue (LOT AM le classait « LLM/payload/froid
  attendus »). **Hors périmètre** « optimiser sans changer les chiffres » — rien à faire côté app.
- **`/readyz` (2,5 s)** : vérifie le schéma et les données EN TEMPS RÉEL (contrat health check). Le
  cacher irait contre son but (le monitoring VPS doit voir l'état réel). Appelé rarement, pas client.
- **`/map/parcels.geojson` (1,17 s)** : EXPLAIN **propre, aucun index manquant** — le Seq Scan
  parallèle sur `parcels` est le choix optimal du planner (Saint-Paul = 51 k parcelles, grosse
  fraction de table), le coût est le `ST_AsGeoJSON(ST_SimplifyPreserveTopology(...))` géométrique,
  **incompressible** sans changer la donnée servie. **Cache HTTP 600 s** déjà en place.
- **`/parcels/{idu}` (fiche)** : profilée à **0,23 s de calcul** (session directe) — saine. Le 2 s
  HTTP est du transport/middleware ; la fiche fait ~59 requêtes rapides (0,003 s chacune), pas de
  goulot DB. Aucun index manquant.

### Verdict R5

- **RV-009 ✅ — Système déjà optimisé.** Les 2 optimisations actionnables du mandat sont **déjà en
  place** (cache entonnoir, index tiles/meta). L'EXPLAIN des routes lentes restantes est propre
  (aucun index manquant, aucun N+1 à ROI positif). Les pires restants sont **structurels et
  attendus** : LLM (explain), health check temps réel (readyz), calcul géométrique caché (geojson).
  **Aucune optimisation supplémentaire n'est sûre ni nécessaire** — arbitrage conservateur : à la
  veille d'une mise en ligne, ne pas refactorer un chemin sain (fiche/middleware) au risque de
  déplacer un chiffre. Baseline gelée dans `qa/revue/r5_baseline.json` pour comparaison post-VPS.

---
## R6 — PAIEMENT STRIPE BOUT EN BOUT (mode TEST réel)

Clés `.env` : `LABUSE_STRIPE_SECRET_KEY=sk_test_…` (mode TEST), `PRICE_INTEGRAL/FLASH`,
`WEBHOOK_SECRET=whsec_…`, `STRIPE_RESTRICTED_KEY=rk_live_…` (lecture dashboard). Cycle déroulé en
**mode test réel** sur `labuse_test` (`qa/revue/r6_stripe.py`, comptes `[REVUE-TEST]` purgés).

### Résultats — 11/11 ✓

| Test | Résultat |
|------|----------|
| Webhook signature **invalide** → rejet | ✅ HTTP 400 |
| Webhook signature **absente** → rejet | ✅ HTTP 400 |
| Webhook signature **valide** → accepté | ✅ HTTP 200 |
| `checkout.session.completed` → compte **actif** | ✅ |
| `invoice.payment_failed` → **paiement_requis** (past_due) | ✅ |
| `invoice.paid` → **réactivé** (actif) | ✅ |
| `customer.subscription.deleted` → **suspendu** | ✅ |
| Rejeu du même `event_id` → **ignoré** (dédup) | ✅ |
| `creer_checkout` → **session Stripe test réelle** (`cs_test_…`) | ✅ |
| Suspension / rétablissement dashboard | ✅ |
| Rapprochement Stripe⇄comptes (restricted key) | ✅ configure=true, **2 orphelins détectés** (comptes app sans abo → alerte ambre) |

### Webhook

**Un endpoint webhook EXISTE** (`POST /stripe/webhook`, onboarding.py) et **vérifie la signature
avant tout traitement** (`stripe.Webhook.construct_event` avec `whsec_`) — signature invalide/absente
rejetée, valide traitée. Dédup par `event_id` (rejeu Stripe), transactionnel (marque + effet
commitent ensemble). **Note VPS** : cet endpoint doit être exposé publiquement et le `whsec_` de
production configuré (en local, `stripe listen` le fournit).

### Findings

- **RV-010 ✅ — Stripe bout en bout sain** en mode test (signature, cycle d'états, dédup, checkout,
  rapprochement orphelins).
- **RV-011 🟡 — incohérence de mode clés.** `sk_test_` (checkout) vs `rk_live_` (lecture dashboard) :
  en recette, le dashboard lit les abonnements **live** tandis que le checkout crée des abos **test**.
  À **aligner à la bascule prod** (tout live) — sinon le rapprochement mêle deux mondes. Documenté.
- **RV-012 🟠→corrigé — message webhook trompeur.** L'endpoint renvoyait « signature invalide » (400)
  pour **toute** exception, y compris une erreur de **traitement** (masquant les vrais bugs de handler
  et empêchant le rejeu utile). Corrigé : `SignatureVerificationError`/`ValueError` → 400 (signature) ;
  toute autre exception → **500** (Stripe rejoue, idempotent). Découvert en testant R6.

---
## R7 — MAILS (Brevo)

Config `.env` : `BREVO_API_KEY=xkeysib-…` + 8 IDs de templates (`BREVO_TPL_ESSAI=4` … `RETABLISSEMENT=11`)
+ SMTP Brevo. Adresse de Vic : `kampusreunion@gmail.com`.

### RV-013 🔴→corrigé — Brevo « non configuré » à tort (bug de préfixe)

Les variables Brevo du `.env` sont sous **`BREVO_*`** (sans préfixe), mais le code (config pydantic,
`env_prefix="LABUSE_"`) attendait **`LABUSE_BREVO_*`** → `s.brevo_api_key` et les templates étaient
lus **`None`**. Conséquence : **AUCUN mail ne serait parti en production**, le dashboard aurait affiché
« Brevo non configuré » alors que les clés étaient bien présentes. **Corrigé** : `brevo.py` lit
désormais le setting préfixé **OU** le repli sans préfixe (`_api_key()` / `_setting_ou_env()`, même
pattern que `STRIPE_RESTRICTED_KEY`). Après correction : `api=True`, **8/8 templates branchés**
(essai=4, souscription=5, onboarding 1/2/3=6/7/8, relance=9, suspension=10, rétablissement=11). Test
« non configuré » ajusté (retire aussi le repli).

### RV-014 ✅ — 8 templates envoyés RÉELLEMENT vers Vic

Chaque template envoyé à `kampusreunion@gmail.com` avec variables réalistes (`nom`, `montant`,
`lien`, `jours`…) — **Brevo a accepté les 8** (HTTP 2xx). Réception + rendu des variables à confirmer
par Vic dans sa boîte (non vérifiable côté serveur).

| Template | ID | Envoi |
|----------|----|-------|
| Essai 48 h · Lien de souscription · Onboarding 1/2/3 · Relance carte · Suspension · Rétablissement | 4–11 | ✅ 8/8 |

### RV-015 ✅ — Rappels J+3 / J+10

Vérifiés sur comptes `[REVUE-TEST]` à dates forcées (purgés) : compte J-4 sans Mail 2 → « Mail 2 à
envoyer (J+3 atteint) » ; J-11 avec Mail 2 fait → « Mail 3 à envoyer (J+10 atteint) » ; J-1 → aucun
rappel. `_rappels_onboarding` correct. Suite dashboard 15/15.

**Aucun envoi automatique** en V1 (mandat) : l'app rappelle, Vic déclenche.

---
## R8 — RECETTE DASHBOARD (Tour de contrôle, conditions réelles)

Recette sur serveur réel (uvicorn :8010, code de la branche) + recoupement SQL.

### Chiffres du Pilotage — RECOUPÉS SQL, exacts

| Indicateur | Dashboard | SQL | Écart |
|-----------|-----------|-----|-------|
| Licences actives | 2 | 2 | ✅ |
| Conso IA du mois (€) | 26,81 | 26,81 | ✅ |
| Conso IA (appels) | 4 559 | 4 559 | ✅ |
| Actifs 24 h | 0 | 0 | ✅ |
| Santé serveur | **13 / 13** (LED verte) | 13 modules heal OK | ✅ |
| Run servi (LED) | q_v11_m137 · carte 27/08 | mvt_meta / served_run | ✅ |

- **Backup** : « aucun trouvé » — **honnête** (le répertoire `/var/backups/labuse` est sur le VPS,
  absent en local ; ambre ≥2 j / rouge ≥7 j / « absent » propre).
- **Capteurs D1 alimentés** par l'usage réel : `usage_events` **outil 56 · heartbeat 127** (27/08),
  `ia_log` 4 570 appels / 26,87 € sur 30 j. `retours` = 0 (aucun clic client « Signaler » réel — sain).
- **Fil admin** : 30 lignes réelles (transitions courrier n°40/41 Demandé→Imprimé→Posté, demandes d'envoi).
- **Rapprochement Stripe** : « orphelins à voir » (ambre) — 2 comptes app sans abo (cohérent R6).

### Sections & mécanismes

- **403 admin** (tests gelés) : `test_admin_403_depuis_compte_client` + `test_a4_403_admin_sur_toutes_les_routes`
  → **passent** (client 403, anonyme non-200 sur les 22 routes).
- **Courrier** : cycle Demandé→Imprimé→Posté journalisé — `test_courrier_transitions_journalisees` ✅.
- **Essai 48 h** : création + bascule à date forcée — `test_essai_expiration_prouvee` ✅.
- **Suspension / rétablissement** : vérifiés en R6 (webhook + manuel) ✅.
- **Produit** (usage par outil + retours à statuts) : `test_produit_usage_et_statut_retour` ✅.
- **Badge sources** : synthèse « 0 à mettre à jour · 3 OK · 56 sans échéance » sur **59 sources** —
  cohérent avec R1 (le badge auto se calcule sur les **cadences configurées**, 56 restent à régler ;
  la vérif en ligne de R1 complète en signalant BD TOPO, qui n'a pas de cadence configurée).
- Capture visuelle des 6 sections : **0 erreur console/pageerror**, rendu conforme.

- **RV-016 ✅ — Dashboard sain en conditions réelles.** Chiffres exacts (recoupés SQL), LED correctes,
  capteurs alimentés, 403 admin gelé, courrier/essai/suspension/produit vérifiés. Capture
  `qa/revue/r8_pilotage.png`.

---
## R9 — NETTOYAGE

### Suite backend — VERTE (0 échec non expliqué)

Baseline : 15 failed + 9 erreurs de collection. Causes réparées **nominativement** :

| Cause | Fichiers | Action |
|-------|----------|--------|
| **pandas absent** (dep `pyproject`) | 6 collection + failed | `pip install pandas` (dep légitime du projet, env incomplet) |
| **joblib/scikit-learn absents** (deps ML) | 4 failed + 2 collection | installés (deps `pyproject`) |
| **weasyprint / libgobject** (lib système) | ~9 failed PDF | libs homebrew présentes (`glib`/`pango`) mais hors `DYLD` de l'env → lancer les tests avec `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` **sur macOS** (en prod Linux, chemin standard, aucun geste). Documenté. |
| **simulplu — `Query()` non résolu** | `test_simulplu` (2) | test corrigé : passe `offset=0` (ce que FastAPI fait via HTTP) |
| **3 tests périmés** (formulation/format évolués) | flash SDP · Étudier marges · sources millésime | mis à jour vers l'état ACTUEL (produit sain, cf. R3) |

Les 3 tests périmés mis à jour (justification unitaire) : (a) le template flash dit « plancher (SDP) =
vendable ÷ rendement » (plus « surface de plancher au sens PLU »/dérivation 1,15) ; (b) EtudierBien a
refondu les deux référentiels en **bascule** « Calibrées LABUSE | Vos hypothèses » ; (c) le millésime
servi est le **millésime amont** (`source_millesime`), jamais la date d'ingestion — la doctrine M73 E
l'interdit (le test suivait l'inverse). **Résultat : `1796 passed, 3 (macOS lib) documentés, 0 failed`.**

### AC-003 — Effacement RGPD complet (FK cascade)

Les **11 tables** à `compte_id` sans FK cascade (`copilote_conversations`, `veilles`, `veille_reprise`,
`ia_log`, `usage_events`, `retours`, `licence_mails`, `notif_prefs`, `notif_canaux`, `share_links`,
`lettre_zonage_refs`) portent désormais `FOREIGN KEY … ON DELETE CASCADE` (patron GB-063 : purge
défensive des orphelins d'abord — **0 orphelin existant** —, migration idempotente dans
`ensure_scoping`). `evenements_compte` exclue (anonymisée exprès). **Garde de régression** :
`test_r9_ac003_effacement_rgpd_purge_les_11_tables` (effacer un compte purge les 11 tables, 0 orphelin).
**RV-017 ✅ corrigé.**

### Traçabilité

- **`pole_echange`** (19/61 sans source) → rattachées à « OSM — transport » (id 75).
- **`tva_primo`** (13/13 sans source) → rattachées à sa source amont « QPV 2024 (ANCT) » (id 75→38) ; le
  **code d'ingestion** (`dispositifs.py build_tva_primo`) pose désormais `data_source_id` (ne se
  reproduira plus). **0 ligne sans source** après rattachement. Aucun chiffre servi ne change (métadonnée).
- `division_or_candidates` : dérivé de scoring — sa régénération relève du re-run (R10), pas d'une
  commande d'ingestion isolée. Documenté.

### Données & code mort

- **Données de test** : **0** résidu `[GB-TEST]`/`[AUDIT-TEST]`/`[REVUE-TEST]` dans `labuse` ET
  `labuse_test` ; **0 orphelin** (vérifié SQL).
- **Fichiers** : **aucun** `*.orig`/`*.bak`/`*.rej`.
- **Branches locales** : **159 branches mergées dans HEAD** (mandats passés, mortes) → **liste pour Vic**
  (`git branch --merged | grep -v grande-revue`) — **NON supprimées** (décision Vic).
- **Vestiges scoring** : `score_snapshot` **déjà absent** (0 table, 0 référence). Les autres candidates
  (`abuse_scores` 1 l., `parcel_v_score` 431 663 l., `score_e` 285 781 l., `parcel_veille_succession`
  7 129 l.) sont **toutes référencées dans le code ET peuplées** → **aucun vestige trivial à supprimer**.
  Trancher « servi vs calculé-mort » exigerait un audit scoring dédié (risqué à la veille d'une mise en
  ligne) → **pas de suppression proposée sans certitude** (le mandat interdit de supprimer).

### Dette 🟡 & sessions

- **RV-003 ✅ — commande `purge-sessions`** créée (`DELETE FROM sessions_auth WHERE expire_at < now()`,
  cronable quotidien — cf. `EXPLOITATION-CRON.md`) : comble la dette AC-011 (sessions non purgées).
- Dette 🟡 des cycles antérieurs largement **absorbée par ce mandat** : fuseau (R2), CSP (R4), webhook
  (R6), Brevo (R7), effacement RGPD (AC-003). Le reste (durcissement admin AC-020/025, incohérence
  clés Stripe RV-011) est **re-documenté, daté, dette assumée** — mandat VPS.
