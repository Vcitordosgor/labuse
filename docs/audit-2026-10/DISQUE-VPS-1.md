# DISQUE-VPS-1 — ne garder sur le VPS que ce qui sert

Branche `fix/disque-vps-1` · 1 session · **pas de merge**. Sur le VPS : **LECTURE SEULE**.
Toute suppression ci-dessous est une **commande écrite pour Vic**, jamais exécutée par l'audit.

- VPS : `vps-5563949c`, Ubuntu, `/dev/sda1` **96 G, 76 G utilisés, 21 G libres (79 %)**.
- PostgreSQL **18.4** ; `pg_repack` **ABSENT** (seul `pgstattuple` est disponible) → la reprise de
  place se fait par **TRUNCATE** (instant), **DROP** (instant), ou **VACUUM FULL** table par table
  en heure creuse (verrou ACCESS EXCLUSIVE le temps de la réécriture).
- Servi aujourd'hui (`/opt/labuse/app/config/served_manifest.json`) :
  `scoring=q_v16 · cascade=q_v13_sources1 · mvt=q_v16 · division=q_v16 · residuel_run_seq=13`.
  **Retour arrière (`precedent`) = `q_v11_m137`** (scoring + cascade + mvt + division),
  `residuel_run_seq=13`. → **q_v11_m137 doit être conservé PARTOUT comme run de secours.**

## Total récupérable : ≈ 30 G (76 G → ~46 G utilisés)

| Poste | Récupérable | Méthode |
|---|---:|---|
| `/opt/labuse/app` (sources brutes + docs + dev) | **≈ 9,7 G** | suppression VPS + arrêt d'envoi (deploy) |
| `/var/backups/labuse` (sauvegarde pré-MAJ 27/08) | **4,1 G** | suppression VPS |
| Base `labuse` (labels morts + datasets reconstructibles + orphelines) | **≈ 16,5 G** | DELETE/TRUNCATE/DROP + reprise d'espace |
| **Total** | **≈ 30,3 G** | |

Et surtout : la **rotation des sauvegardes est corrigée** (elle pouvait atteindre 7 × 4,37 G = 30 G
et saturer le disque — cf. §3).

---

## 1. `/opt/labuse/app` (11 G) — n'envoyer et ne garder que l'utile

**Preuve de ce que l'app lit au runtime** (grep des chemins, crons `/etc/cron.d/labuse-*`, CLI) :

- L'API ne lit de `data/` que des **petits fichiers** : `carte_loyers_reunion_2025.json`,
  `insee_occupation_reunion_2022.json`, `obsimmo_vente_reunion.json` (`src/labuse/loyers.py:22`,
  `occupation.py:19`, `obsimmo.py`), les graines `data/fiscal/ data/entites/ data/anc/` (CLI/copilote),
  `data/cerfa/` (pré-dossier CERFA), et **deux caches écrits SUR le VPS** : `data/plu_reglements/`
  (API `/rules/plu`, `plu/extraction.py:32`) et `data/ortho_tiles/` (`ingestion/ortho_tiles.py:12`).
- Les **gros dossiers de `data/` sont des SOURCES d'ingestion brutes**, consommées une fois par des
  commandes `ingest-*` **manuelles** (ex. `ingest-cosia --extract-dir data/cosia/extract`,
  `cli.py:267`) puis matérialisées en base (`parcel_cosia_couverture`, `rgealti_pente_5m`, …).
  **Aucun cron ni l'API ne les relit.** Les crons d'ingestion (`ban`, `dvf`, `dpe`, `sitadel`,
  `bodacc`) **téléchargent** (`--download` / réseau), ils ne lisent pas ces dossiers.
- `docs/` n'est lu que par `docs/TESTS-TOLERES.md` (`suite_verte.py:27`) via `labuse circuit suite`,
  qui est la **barrière de déploiement jouée côté Mac**, jamais sur le VPS. `docs/CIRCUIT/VERROUS.md`
  n'est **jamais lu au runtime** (seulement cité dans des messages d'erreur).
- `qa/ outputs/ captures/ audit_shots/ tests/ reports/` ne sont lus par aucun chemin de prod
  (`outputs/` est **écrit** au runtime — exports PDF, `.eml` — jamais relu).

