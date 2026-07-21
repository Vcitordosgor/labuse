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
