# PRÉ-VOL M7 — la moitié locale du déploiement (mode autonome total)

Branche `prevol/m7` · un lot = un commit [P1]…[P7] · Vic absent (zéro sollicitation) · STOP final à son
retour. Interdits tenus : aucun ssh VPS, aucun début de M7, aucun refactor des monolithes, aucune écriture
DB destructive hors la base de répétition P3.

---

## P1 · Câblage ingest-permits ✅

**Constat** : le **cron de prod était DÉJÀ sur la voie vivante** (`deploy/cron.d/sitadel` →
`python -m labuse.ingestion.permits_sdes --refresh`) — mais la **commande CLI `ingest-permits` appelait
encore la voie MORTE** (`permits.ingest_permits`, ODS Région, plus alimentée depuis 2023-09).

**Fix** : la commande CLI est rebranchée sur `permits_sdes.run(refresh, geocode)` (flux national
SDES/Dido, Sitadel3, dép. 974, MAJ mensuelle) — mêmes options que le cron (`--refresh` = delta avec
recouvrement 3 mois ; défaut = backfill complet). `geocode-permits` inchangée (helper cadastre VIVANT de
permits.py, générique). La voie ODS reste en legacy documenté, appelée par personne.

**Preuve du câblage final** (`tests/test_ingest_permits_cablage.py`, 4/4 verts) :
1. appel CLI mocké → `permits_sdes.run(refresh=True, geocode=True)` reçu (le chemin de code, prouvé) ;
2. défaut = backfill (`refresh=False`) ;
3. le cron.d pointe `permits_sdes --refresh` et jamais la legacy ;
4. grep : `ingest_permits(` (ODS morte) n'a plus AUCUN appelant dans src/.

## P2 · Le golden apprend les cibles distantes ✅

- `qa/golden_check.py` : cible paramétrable — **`--base-url`** (prime) > **`LABUSE_QA_TARGET`** >
  `LABUSE_API_BASE` (compat) > défaut `localhost:8010` **inchangé**. La face DB suit
  `LABUSE_DATABASE_URL` (déjà paramétrable) — pour un golden VPS complet : `LABUSE_QA_TARGET` (API)
  + `LABUSE_DATABASE_URL` pointée sur la base du VPS (tunnel), ou exécution sur place.
- `tests/test_run_serving_coherence.py` : nouveau test `test_mvt_run_label_cible_distante` — si
  `LABUSE_QA_TARGET` est défini, la cohérence du run servi est vérifiée contre `/map/tiles/meta` de la
  CIBLE (l'endpoint expose `mvt_meta.run_label`) ; sans l'env → skip, comportement par défaut inchangé.
- **PREUVE (le geste exact de M7)** : instance de main lancée sur `:8011` (pattern M3) →
  `golden_check.py --base-url http://127.0.0.1:8011` = **116/116 PASS** ; idem via `LABUSE_QA_TARGET`
  = **116/116 PASS** ; `test_run_serving_coherence` distant : 4/4.
- **Finding rate-limit (piège documenté re-confirmé)** : deux goldens enchaînés contre la même instance
  sans `LABUSE_DEV_MODE=1` → 4 FAIL par throttle 429 (pas une régression). M7 devra lancer le golden
  VPS avec dev_mode actif ou espacer les runs.

## P4 · Kit deploy/ complété (écrit, pas exécuté) ✅

**Inventaire des manques → écrits en idempotent, rien exécuté sur un VPS (aucun ssh) :**
| Manque | Livré |
|---|---|
| **Cron mort-vivant** : `deploy/cron.d/solaire` appelait 7 commandes retirées par M3 (aurait planté chaque mois) | **Retiré** (les données solaire dorment, aucune tâche ne doit tourner) |
| Aucun cron n'appelait `backup_postgres.sh` | `deploy/cron.d/backup` (3h, quotidien) |
| Pas de rapatriement des sauvegardes | `deploy/scripts/pull_backups.sh` — **pull depuis le poste local** (le VPS ne détient aucun credential vers chez nous), rsync delta + rotation locale + contrôle `pg_restore --list` |
| Pas de procédure ufw | `deploy/scripts/ufw_setup.sh` — SSH rate-limité EN PREMIER, garde anti-lock-out (abandon si la règle SSH manque), enable en dernier |
| Pas d'état des crons observable | **`GET /healthz/crons`** (routeur additif `api/ops.py`, public comme /healthz) : âge du dernier passage lu dans `ingestion_runs`/`data_sources.last_sync_at` — un cron mort se voit en un GET ; « jamais_vu »/« non_trace_db » honnêtes, jamais un faux OK |
| `.env.example` : ~10 variables sur ~40 | Complété : `LABUSE_SERVED_RUN` (+ warning VITE_RUN_LABEL/build-mvt), quotas/anti-abus, `LABUSE_DEV_MODE`, INPI, Stripe (Flash), Merci Facteur, SMTP, `LABUSE_QA_TARGET` (P2), rotation locale backups — placeholders, zéro secret |

Vérifié en local : `/healthz/crons` sur la base réelle → sitadel ok (11 j), ban ok (10,8 j), catnat
« jamais_vu » (vrai : jamais tourné ici), abuse/backup « non_trace_db » (documenté).
`tests/test_ops_healthz.py` 3/3 (dont : le cron solaire mort ne réapparaît pas).

## P6 · F6 — skip ortho : RÉSOLU (fix trivial, skip levé) ✅

Le « drift ortho » n'était **pas dans le code ortho** : `parcel_residuel_bati` a 11 colonnes (`commune`
en 2ᵉ position) et l'INSERT **positionnel** du test mettait `120` dans `commune`, laissant
`emprise_batie_m2` NULL → contexte 0.0 → candidat rejeté (`sans_contexte`) → `NoResultFound`. Même
famille que F3/F5 : **test périmé, code correct**. Fix : colonnes explicites ; **skip levé** ;
`test_ortho_detection` **5/5**. F6 clos dans PHASE0_FINDINGS.