> ⚠️ Les gros dossiers `data/*` sont **gitignorés** (`.gitignore:21 data/*`) et **absents du dépôt Mac** :
> ils ont été posés/ingérés directement sur le VPS. Donc (a) le `deploy_app.sh` **actuel**, avec son
> `--delete`, les **EFFACERAIT** au prochain déploiement (ils ne sont pas dans la source) — le nouveau
> script les protège par exclusion ancrée ; (b) si on les supprime pour la place, les **ré-ingérer**
> suppose un **re-téléchargement depuis la source open-data** (CoSIA/IGN, RGE ALTI, DVF, INSEE), pas un
> renvoi depuis le Mac.

| Quoi | Taille | Lu en prod ? | Preuve | Action | Gain |
|---|---:|---|---|---|---:|
| `data/cosia` | 3,4 G | **non** | `cli.py:267` ingest manuel, 0 lecteur runtime/cron | supprimer (VPS) + exclure (deploy) | 3,4 G |
| `data/ortho_irc` | 1,9 G | **non** | source ortho IRC, ingérée | supprimer + exclure | 1,9 G |
| `docs` | 1,7 G | non (gate Mac) | `suite_verte.py:27` joué côté Mac | supprimer + exclure | 1,7 G |
| `qa` | 803 M | non | dev/QA, 0 import prod | supprimer + exclure | 803 M |
| `data/ml` | 400 M | **non** | corpus entraînement ML | supprimer + exclure | 400 M |
| `data/insee_rp` | 400 M | **non** | source INSEE RP, ingérée | supprimer + exclure | 400 M |
| `data/rgealti` | 361 M | **non** | source RGE ALTI → `rgealti_pente_5m` | supprimer + exclure | 361 M |
| `data/dvf_histo` | 349 M | **non** | source DVF historique, ingérée | supprimer + exclure | 349 M |
| `captures` | 270 M | non | captures de dev | supprimer + exclure | 270 M |
| `audit_shots` | 59 M | non | captures d'audit | supprimer + exclure | 59 M |
| `data/edf_hta` `data/tcsp` `data/dvf` | 16 M | **non** | sources ingérées | supprimer + exclure | 16 M |
| `tests` | 4 M | non | non importé par l'app | supprimer + exclure | 4 M |
| `outputs` | 424 M | **écrit** seulement | sorties runtime | **exclure** (protéger du `--delete`), ne pas supprimer | — |
| `data/plu_reglements` | 197 M | **oui (cache)** | `plu/extraction.py:32` | **garder** + exclure (ne pas écraser) | — |
| `data/ortho_tiles` | 76 M | **oui (cache)** | `ingestion/ortho_tiles.py:12` | **garder** + exclure | — |
| `data/ban` | 74 M | cron (re-DL) | `cli.py:3572` ingest-ban `--download` | garder + exclure (cron le régénère) | — |
| `src config declarations frontend deploy` + petits `data/*` | ~0,5 G | **oui** | cœur API/CLI/front | **garder et envoyer** | — |

