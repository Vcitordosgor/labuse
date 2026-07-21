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