Au passage (mise en cohérence documentaire, pas un fix silencieux) : **F7** était encore « reporté » au
doc alors que la nuit N4 l'avait traité (vérifié dans le code : `ext_sql.py` ne committe plus, commit
délégué à la frontière CLI aux 4 sites) — statut aligné. **Plus aucun finding Phase 0 bloquant ouvert** ;
restent 4 « reporté » assumés hors périmètre (noyau 30→32, wordings, outil de revue) qui sont des
décisions produit, pas des dettes techniques.

## P3 · Répétition de migration à blanc ✅ — LE CHIFFRE CLÉ : **3,8 GB**

1. **Purge N7 exécutée** (elle n'avait jamais été appliquée — dryrun montait à 18 GB) : run à blanc
   ROLLBACK conforme au script (56 661 904 + 1 726 652 lignes, runs conservés intacts à 431 663), puis
   COMMIT + `VACUUM (FULL, ANALYZE)` ×2. **`dryrun_cascade_results` 18 GB → 6 GB, base 34 GB → 21 GB**
   (~13 GB récupérés, mieux que les ~11,3 prévus). Fenêtre de maintenance annoncée : seul sur la machine ;
   verrou exclusif VACUUM ≈ minutes ; incident collatéral instructif : une instance API démarrée PENDANT
   le VACUUM bloque au boot (ALTER TABLE du startup en attente de verrou) — à savoir pour M7.
2. **pg_dump -Fc réel** (pg_dump 18.4 de l'env conda labusedb — le brew 16 refuse le serveur 18, noté
   pour le VPS) : **5 min 50**, écritures gelées (seul sur la machine, aucune écriture pendant le dump).
   **TAILLE COMPRESSÉE : 3,8 GB** → transfert Gravelines : ~7 min à 10 MB/s, ~80 s à 50 MB/s.
3. **Restore complet** dans `labuse_m7_rehearsal` (`pg_restore -j 4`) : **7 min 39**. **Comptages M7
   contre la base restaurée — TOUS EXACTS** :
   | | attendu | restauré |
   |---|---|---|
   | parcels | 431 663 | **431 663** ✓ |
   | q_v7_defisc (servi) / q_v6_m8 (hystérésis) | complets | **431 663 / 431 663** ✓ |
   | defisc_fenetres (dont actives) | 1 166 / 797 | **1 166 / 797** ✓ |
   | pc_caducs | 2 164 | **2 164** ✓ |
   | score_e (dont estimables) | 77 718 / 51 926 | **77 718 / 51 926** ✓ |
   | outils : prix neuf / surface_d / division_or | 62 / 11 784 / 123 | **62 / 11 784 / 123** ✓ |
   | dormantes spin-off : parcel_solar / parcel_vue_mer | 431 663 / 150 643 | **431 663 / 150 643** ✓ |
4. `DROP DATABASE labuse_m7_rehearsal` propre. **Dump conservé : `~/labuse-backups/labuse_m7_20260721.dump`
   (3,8 GB)** — si M7 part vite, il sert tel quel.
   Chronologie complète de la migration répétée : dump 5 min 50 + transfert (≈ 2-7 min) + restore 7 min 39
   ≈ **un créneau de ~20 minutes** pour la bascule données.

## P5 · Harnais Playwright v1 ✅ — 8/8 captures

`qa/captures.mjs` (additif pur, aucun code produit touché ; PNG horodatés dans `qa/captures/out/`,
gitignorés). **Run réel contre une instance de la branche (:8011) : 8/8 parcours photographiés** :
dashboard + recherche · fiche brûlante (nav **7 onglets sans Solaire, Faisabilité en place** — vérifié
par le harnais : `Synthèse·Règles·Risques·Marché·Proprio·Faisabilité·Bilan·Pourquoi pas ?`) · onglet
Faisabilité · boutons export (Banquier) · scoreur d'adresse (panneau O2) · fiche écartée onglet
« Pourquoi pas ? » (motifs hiérarchisés) · vue Projets (pas de parcours actif → capture honnête).
Leçons durcies dans le harnais : attendre `/communes` avant l'omnibox ; l'analyse est opt-in
(`data-verdict-on`) ; fiche ciblée par IDU d'un TIER précis via l'API (robuste en E2E froid).
**Finding** : la bascule commune par l'omnibox reste asynchrone-fragile à froid (toast « aucune
commune ») — un hook QA store (1 ligne code produit, post-M7) rendrait le parcours commune déterministe.

## P7 · Audit de convergence des deux couches IA ✅ (bonus, lecture seule)

`docs/audits/CONVERGENCE_IA.md` : cartographie complète — LEGACY (`ai/agent.py`, UNE chaîne :
narratif post-cascade du pipeline, ajustement neutralisé à 0, provider config stub/anthropic) vs
SOCLE (`ai/core.py`, 11 kinds catalogués, grounding Fact + validation + cache CONTEXT_VERSION=4 +
coûts). Partagé : `ia_log`, clé API. Plan de migration en 4 étapes C1→C4 (kind
« narratif-evaluation » → flag → bascule → retrait legacy + settings morts), 2-3 sessions, zéro
touche scoring (le narratif est le seul produit des deux couches). **RIEN n'est migré** (post-M7).
