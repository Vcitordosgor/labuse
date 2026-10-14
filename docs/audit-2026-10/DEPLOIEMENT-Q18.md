# DÉPLOIEMENT PROD — q_v18 + sources-maj-1 (cadastre 2026-09, PPR partiel, ouverture, contenance)

> **Lecture seule / plan — RIEN n'est lancé par ce document.** Rédigé le 2026-10-11.
> Architecture : **le Mac CALCULE, le VPS SERT.** Le run q_v18 est déjà calculé et servi EN LOCAL
> (`config/served_manifest.json` : scoring `q_v18`, cascade `q_v18_sources`, résiduel `run_seq=15`).
> Ce plan **porte en prod** le code mergé dans `main` + les données (cadastre différentiel + sortie du run).
>
> **Màj 12/10** : ajout de la **Phase 9 — CHASSE-DONNEES-FIX-1** (gestes prod du fix données servies,
> SUIT q_v18) : build-mvt + purge cache tuiles, fiche-commune-cache, detect-events, refresh
> owner_enrichment, sync BAN/DPE, ré-ingestions CatNat/OCS GE, millésimes CatNat/AZI. **Le servi reste
> q_v18** ; le run `run_seq=16`/`q_v19` du fix n'est PAS déployé.

## Règles non négociables (rappel + où elles sont appliquées)

| Règle | Application dans ce plan |
|---|---|
| **`deploy/scripts/deploy_app.sh` JAMAIS `deploy.sh`** | Phase 1 et Phase 5.3 n'utilisent QUE `deploy_app.sh`. `deploy.sh` (racine) est **interdit ici** (il enchaîne des gestes data/bascule hors de notre maîtrise). |
| **Cron DVF commenté pendant le test de Stéphanie** | Phase 0.3 le commente (`/etc/cron.d/labuse-dvf`), Phase 8 le ré-active. Tant que le test tourne, `refresh-dvf` (mer. 09:00) ne doit PAS écrire. |
| **Tables clients jamais touchées** | Tous les dumps/restores sont `-t <table>` CIBLÉS (jamais `--clean` global). Liste des tables clients protégées en annexe A. Les disparues sont **marquées, pas supprimées** (sinon FK CASCADE → `pipeline_entries`/`projet_parcelles`/`alertes`/`module_division`). |
| **Sauvegarde de la prod avant** | Phase 0.2 (dump lean prod + vérif `pg_restore --list`). Rollback en annexe B. |
| **Tout CLI `labuse` sur le VPS : sourcer `labuse.env` + `cd /opt/labuse/app`** | Sinon `fe_sendauth: no password supplied` (creds DB dans `labuse.env`) et chemins `config/` cassés (relatifs au cwd). Pattern OBLIGATOIRE ci-dessous. Découvert 13/10 (Phases 5/6 et §8bis). |

> **Pattern CLI VPS (toute commande `labuse` manuelle)** — le raccourci `sudo -u labuse /opt/labuse/venv/bin/labuse <cmd>` **ne suffit PAS** :
> ```bash
> ssh labuse-vps "sudo -u labuse bash -c 'set -a; . /etc/labuse/labuse.env; set +a; cd /opt/labuse/app && /opt/labuse/venv/bin/labuse <cmd>'"
> ```
> Pour les CRONS (qui sourcent déjà `labuse.env`), le seul manque était le PATH : corrigé en **§8bis** (ligne `PATH=/opt/labuse/venv/bin:…` dans le registre + gabarit CRON-1 `cli.py`).

## Fenêtre de déploiement (⚠ créneaux à éviter — heure Réunion)

- **09:30 quotidien** : `labuse-backup` (dump prod) — `sync-run.sh` dit explicitement « ne JAMAIS lancer pendant le backup » (verrous croisés). 
- **08:00 dimanche** : `db_maintenance.sh` (VACUUM). 
- **09:00 mercredi** : `labuse-dvf` (neutralisé en Phase 0.3 de toute façon). 
→ **Choisir un créneau hors 09:00–10:00 et hors dimanche matin.**

---

## Delta depuis le dernier déploiement

**Dernier déploiement prod** = **07/10/2026, commit `143a5739`, servi `q_v16`** (confirmé). Le delta code ci-dessous = `143a5739..main` (`5021012a`).

### Code (via git — part avec `deploy_app.sh`, en clair par `main`)
| Bucket | Merge(s) `main` |
|---|---|
| Correctifs | `c4bffe5d` (fix/correctifs-1) · `a883cabc` (chargement-1) |
| Ouverture (zones AU) | `684db4e8` (feat/ouverture) |
| Contenance | `58167df5` (fix/contenance-1) · `88127ca8` (contenance×ppr-partiel) · `c978546e` (garde-fou symétrique) |
| PPR partiel | `a81817ce` (fix/ppr-partiel-a) |
| Sources / cadastre | `a7f91a04`+`9ecbd79f` (fix/sources-maj-1 : `ingestion/arcep_fibre.py` T2, `api/app.py` fiche disparue, `reevaluer-cascade`, exclusion des disparues, scripts q_v18) |
| Recette | `bffd1eab` · `912d1fad` (surface incertaine lisible, 11 retouches fiche/flash/dashboards/successions) |
| Signal / run | `5d4cb1e3` (univers Signal = parc vivant) · `5021012a` (bascule q_v18) |