**Sous-total `/opt/labuse/app` : ≈ 9,7 G** (l'app passe de 11 G à ~1,3 G).

### Correctif `deploy_app.sh` (fait dans cette branche)

- **Plus de transit `/tmp/labuse-app-sync`** : `rsync` écrit **directement** dans `/opt/labuse/app`
  via `--rsync-path="sudo rsync"` (économise aussi ~11 G temporaires sous `/tmp` à chaque déploiement).
- **Exclusions ancrées** (`/data/cosia`, `/docs`, `/qa`, … préfixe `/` = ancré à la racine du transfert),
  **testées en `--dry-run`** (cf. §Vérification). Les exclusions **protègent aussi du `--delete`** les
  caches runtime (`plu_reglements`, `ortho_tiles`, `outputs`) et les sources brutes présentes sur le VPS.

---

## 2. Base `labuse` (43 G)

### Qui lit quoi (preuve)

| Table | Taille | Servie / lue en prod ? | Preuve |
|---|---:|---|---|
| `spatial_layers` (+`_sub`), `tuyau_subdivise`, `mvt_parcels`, `mvt_tile_cache` | 7,9 G | **oui — carte** | `api/tiles.py`, `api/couches_tuyau.py:193` |
| `parcel_p_score_v2` | 4,5 G | **oui — Signal** (run servi) | `api/…`, `golden_ops.py:37` — `run_id=q_v16` |
| `score_labuse` | 1,5 G | **oui — Score** (run servi) | `api/app.py:1304` — `run_label=q_v16` |
| `cascade_results` (sans label) | 1,4 G | **oui — fiche/Dossier** | `gabarit/builder.py:335`, `courrier_compose.py:112` |
| `dryrun_cascade_results` | 13 G | **partiel** — seuls `q_v13_sources1` (servi) + `q_v11_m137` (secours) | `renouvellement.py:137`, manifeste |
| `p_model_ext_dataset` | 1,56 G | **oui — fiche** (SDP résiduelle) | `api/moteurs.py:293`, `api/modules.py:1093`, `api/accueil.py:89` |
| `p_model_dataset(_v2/_v2bis)`, `p_model_candidates` | 5,08 G | **non** — build dataset/entraînement, **inertes sur le VPS** | listées `_BACKUP_RECONSTRUCTIBLES` `cli.py:2932` ; 0 lecteur api/cron ; `reports/` (joblib) **absent du VPS** → le modèle n'est **pas** entraîné ici |
| `parcel_residuel_runs` | 190 M | **oui** — run 13 (servi+secours) | manifeste `residuel_run_seq=13` |
| orphelines (`algo2_prop_features`, `m6_*`, backups, photos…) | ~1,24 G | **non** | registre `registre/tables.py:597 ACTIONS_PROPOSEES` = « purger/archiver » |

**Règle respectée** : `q_v13_sources1` (cascade), `q_v16` (scoring/mvt/division), résiduel run 13 et le
run de secours `q_v11_m137` sont **tous conservés**.

### Labels / runs morts (à retirer)

- `dryrun_cascade_results` (13 G, 4 labels ~3,3 G chacun) : **garder** `q_v13_sources1` (servi, 3,66 G)
  + `q_v11_m137` (secours, 3,31 G) ; **morts** `q_v10_m129` (3,31 G) + `q_v8_calibre` (3,05 G).
- `parcel_p_score_v2` (4,5 G, 9 runs ×565 M) : **garder** `q_v16` (servi) + `q_v11_m137` (secours) ;
  **morts** `q_v8_calibre`, `…_pre_regle`, `…_pre_m28`, `…_pre_m39`, `…_pre_pond`, `q_v10_m129`, `q_v2_demo`.
- `dryrun_parcel_evaluations` (287 M) : garder `q_v13_sources1` + `q_v11_m137` ; morts `q_v10_m129`, `q_v8_calibre`.
- `parcel_residuel_runs` (190 M, runs 1/2/13) : garder 13 (servi) ; run 1 et 2 anciens (run 2 est
  l'ancien servi — à garder au choix ; run 1 supprimable).

### Plan de purge **dans l'ordre**, avec gain et retour arrière

> **Avant tout** : une sauvegarde `pg_dump` fraîche existe chaque matin (09:30, `backup_postgres.sh`),
> le schéma `sauvegarde_20261006` et `app-avant-0610` restent (§4). Lancer une sauvegarde manuelle de
> contrôle avant l'étape 3 :
> `sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; /opt/labuse/app/deploy/scripts/backup_postgres.sh'`

**Étape 2a — TRUNCATE des datasets reconstructibles inertes (instantané, 0 verrou long) — gain ≈ 5,08 G**
```sql
-- reconstructibles (cli.py:_BACKUP_RECONSTRUCTIBLES), AUCUN lecteur prod sur le VPS.
-- p_model_ext_dataset est EXCLU de la liste : l'API le lit (fiche) → on n'y touche PAS.
TRUNCATE TABLE p_model_dataset_v2bis;   -- 1,85 G
TRUNCATE TABLE p_model_dataset_v2;      -- 1,60 G
TRUNCATE TABLE p_model_candidates;      -- 862 M
TRUNCATE TABLE p_model_dataset;         -- 769 M
```
Retour arrière : rebâties par le feature-store/scoring (jamais saisies par l'utilisateur).

**Étape 2b — DROP des orphelines (instantané) — gain ≈ 1,24 G**
Voie maison (sanctionnée) :
```bash
cd /opt/labuse/app && sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; \
  /opt/labuse/venv/bin/labuse tables purger --apply'   # déplace les orphelines vers le schéma `poubelle`
# … vérifier le site, puis libérer la place :
sudo -u postgres psql labuse -c 'DROP SCHEMA IF EXISTS poubelle CASCADE;'
```
Principales : `algo2_prop_features` 389 M, `m6_a02_backup_plu_dup` 252 M, `m6_snapshot_mvt_post2a/b`
221 M ×2, `p_model_static_pre_v8` 79 M, `parcel_adjacence` 71 M, `p_model_scores_2026` 52 M,
`p_model_bati_features` 37 M, `agent_run_parcels` 27 M, `parcel_zone_plu_prebascule` 21 M,
`parcel_residuel_rerun` 21 M, `parcel_residuel_pre_v8` 18 M, `backup_spaul_ppr_avant_littoral` 18 M, …
Retour arrière : la sauvegarde du matin contient leur définition + données.

**Étape 2c — DELETE des labels morts puis reprise d'espace (heure creuse) — gain ≈ 9,9 G**
```sql
DELETE FROM dryrun_cascade_results   WHERE run_label IN ('q_v10_m129','q_v8_calibre');       -- ~6,35 G logiques
DELETE FROM parcel_p_score_v2        WHERE run_id NOT IN ('q_v16','q_v11_m137');             -- ~3,4 G logiques
DELETE FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v10_m129','q_v8_calibre');      -- ~0,14 G
DELETE FROM parcel_residuel_runs     WHERE run_seq = 1;                                       -- ~0,06 G
```
Le DELETE **ne rend pas la place** : il faut réécrire la table. `pg_repack` étant absent, deux options :

- **Option A — `VACUUM FULL` (simple, mais verrou ACCESS EXCLUSIVE)** — en **heure creuse (~00:00–05:00
  heure Réunion**, hors crons 06:00–10:00 et backup 09:30) :
  ```sql
  VACUUM (FULL, ANALYZE) dryrun_cascade_results;    -- réécrit ~6,7 G restants  → ~10-20 min
  VACUUM (FULL, ANALYZE) parcel_p_score_v2;         -- réécrit ~1,1 G restants  → ~3-5 min
  VACUUM (FULL, ANALYZE) dryrun_parcel_evaluations; -- ~1 min
  VACUUM (FULL, ANALYZE) parcel_residuel_runs;      -- < 1 min
  ```
  Pendant le `VACUUM FULL` d'une table, les requêtes du site **sur cette table** attendent → d'où l'heure creuse.
- **Option B — recopie + bascule (quasi sans coupure)**, recommandée pour `dryrun_cascade_results` :
  ```sql
  CREATE TABLE dryrun_cascade_results_new (LIKE dryrun_cascade_results INCLUDING ALL);
  INSERT INTO dryrun_cascade_results_new
    SELECT * FROM dryrun_cascade_results WHERE run_label IN ('q_v13_sources1','q_v11_m137'); -- en ligne
  BEGIN;  -- verrou bref
    ALTER TABLE dryrun_cascade_results RENAME TO dryrun_cascade_results_old;
    ALTER TABLE dryrun_cascade_results_new RENAME TO dryrun_cascade_results;
  COMMIT;
  -- vérifier le site, puis : DROP TABLE dryrun_cascade_results_old;
  ```

**Sous-total base : ≈ 16,2 G** (5,08 + 1,24 + 9,9).

---

## 3. Sauvegardes `/var/backups/labuse` (13 G) — rotation corrigée

État : `labuse-labuse-20261005-093001.dump` 4,37 G + `20261006` 4,37 G + `pre-maj-20260827/` 4,1 G
(sauvegarde manuelle **pré-migration du 27/08**, hors rotation). `LABUSE_BACKUP_KEEP=7` dans
`/etc/labuse/labuse.env` → **7 × 4,37 G = 30,6 G** potentiels : **la rotation pouvait saturer le disque.**

**Correctifs `backup_postgres.sh` (faits dans cette branche)** :
- défaut `KEEP` **7 → 4** (`LABUSE_BACKUP_KEEP` l'emporte toujours s'il est posé) ;
- rétention hebdo **4 → 3** ;
- **garde-disque avant dump** : si l'espace libre < 1,3 × taille du dernier dump, suppression des
  **dumps quotidiens les plus anciens** (jamais le plus récent) jusqu'à avoir la place → « tient dans
  le disque, garde toujours au moins le plus récent » est désormais **structurel**.

**Commandes pour Vic** :
```bash
# (a) abaisser la rétention effective dans l'env du VPS (le défaut script est 4, mais l'env=7 prime) :
sudo sed -i 's/^LABUSE_BACKUP_KEEP=.*/LABUSE_BACKUP_KEEP=4/' /etc/labuse/labuse.env
# (b) supprimer la sauvegarde pré-migration du 27/08 (migration faite, prod stable sur q_v16) :
sudo rm -rf /var/backups/labuse/pre-maj-20260827        # gain 4,1 G
```
Les `.tar.gz` de captures Radar (116 o chacun) sont négligeables (`/srv/labuse/pige/captures` est vide).

**Sous-total sauvegardes : 4,1 G** (+ plafond de rotation ramené de ~30 G à ~4 × 4,37 G ≈ 17,5 G max).

---

## 4. À garder pour l'instant (retour arrière) — quand les supprimer

- **`/opt/labuse/app-avant-0610` (4,2 G)** — l'app servie **avant la bascule du 06/10** (son
  `config/served_run.txt` = `q_v11_m137`). **Garder** tant que `q_v16` n'est pas confirmé définitif.
  Supprimable quand Vic acte que **le retour arrière applicatif vers q_v11_m137 n'est plus envisagé**
  (p. ex. après ~2 semaines de prod stable sur q_v16, soit **vers le 20/10**) :
  `sudo rm -rf /opt/labuse/app-avant-0610` → **+4,2 G**.
- **Schéma `sauvegarde_20261006` (~18 M)** — retour arrière données de la bascule 06/10. **Poids
  négligeable**, aucune urgence ; supprimable en même temps que `app-avant-0610` :
  `DROP SCHEMA sauvegarde_20261006 CASCADE;`.

---

## Récapitulatif — commandes pour Vic, dans l'ordre

```bash
# ── FICHIERS (immédiat) ───────────────────────────────────────────────────────
# 1. sauvegarde pré-MAJ 27/08 (migration faite)                         +4,1 G
sudo rm -rf /var/backups/labuse/pre-maj-20260827
# 2. sources brutes d'ingestion + docs + dev (NON lues en prod)         +9,7 G
sudo rm -rf /opt/labuse/app/{docs,qa,captures,audit_shots,tests}
sudo rm -rf /opt/labuse/app/data/{cosia,ortho_irc,ml,insee_rp,rgealti,dvf_histo,edf_hta,tcsp,dvf}
#   (on NE touche PAS data/plu_reglements, data/ortho_tiles, data/ban, outputs : caches/sorties runtime)
# 3. rotation des sauvegardes                                           (évite +30 G futurs)
sudo sed -i 's/^LABUSE_BACKUP_KEEP=.*/LABUSE_BACKUP_KEEP=4/' /etc/labuse/labuse.env

# ── BASE (sauvegarde de contrôle d'abord) ─────────────────────────────────────
sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; /opt/labuse/app/deploy/scripts/backup_postgres.sh'
# 4. TRUNCATE datasets reconstructibles inertes                         +5,08 G
sudo -u postgres psql labuse -c "TRUNCATE p_model_dataset_v2bis, p_model_dataset_v2, p_model_candidates, p_model_dataset;"
# 5. orphelines → poubelle → DROP schéma                                +1,24 G
cd /opt/labuse/app && sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; /opt/labuse/venv/bin/labuse tables purger --apply'
sudo -u postgres psql labuse -c "DROP SCHEMA IF EXISTS poubelle CASCADE;"
# 6. labels morts + reprise d'espace (HEURE CREUSE ~00:00-05:00 Réunion) +9,9 G
sudo -u postgres psql labuse <<'SQL'
DELETE FROM dryrun_cascade_results    WHERE run_label IN ('q_v10_m129','q_v8_calibre');
DELETE FROM parcel_p_score_v2         WHERE run_id   NOT IN ('q_v16','q_v11_m137');
DELETE FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v10_m129','q_v8_calibre');
DELETE FROM parcel_residuel_runs      WHERE run_seq = 1;
VACUUM (FULL, ANALYZE) dryrun_cascade_results;
VACUUM (FULL, ANALYZE) parcel_p_score_v2;
VACUUM (FULL, ANALYZE) dryrun_parcel_evaluations;
VACUUM (FULL, ANALYZE) parcel_residuel_runs;
SQL

# ── PLUS TARD (vers le 20/10, q_v16 confirmé définitif) ───────────────────────
# sudo rm -rf /opt/labuse/app-avant-0610                                 +4,2 G
# sudo -u postgres psql labuse -c "DROP SCHEMA sauvegarde_20261006 CASCADE;"
```

**Total immédiat ≈ 30,3 G** (76 G → ~46 G utilisés) ; **+4,2 G** supplémentaires vers le 20/10.