### Données
1. **Base sources-maj-1** (Phase 3) : `parcels` (+2 919 nouvelles, 1 501 géométries, **1 353 marquées `cadastre_disparue_le`**, contenance) en **delta data-only** (3a, jamais de DROP — FK client) ; `parcel_cadastre_remplacement`, `adresse_parcelles`, `sitadel_permits` (→ 08-2026), `spatial_layers` (transport), `arcep_immeubles` (T2), `rnic_coproprietes`, `data_sources` en restore ciblé (3b).
2. **Sortie du run q_v18** (via `sync-run.sh` — Phase 4) : résiduel `run_seq=15`, étage 0 `q_v18_sources` (`dryrun_cascade_results`/`dryrun_parcel_evaluations`), Signal `parcel_p_score_v2`/`p_score_v2_runs` q_v18, score `score_labuse`/`score_labuse_runs` q_v18, dérivés (`score_e`, `dvf_prix_sortie_neuf`, `pc_caducs`, `defisc_fenetres`, `parcel_evaluations`, `surface_d_events`).
3. **`parcel_couche_intersection` : COPIÉE depuis le Mac** (Phase 4bis — jamais `build-intersections` en prod).
4. **Reconstruit SUR le VPS après bascule** (Phase 6) : `parcel_flags`, `parcel_renouvellement`, `score_e` (re-stampé), `mvt_parcels`+tuiles, `commune_contexte_cache` via `jobs exec fiche-commune-cache`, couche VEFA.

---

## Phase 0 — Pré-vol (sauvegarde + gel du cron DVF)

### 0.1 — Vérifier l'état local (référence du déploiement)
```bash
cat config/served_manifest.json    # doit montrer scoring_run=q_v18, cascade_run=q_v18_sources, residuel_run_seq=15
git -C ~/Desktop/labuse log --oneline --first-parent -5   # HEAD main = 5021012a (bascule q_v18)
```
**Durée** : < 1 min. **Vérif** : manifeste = q_v18/q_v18_sources/15.

### 0.2 — Sauvegarde de la prod (OBLIGATOIRE avant toute écriture)
```bash
ssh labuse-vps 'sudo -u labuse /opt/labuse/app/deploy/scripts/backup_postgres.sh'
ssh labuse-vps 'ls -lt /var/log/labuse/ ; sudo -u postgres ls -lh ~/backups | head'
```
**Durée** : ~3–8 min (dump lean + `pg_restore --list` + rotation). **Vérif** : le script vérifie lui-même `pg_restore --list` ; un dump daté du jour apparaît. Conserver aussi les dumps locaux pré-cadastre `~/labuse-backups/sources-maj-1/parcels-AVANT-CADASTRE-*.dump` (rollback parcels).

### 0.3 — Geler le cron DVF (durée du test de Stéphanie)
```bash
ssh labuse-vps 'sudo sed -i "s/^\([^#].*refresh-dvf\)/# GELÉ test Stéphanie \1/" /etc/cron.d/labuse-dvf \
  && sudo systemctl reload cron'
ssh labuse-vps 'cat /etc/cron.d/labuse-dvf'          # la ligne refresh-dvf est commentée
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool   # labuse-dvf ne doit plus être « dû »
```
**Durée** : < 1 min. **Vérif** : la ligne `0 9 * * 3 … refresh-dvf` est préfixée `#`. **Phase 8 la ré-active.**

---

## Phase 1 — Code applicatif (`deploy_app.sh` — JAMAIS `deploy.sh`)

```bash
cd ~/Desktop/labuse
VITE_RUN_LABEL=q_v18 deploy/scripts/deploy_app.sh labuse-vps
```
**Ce que ça fait** : rsync du code (sans data/docs/tests), `pip install -r requirements.lock` + `-e . --no-deps`, **import-smoke de la chaîne de démarrage** (échoue le déploiement si une dépendance cœur manque), `npm ci` + `vite build --base=/` (front au label q_v18), install de l'unit systemd + `daemon-reload`.
**Durée** : ~4–8 min. **Vérif** : la ligne `chaîne de démarrage importable ✓` s'affiche ; `set -e` fait échouer sinon. (⚠ le restart effectif est Phase 5 / 6.)

> `deploy_app.sh` **ne touche aucune donnée** (DB intacte). C'est voulu : les données passent par les phases 3–4.

> 🔴 **INCIDENT 13/10 (corrigé)** : `deploy_app.sh` rsync'd `config/served_manifest.json` local (q_v18) par-dessus
> celui de prod → la prod a basculé sur q_v18 **sans données** (`/readyz=false`, site exposé en test). Rollback
> manuel du manifeste sur `precedent` (q_v16 / q_v13_sources1 / seq 13) → `/readyz=true`. **Correctif** :
> `deploy_app.sh` **exclut désormais `config/served_manifest.json` et `config/served_run.txt`** (fichiers d'état
> servi, écrits par la bascule SEULE, propres à la prod). **La bascule vers q_v18 se fait en Phase 5, pas par le
> déploiement du code.** ⚠ La Phase 5.3 re-lance `deploy_app.sh` : vérifier que le manifeste prod reste intact après.

---

## Phase 2 — Schéma DDL sur prod (AVANT les données — colonnes nouvelles de `parcels` d'abord)

> Le chargement de `parcels` en Phase 3 est **data-only / delta** (jamais un DROP : `parcels` est
> référencée par des FK client — cf. Phase 3). Les colonnes ajoutées hors ORM doivent donc EXISTER
> sur prod **avant** le delta, sinon le COPY/UPDATE échoue. On les pose toutes ici (idempotent).

```bash
ssh labuse-vps "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse \
  -c 'ALTER TABLE parcels ADD COLUMN IF NOT EXISTS cadastre_disparue_le date;' \
  -c 'ALTER TABLE parcels ADD COLUMN IF NOT EXISTS contenance_m2 integer;'"
# Garde-fou « toute colonne nouvelle de parcels » : comparer le schéma Mac vs prod et poser ce qui manque.
diff <(~/miniforge3/envs/labusedb/bin/psql "postgresql://openclaw@localhost:5432/labuse" -tAc \
        "SELECT column_name||' '||data_type FROM information_schema.columns WHERE table_name='parcels' ORDER BY 1") \
     <(ssh labuse-vps "sudo -u postgres psql -d labuse -tAc \
        \"SELECT column_name||' '||data_type FROM information_schema.columns WHERE table_name='parcels' ORDER BY 1\"") \
  && echo "✓ schéma parcels identique Mac↔prod" || echo "⚠ colonnes à poser (lignes « < » = présentes Mac, absentes prod)"
# parcel_cadastre_remplacement : copier la structure EXACTE créée en local
~/miniforge3/envs/labusedb/bin/pg_dump -s -t parcel_cadastre_remplacement \
  "postgresql://openclaw@localhost:5432/labuse" | ssh labuse-vps 'sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse'
```
**Durée** : < 1 min. **Vérif** :
```bash
ssh labuse-vps "sudo -u postgres psql -d labuse -c \
  \"SELECT column_name FROM information_schema.columns WHERE table_name='parcels' AND column_name IN ('cadastre_disparue_le','contenance_m2')\" -c \"\\d parcel_cadastre_remplacement\""
```
`cadastre_disparue_le` **et** `contenance_m2` présentes + table `parcel_cadastre_remplacement` créée (vide) + diff de schéma vide.

---

## Phase 3 — Données sources-maj-1 (dump/restore CIBLÉ — ⛔ JAMAIS `ingest-island`)

> **Landmine (RAPPORT §5.2)** : `ingest-island` fait `DELETE FROM parcels WHERE commune` par commune → détruirait les 1 353 marques + les liens de remplacement. **On transfère les tables, on ne ré-ingère pas.**
> **⚠ `parcels` NE se charge PAS en `--clean`** : elle est référencée par des FK client (`pipeline_entries`, `projet_parcelles`, `module_division`, `alertes`, `parcel_residuel_runs`…). Un `DROP TABLE parcels` échouerait (dépendances) ou, en CASCADE, détruirait des contraintes/lignes CLIENT. → `parcels` = **delta data-only** (INSERT/UPDATE), les colonnes de Phase 2 doivent préexister.

### 3a — `parcels` : delta NON destructif (depuis les tables de staging `_cad_sm1_*`)
```bash
PG=~/miniforge3/envs/labusedb/bin ; L=postgresql://openclaw@localhost:5432/labuse ; S=/tmp/sm1 ; mkdir -p $S
# On expédie les 3 jeux de staging + le cadastre complet staging, PAS la table parcels elle-même.
# ⚠ `adresses` AVANT `adresse_parcelles` : le BAN (`adresses`) est MIRROIR Mac→prod (Mac = source de vérité ;
#   prod ne ré-ingère JAMAIS le BAN seul — cf. 9.3 supprimée). Mis à jour sur le Mac PUIS copié ici, sinon la
#   FK `adresse_parcelles_id_ban_fkey` → adresses(id_ban) ne valide pas (divergence constatée au déploiement :
#   1202 id_ban orphelins). `adresses` : 0 FK/vue dépendante sur prod (vérifié) → `--clean` sûr.
for T in _cad_sm1_nouvelles _cad_sm1_geommodif _cad_sm1_disparues _cad_sm1_staging parcel_cadastre_remplacement adresses adresse_parcelles ; do
  $PG/pg_dump -Fc -t "$T" -d "$L" -f "$S/$T.dump"
  rsync -a --partial "$S/$T.dump" labuse-vps:/tmp/$T.dump
  ssh labuse-vps "sudo -u postgres pg_restore --clean --if-exists --no-owner --no-acl --role=labuse -d labuse /tmp/$T.dump 2>&1 | tail -1"
done
# Contrôle propriété (toute table copiée doit appartenir à labuse) :
ssh labuse-vps "sudo -u postgres psql labuse -c \"SELECT tablename,tableowner FROM pg_tables WHERE tablename IN ('_cad_sm1_nouvelles','_cad_sm1_geommodif','_cad_sm1_disparues','_cad_sm1_staging','parcel_cadastre_remplacement','adresses','adresse_parcelles') AND tableowner<>'labuse';\""
# Application du delta EN UNE TRANSACTION (INSERT nouvelles · UPDATE géom+contenance · MARQUE disparues).
# `_cad_sm1_staging` porte le cadastre 2026-09 complet (idu, geom, contenance) ; on n'agit QUE sur les idu listés.
ssh labuse-vps "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse" <<'SQL'
BEGIN;
-- nouvelles (2 919) : INSERT avec id du Mac (préserve les ids → les intersections copiées en 4bis matchent)
INSERT INTO parcels (id, idu, commune, geom, surface_m2, contenance_m2, centroid)
  SELECT st.id, st.idu, left(st.idu,5), st.geom, ST_Area(st.geom), st.contenance_m2, ST_Centroid(st.geom)
  FROM _cad_sm1_staging st JOIN _cad_sm1_nouvelles n USING (idu)
  ON CONFLICT (id) DO NOTHING;
-- géométries modifiées (1 501) : UPDATE geom + contenance (trigger geom_2975 recalcule)
UPDATE parcels p SET geom = st.geom, surface_m2 = ST_Area(st.geom), contenance_m2 = st.contenance_m2
  FROM _cad_sm1_staging st JOIN _cad_sm1_geommodif g USING (idu) WHERE p.idu = st.idu;
-- disparues (1 353) : MARQUE seulement (jamais DELETE → FK client protégées)
UPDATE parcels p SET cadastre_disparue_le = DATE '2026-09-01'
  FROM _cad_sm1_disparues d WHERE p.idu = d.idu AND p.cadastre_disparue_le IS NULL;
COMMIT;
SQL
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "ANALYZE parcels;"'
```

### 3b — tables de référence (NON FK-client) : `pg_restore --clean` ciblé
```bash
for T in sitadel_permits spatial_layers arcep_immeubles rnic_coproprietes data_sources ; do
  $PG/pg_dump -Fc -t "$T" -d "$L" -f "$S/$T.dump"
  rsync -a --partial "$S/$T.dump" labuse-vps:/tmp/$T.dump
  ssh labuse-vps "sudo -u postgres pg_restore --clean --if-exists --no-owner --no-acl --role=labuse -d labuse /tmp/$T.dump 2>&1 | tail -1"
done
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "ANALYZE spatial_layers;"'
# Contrôle propriété (= labuse) pour toutes les tables 3b :
ssh labuse-vps "sudo -u postgres psql labuse -c \"SELECT tablename,tableowner FROM pg_tables WHERE tablename IN ('sitadel_permits','spatial_layers','arcep_immeubles','rnic_coproprietes','data_sources') AND tableowner<>'labuse';\""
```
**Durée** : ~15–30 min (delta parcels ~2–5 min ; spatial_layers ~51 Mo ~3–6 min ; staging `_cad_sm1_staging` ~181 Mo dump/transfert ~3–5 min ; autres petits). Le trigger `geom_2975` recalcule à l'INSERT/UPDATE. **`parcels.id` préservés** (nécessaire pour la copie des intersections en Phase 4bis).
**Vérif** (prod, requêtes ciblées) :
```bash
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "
  SELECT count(*) total, count(*) FILTER (WHERE cadastre_disparue_le IS NULL) vivantes,
         count(*) FILTER (WHERE cadastre_disparue_le IS NOT NULL) marquees FROM parcels;"'
# attendu : total 434582 · vivantes 433229 · marquees 1353
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "SELECT count(*) FROM parcel_cadastre_remplacement;"'  # 3007 lignes (mapping N:N ; 1292 anciennes distinctes / 1353 disparues ; 61 sans remplacement)
# adresses mirror + FK validée (0 orphelin) :
ssh labuse-vps "sudo -u postgres psql -d labuse -c \"SELECT count(*) AS adresses FROM adresses\" -c \"SELECT convalidated FROM pg_constraint WHERE conname='adresse_parcelles_id_ban_fkey'\""  # 339915 (= Mac) · t
```

---

## Phase 4 — Sortie du run q_v18 (`sync-run.sh`, filtré)

```bash
cd ~/Desktop/labuse
# répétition sans écrire (dump + transfert + comptages, PAS de restore) :
deploy/scripts/sync-run.sh --dry-run --run-label q_v18 --residuel-seq 15 --cascade-label q_v18_sources
# bascule réelle des données (après dry-run vert) :
deploy/scripts/sync-run.sh --run-label q_v18 --residuel-seq 15 --cascade-label q_v18_sources
```
**Ce que ça transfère** : scoring versionné (`parcel_p_score_v2`, `p_score_v2_runs`, `score_labuse`, `score_labuse_runs` filtrés `run_id/label=q_v18`), cascade (`dryrun_cascade_results`, `dryrun_parcel_evaluations` filtrés `run_label=q_v18_sources`), résiduel (`parcel_residuel_runs`+`residuel_runs` filtrés `run_seq=15`, **sans toucher `is_served`**), dérivés entiers (`score_e`, `dvf_prix_sortie_neuf`, `pc_caducs`, `defisc_fenetres`, `parcel_evaluations`, `surface_d_events`).
**Durée** : ~30–50 min (la cascade `q_v18_sources` ≈ 2,6 Go en clair, gzip -1 en flux ; transfert + `DELETE+COPY` par table + `ANALYZE`).
**Vérif** : le script fait **comptages local vs VPS, le moindre écart = arrêt (exit 1)** — il imprime `✓ <table> <n>` ou `✗ local=… vps=…`. Il **ne bascule aucun pointeur** (c'est la Phase 5).

> ⚠ `sync-run.sh` interdit la fenêtre de backup 3 h et ne lance plus build-mvt/golden lui-même (séparation données/bascule). Les pointeurs restent inchangés jusqu'à la Phase 5.

---

## Phase 4bis — Intersections : COPIE Mac → prod (⛔ AUCUN `build-intersections` en prod)

> **Leçon 06/10** : `build-intersections` sur l'île = rebuild complet (staging + RENAME), **>1 h / 4 000
> parcelles → plusieurs jours**, et il a **saturé la prod**. On ne le relance JAMAIS en prod. On COPIE
> la table `parcel_couche_intersection` (déjà calculée sur le Mac, **mêmes `parcels.id`** grâce à la
> Phase 3a) + sa table de version `_meta`.
>
> **Fait établi (lecture seule 12/10)** : AUCUNE couche de servitude de la fiche (`dpu`/`peb`/`sup`/
> `plu_gpu_prescription`) n'a changé depuis le 03/10 ; la table n'est périmée QUE par le différentiel
> cadastre. Côté Mac, on la met à jour de façon CIBLÉE (4 420 parcelles cadastralement modifiées, pas
> l'île) avec le script livré — voir Phase 4bis-0.

### 4bis-0 — (sur le MAC) rendre la table d'intersections fraîche, en ciblé
```bash
cd ~/Desktop/labuse
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src .venv/bin/python \
  scripts/audit/intersections/build_intersections_cible.py --apply --update-meta
```
Recalcule UNIQUEMENT les 4 420 parcelles `_cad_sm1_nouvelles` ∪ `_cad_sm1_geommodif` contre les
servitudes (DELETE+INSERT par lots, aucune autre ligne touchée), puis repose `serv_version`.
**Durée** : **~5–15 min** (mesuré : 25 parcelles/14 s à froid, 74 parcelles/2 s à chaud → ~0,03 s/parcelle en régime). **Vérif** : `serv_version` du `_meta` = empreinte courante (le script l'affiche).

### 4bis-1 — (Mac → prod) copier la table + sa version (AVANT la bascule)
```bash
PG=~/miniforge3/envs/labusedb/bin ; L=postgresql://openclaw@localhost:5432/labuse ; S=/tmp/sm1
$PG/pg_dump -Fc -t parcel_couche_intersection -t parcel_couche_intersection_meta -d "$L" -f "$S/inter.dump"
rsync -a --partial "$S/inter.dump" labuse-vps:/tmp/inter.dump
ssh labuse-vps 'sudo -u postgres pg_restore --clean --if-exists --no-owner --role=labuse -d labuse /tmp/inter.dump 2>&1 | tail -2'
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "ANALYZE parcel_couche_intersection;"'
```
`parcel_couche_intersection` n'est référencée par AUCUNE table client → `--clean` sans risque.
**Durée** : ~5–10 min (transfert + restore). **Vérif — fraîcheur = le verrou anti-rebuild** :
```bash
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/python -c "
from labuse.db import session_scope; from labuse import couche_intersection as ci
with session_scope() as s: print(\"fraiche =\", ci.fraiche(s))"'   # DOIT afficher : fraiche = True
```
> **C'est le verrou qui empêche la saturation** : `residuel-serve` (5.2) et `build-mvt` (6) appellent
> tous deux `couche_intersection.build` **seulement si `fraiche()` est faux**. Tant que la copie ci-dessus
> donne `fraiche = True` (prod `parcels`+servitudes == Mac, `_meta` copié), ils **sautent** la
> reconstruction des intersections. → **l'ordre des étapes est le garde-fou : copier AVANT de basculer.**

---

## Phase 5 — Bascule (pointeurs → q_v18)

### 5.1 — Scoring
```bash
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse golden promote q_v18'
```
Écrit `config/served_run.txt` (vue dérivée) ; le manifeste fait foi. **Durée** : < 1 min.

### 5.2 — Résiduel (déclenche la reconstruction des caches, Phase 6)
```bash
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse residuel-serve 15'
```
Passe `is_served` → `run_seq=15` **et lance `labuse rebuild` DÉTACHÉ** (tuiles + flags + renouvellement + score_e + fiches communes). **Les intersections sont SAUTÉES** car `fraiche()=True` depuis la Phase 4bis (c'est voulu — surtout pas de rebuild île). **Durée** : rebuild détaché quelques min (hors intersections) ; suivi `/tmp/labuse-rebuild-residuel-seq15.log`.

### 5.3 — Front au bon label (si pas déjà fait en Phase 1)
```bash
cd ~/Desktop/labuse && VITE_RUN_LABEL=q_v18 deploy/scripts/deploy_app.sh labuse-vps
```
**Durée** : ~4–8 min. **Vérif** : la page sert les données q_v18 (voir Phase 7).

---

## Phase 6 — Reconstruction des caches SUR le VPS

> **⛔ AUCUN `build-intersections` et AUCUN `labuse rebuild` global en prod.** Les intersections sont
> COPIÉES (Phase 4bis) ; la fiche commune se refait par son JOB dédié. `residuel-serve` (5.2) a déjà
> lancé un `rebuild` détaché qui a refait tuiles/flags/renouv/score_e/fiches **en sautant les
> intersections** (`fraiche()=True`). Les gestes ci-dessous sont des confirmations idempotentes.

| Geste | Commande (sur VPS, user labuse) | Reconstruit | Durée est. | Vérif |
|---|---|---|---|---|
| Tuiles + tables run-scopées | `labuse build-mvt` | `mvt_parcels`, `parcel_flags`, `parcel_renouvellement`, `score_e` (re-stampé q_v18), tiles-warm | ~5–10 min | `mvt_meta.run_label=q_v18`. **N.B.** son épilogue intersections affiche « déjà à jour (sources inchangées) » → **ne reconstruit RIEN** (grâce à 4bis). |
| Fiches communes | `labuse jobs exec fiche-commune-cache` | `commune_contexte_cache` (24 communes, précalcul du contexte) | ~2–5 min | `labuse jobs status` → job vert + vraie date de calcul |
| VEFA / prix neuf | `labuse vefa-neuf-build` | couche VEFA `neuf_vefa_commune`→`spatial_layers` | ~1–3 min | couche présente |

Préfixe VPS : `ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse <cmd>'`.
**Ordre** : build-mvt → `jobs exec fiche-commune-cache` → vefa. Chaque commande imprime sa durée (`· X s`).

> `parcel_couche_intersection` n'apparaît PLUS ici : elle vient de la Phase 4bis (copie). Si par malheur
> un `build-mvt`/`rebuild` affichait « sources servitudes changées → reconstruction » (donc `fraiche()`
> serait faux), **STOP** : re-vérifier la Phase 4bis-1 (table + `_meta` copiés, `parcels.id` alignés)
> AVANT de laisser un rebuild île repartir — c'est exactement ce qui a saturé la prod le 06/10.
>
> Note : `parcel_flags` était déjà q_v18 en local ; `parcel_renouvellement`/`score_e` étaient encore q_v16 — **le `build-mvt` sur le VPS les reconstruit frais** depuis la cascade/score/résiduel q_v18 synchronisés.

---

## Phase 7 — Vérification de bout en bout

```bash
# 1) Santé générale + crons (dvf toujours gelé)
curl -sS https://app.labuse.immo/healthz | python3 -m json.tool
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool      # "ok": true, retards: []
# 2) Golden distant (le run n'est « bon » qu'ici vert)
python3 qa/golden_check.py --base-url "$LABUSE_QA_TARGET"                   # env QA requis
# 3) Comptages run servi (prod)
ssh labuse-vps 'sudo -u postgres psql -d labuse -c "
  SELECT n_parcelles FROM p_score_v2_runs WHERE run_id=''q_v18'';         -- 433229
  SELECT run_seq,is_served FROM residuel_runs WHERE is_served;            -- 15, t
  SELECT value FROM mvt_meta WHERE key=''run_label'';"'                   -- q_v18
# 3bis) intersections : fraîches ET aux dimensions attendues (copiées, pas rebuildées)
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/python -c "
from labuse.db import session_scope; from labuse import couche_intersection as ci
with session_scope() as s: print(\"fraiche =\", ci.fraiche(s))"'            # fraiche = True
# 4) Témoins fonctionnels (fiche prod)
#    - une NOUVELLE parcelle (cadastre 2026-09) a un score q_v18 et s'affiche ;
#    - une DISPARUE affiche le bandeau « parcelle disparue — remplacée par … » et est absente de la recherche/carte ;
#    - une parcelle à contenance ≫ dessin affiche « surface incertaine / Analyse incomplète ».
```
**Durée** : ~5–10 min. **Critère de succès** : healthz ok, golden distant vert, 433229/15/q_v18, 3 témoins conformes.

---

## Phase 8 — Ré-activer le cron DVF (APRÈS le test de Stéphanie)

```bash
# ⚠ Le gel 0.3 a été posé avec le préfixe « # GELÉ deploiement-q18 » (pas « test Stéphanie »).
ssh labuse-vps 'sudo sed -i "s/^# GELÉ deploiement-q18 //" /etc/cron.d/labuse-dvf'
ssh labuse-vps 'cat /etc/cron.d/labuse-dvf'      # la ligne refresh-dvf est redevenue active
# NB : `systemctl reload cron` N'EXISTE PAS sur ce VPS (« reload non applicable à cron.service »).
# Inutile : cron relit /etc/cron.d/* automatiquement (mtime). Ne PAS tenter de reload.
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool
```
**Durée** : < 1 min. **À ne faire qu'une fois le test de Stéphanie terminé.**

### 8bis — Réparer les crons du registre (PATH) pour atteindre `healthz/crons: ok:true`
> **Diagnostic 13/10 (lecture seule)** : `sonde-sources`/`coherence-robinets` (dernier OK 22/09) et
> `ingest-bodacc` (dernier OK 06/10) sont en retard. **Cause** : le registre `/etc/cron.d/labuse`
> (généré par `deploy.sh`) lance `sh -c '. /etc/labuse/labuse.env; exec labuse jobs run <nom>'`, mais
> `labuse` NU n'est pas sur le `PATH` (ni cron, ni `labuse.env` n'ajoute `/opt/labuse/venv/bin`) →
> `labuse: not found`, **silencieux** (MAILTO=root sans MTA, aucune redirection). 25 jobs exposés ;
> seuls ceux SANS cron legacy de secours tombent (backup/sitadel/dpe ont un legacy à chemin complet).
> **Rien à voir avec le disque/la sauvegarde** (backup-postgres OK).
>
> **Correctif pérenne (dans le gabarit CRON-1, pas le fichier généré — `deploy.sh` régénère)** : soit
> appeler `/opt/labuse/venv/bin/labuse`, soit préfixer le venv au `PATH` dans `/etc/labuse/labuse.env`.
> Puis relancer les 3 jobs à la main une fois pour rattraper :
```bash
for J in sonde-sources coherence-robinets ingest-bodacc ; do
  ssh labuse-vps "sudo -u labuse sh -c '. /etc/labuse/labuse.env; /opt/labuse/venv/bin/labuse jobs run $J'"
done
curl -sS https://app.labuse.immo/healthz/crons | python3 -m json.tool   # attendu : ok:true
```

---

## Phase 9 — CHASSE-DONNEES-FIX-1 (SUIT q_v18 — gestes prod après le déploiement du code fix)

> Déploiement SÉPARÉ, APRÈS que q_v18 est servi en prod (Phases 1-8). CHASSE-DONNEES-FIX-1 (branche
> `fix/chasse-donnees-1`, 15 commits, cf. `docs/audit-2026-10/chasse-donnees-1/RAPPORT-FIX.md §SUITES`)
> corrige 74/83 écarts de données SERVIES **sans toucher le résiduel ni le score**.
>
> **Le run servi RESTE q_v18.** Le run `run_seq=16` / `q_v19` de la suite 1 (règles PLU au moteur) est
> un CANDIDAT local, `is_served=false` : **il n'est PAS déployé** (il a prouvé que les règles PLU
> appliquées fidèlement ne changent AUCUNE valeur servie → q_v19 ≡ q_v18). Ne rien synchroniser de
> `run_seq=16`, ne pas basculer le résiduel, ne pas le `sync-run`.

### 9.0 — Code du fix (`deploy_app.sh` — JAMAIS `deploy.sh`)
```bash
cd ~/Desktop/labuse   # après merge de fix/chasse-donnees-1 dans main
VITE_RUN_LABEL=q_v18 deploy/scripts/deploy_app.sh labuse-vps
```
**Vérif** : `chaîne de démarrage importable ✓`. Le fix ne touche aucune donnée ; les gestes 9.1-9.4
reconstruisent des caches, 9.5-9.7 rafraîchissent des sources tierces.

### 9.1 — Caches dérivés RECONSTRUCTIBLES (joués en local, à refaire en prod — PAS des runs)
Préfixe VPS : `ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse <cmd>'`.

| Geste | Commande (VPS, user labuse) | Pourquoi (écart) | Vérif |
|---|---|---|---|
| **Tuiles** (surface terrain bakée + drapeau incertaine) | `labuse build-mvt` | L1 C-09/C-10 : `mvt_parcels.surface_m2` = `COALESCE(contenance, dessin)` + `surface_incertaine`. `build-mvt` bumpe `mvt_meta.updated_at` → **invalide la version du cache tuiles** (les octets périmés ne sont plus retrouvés). | `mvt_meta.run_label=q_v18` ; survol carte CW0658 = 25 633 (plus 27 156). |
| **Purge cache tuiles parcels** (libère le disque périmé) | `sudo -u postgres psql -d labuse -c "DELETE FROM mvt_tile_cache WHERE layer='parcels';"` | idem — le bump de version suffit à l'invalidation, la purge récupère l'espace. | `SELECT count(*) FROM mvt_tile_cache WHERE layer='parcels';` → 0 (se re-remplit à la demande). |
| **Fiches communes** (fenêtre permis ancrée + socle) | `labuse jobs exec fiche-commune-cache` | L7 C-21 (ventilation permis sur la fenêtre ancrée du total) + clôt C-44 (dérive cache nocturne). Reconstruit `commune_contexte_cache` (24 communes). | `labuse jobs status` → vert + date du jour ; Le Tampon permis total = ventilation + annulés. |
| **Cloche sur le run servi** | `labuse detect-events --rattrapage` | L5 C-45 : `detect_events` jamais rejoué depuis q_v10 → cloche dans un autre monde que le digest. `--rattrapage` lit `run_from` = run PRÉCÉDENT de la table des runs (q_v16), `run_to` = servi (q_v18). Idempotent (clé `kind,idu,run_from,run_to`), écrit `event_log` (notifications), jamais le score. | `SELECT max(ts) FROM event_log WHERE kind='bascule' AND run_to='q_v18';` non nul. |

### 9.2 — Cache SIRENE/état des sociétés (recherche-entreprises)
```bash
# L5 D-46 : le cache owner_enrichment date de juillet → des SCI CESSÉES sont servies « actives ».
# score-v-fetch --passe owners ne REMPLIT que les SIREN ABSENTS du cache ; pour RAFRAÎCHIR l'existant
# (états cessée/radiée), purger d'abord le cache (reconstructible) PUIS re-moissonner.
ssh labuse-vps "sudo -u postgres psql -d labuse -c \"DELETE FROM owner_enrichment WHERE source='recherche_entreprises';\""
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse score-v-fetch --passe owners'
```
**Durée** : réseau (recherche-entreprises, throttle 0,2 s/SIREN ; quelques centaines de PM servies →
~qq min). **Vérif** : fiche prod d'une PM cessée → `proprietaire_moral.identite.actif=false` +
`etat_societe` « société cessée ». ⚠ geste RÉSEAU (API gouv) : hors heures creuses si possible.

### 9.3 — Sources tierces à re-synchroniser (fraîcheur — aucune divergence de VALEUR côté témoins)
> **⛔ BAN SUPPRIMÉ de la prod (décision 13/10).** On ne lance **jamais** `ingest-ban-plus` sur le VPS :
> le BAN (`adresses` + `adresse_parcelles`) se met à jour **sur le Mac** puis se **copie** Mac→prod en
> **Phase 3a** (mirror `adresses`, FK `adresse_parcelles_id_ban_fkey` validée). Raison : une ré-ingestion BAN
> en prod seule fait diverger `adresses` du Mac (constaté : 1202 id_ban orphelins → FK impossible). Mac = source
> de vérité unique du BAN. *(D-60 traité par la copie de Phase 3, pas par une ingestion prod.)*
```bash
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse ingest-dpe'        # D-61 : DPE ADEME (dernier sync 19/09)
```
**Vérif** : `data_sources` DPE `last_sync_at` du jour ; `max(dpe_records.date_etablissement)` avancé.
(BAN : vérifié en Phase 3a — `adresses` = Mac, FK validée, 0 orphelin.)

### 9.4 — Ré-ingestions CatNat / OCS GE (⚠ nécessitent le correctif de code AVANT, cf. RAPPORT-FIX §B)
> Ces deux écarts gardent un défaut DANS LE CODE D'INGESTION, non corrigé par cette chasse (laissés
> « motif » : ils ne changent effet qu'à la ré-ingestion). **Corriger le code PUIS ré-ingérer.**
```bash
# D-53 — le dédoublonnage CatNat avale un arrêté multi-événements (Saint-Paul 23 vs 24 GASPAR) :
#   corriger la clé de dédup dans src/labuse/ingestion/catnat.py (code), PUIS :
ssh labuse-vps 'sudo -u labuse /opt/labuse/venv/bin/labuse ingest-catnat'
# D-55 — OCS GE a le millésime « 2022 » EN DUR (src/labuse/ingestion/ocsge.py :186/:250 + filtres/sources.py) :
#   lire le millésime de la source au lieu du littéral (code), PUIS ré-ingérer OCS GE au prochain millésime.
```
**Vérif** CatNat : `SELECT count(*) FROM catnat_arretes WHERE insee='97415';` = 24 (plus 23).

### 9.5 — Étiquettes de millésime CatNat / AZI (`data_sources.source_millesime`)
> D-62/D-63 : la re-moisson (`job_sur_clic`) met la TABLE à jour mais pas le texte `source_millesime`
> → la vitrine affiche une date plus vieille que la donnée. Deux options :
```bash
# (a) rafraîchir le libellé depuis la date réelle de la table (UPDATE ciblé sur data_sources = table de RÉFÉRENCE) :
ssh labuse-vps "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse <<'SQL'
UPDATE data_sources SET source_millesime =
  'GASPAR — arrêtés CatNat 974 (paginés, ' || to_char((SELECT max(ingested_at) FROM catnat_arretes),'DD/MM/YYYY') || ')'
  WHERE id = 97;
UPDATE data_sources SET source_millesime =
  'GASPAR azi+tri par commune (' || to_char((SELECT max(maj_at) FROM azi_communes),'DD/MM/YYYY') || ')'
  WHERE id = 114;
SQL"
# (b) alternative pérenne : faire DÉRIVER le millésime de la table au point de lecture (code) — à cadrer.
```
**Vérif** : page Sources prod → CatNat « …28/09/2026 », AZI « …14/09/2026 » (= `max()` des tables).

### 9.6 — Décisions actées (aucun geste technique)
- **D-64 — FERMÉ par décision (Vic)** : les 17 vitrines sans `source_millesime` restent telles
  quelles. Les **dates des sources sont réservées à l'ADMIN** (circuit/registre), pas exposées au
  client — **rien à changer côté client**. La donnée reste datée en table pour l'exploitation interne.
- **C-38 — gardé tel quel** : le Comparatif dit « hors zonage PLU », la fiche « commune au RNU »
  (même fait, phrasé différent, **aucune valeur fausse**) — choix assumé DOCS-FIX-1 P5, non rouvert.

### 9.7 — Vérification du fix (banc rejouable)
```bash
# en local (le banc frappe une API) — après déploiement, viser l'API prod si le réseau le permet :
LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" PYTHONPATH=src \
  ~/Desktop/labuse/.venv/bin/python -m scripts.coherence.chasse_donnees --api http://127.0.0.1:8750
```
**Critère** : `Bilan : 25 OK · 0 ECART · 0 SKIP (25 gardes)`. Témoins prod : export md CW0658 « Surface
cadastrale : 25 633 m² » ; PDF (gabarit/dossier/comparatif/étude-zone) portent le pied « Données LABUSE
au <date du run servi> » ; une parcelle disparue refuse ses documents.

> **Rien du `run_seq=16`/q_v19 n'est déployé.** Le résiduel servi reste `run_seq=15`, le scoring `q_v18`.

---

## Annexe A — Tables clients JAMAIS touchées (hors périmètre)

Aucun dump/restore de ce plan ne les cible (tous les `pg_restore` sont `-t <table>` sur la liste des phases 3–4) :
`comptes`, `sessions`, `pipeline_entries`, `pipeline_projet`, `projet_parcelles`, `module_division`, `alertes`/`watch_zones`, `saved_filters`, `documents_generes`, `contact_*`, `bilan_params`/`bilan_ratios`, `suggestions`, abonnements/Stripe. 
Les 1 353 disparues sont **marquées** (`cadastre_disparue_le`), **jamais supprimées** — précisément pour ne pas déclencher les FK CASCADE vers `pipeline_entries`/`projet_parcelles`/`alertes`/`module_division` (46 parcelles disparues sont référencées client).

## Annexe B — Rollback

- **Code** : re-déployer le SHA précédent avec `deploy_app.sh` (git checkout du SHA + redeploy) — pas de state à défaire.
- **Données run** : `sync-run.sh` est idempotent par label ; rebasculer les pointeurs sur `q_v16` (`golden promote q_v16` + `residuel-serve <seq q_v16>`) ramène le servi précédent sans supprimer q_v18. ⚠ `residuel-serve q_v16` relancera un `rebuild` : s'assurer que `parcel_couche_intersection` reste `fraiche()` (sinon rebuild île) — re-copier depuis le Mac si besoin.
- **parcels (delta)** : le delta 3a est non destructif ; pour revenir à l'état pré-cadastre en prod, restaurer `parcels` depuis le **dump prod de Phase 0.2** (pas le dump Mac `parcels-AVANT-CADASTRE`, qui est l'état local). Ne jamais `DROP` parcels (FK client).
- **Intersections** : re-copier depuis le Mac (Phase 4bis-1) ; jamais `build-intersections` en prod.
- **Prod globale** : le dump de Phase 0.2 (vérifié `pg_restore --list`).

## Annexe C — Ce qui n'est PAS dans ce déploiement

- **Sources 28 (érosion) / 46 (classement sonore) / 10 (RPG)** : non entrées dans q_v18 (URL/parseur à adapter, cf. RAPPORT §5.4) — report à un run ultérieur.
- **Source 86 SIRENE** : ingestion en échec (INSEE orphelin 97454) — hors périmètre.
- **Tables de travail locales** `_cad_sm1_staging`/`_cad_sm1_*` : **non expédiées**, droppables en local après coup.
- **Run `run_seq=16` / `q_v19`** (CHASSE-DONNEES-FIX-1 suite 1, PLU au moteur) : CANDIDAT local
  `is_served=false`, **NON déployé** (il prouve que q_v19 ≡ q_v18). Le servi reste `run_seq=15` / `q_v18`.
  Ne pas `sync-run`, ne pas `residuel-serve 16`, ne pas `golden promote q_v19`. Cf. Phase 9.
- Durées = **estimations** (set-based SQL + transferts) ; chaque commande imprime sa durée réelle, et les gardes (import-smoke, comptages sync-run, golden) sont les vrais critères d'arrêt.
