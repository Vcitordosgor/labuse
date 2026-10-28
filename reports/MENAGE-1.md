# MENAGE-1 — où partent les gigaoctets, et ce qu'on peut enlever

**Branche** `audit/menage-1` · worktree `~/Desktop/labuse-menage` · **PHASE A — AUDIT LECTURE SEULE.**
Rien n'a été supprimé, déplacé, compressé, vidé ni réécrit. Aucun `rm`, `DROP`, `TRUNCATE`, `VACUUM`, `git gc`, `filter-repo`, `docker prune`. Seules des mesures (`du`, `df`, `ls`, `git count-objects`, `git rev-list`, `SELECT`/`pg_*_size`) ont été exécutées, sur le Mac et sur le VPS (`ssh labuse-vps`, lecture seule).

Date de mesure : **2026-10-28**.

> **⚠️ Urgence Mac.** Le disque du Mac est à **649 Mo libres** (`/System/Volumes/Data` 100 %). C'est le point chaud. Le VPS est à ~21 Go libres (79 %), confortable mais à surveiller. Toutes les « commandes exactes » ci-dessous sont **pour la phase B** et ne seront lancées qu'après ton feu vert, case cochée.

> **⚠️ Ordre imposé en phase B (Mac).** Avec 649 Mo libres, un `VACUUM FULL` sur une grosse table est **impossible** (il lui faut un scratch ≈ la taille de la table). Il faut **d'abord libérer du disque** (worktrees mergés, vieux dump VPS) **puis** faire le ménage Postgres. Détail en A4.

---

## Liste à cocher — triée par gain, par machine

Convention : `[ ] chemin/objet — taille — sûr / à décider — commande exacte (phase B)`.
« sûr » = reconstructible ou rebut explicite, aucune perte de donnée. « à décider » = demande ton arbitrage (frontière run précédent, table lue ou non, livrable non archivé). « à garder » = jamais proposé (liste en bas).

### MAC — SÛR (≈ 9,8 Go)

- [ ] `~/Desktop/labuse-recette-prod` (worktree) — **3,4 Go** — sûr — branche `fix/recette-prod-1` **mergée** dans main, arbre propre — `git -C ~/Desktop/labuse worktree remove ~/Desktop/labuse-recette-prod`
- [ ] `~/Desktop/labuse-vitesse2` (worktree) — **3,2 Go** — sûr — branche `fix/vitesse-2` **mergée**, propre — `git -C ~/Desktop/labuse worktree remove ~/Desktop/labuse-vitesse2`
- [ ] `~/Desktop/labuse-etatfix` (worktree) — **3,1 Go** — sûr — branche `fix/donnees-etat-fix-1` **mergée**, propre — `git -C ~/Desktop/labuse worktree remove ~/Desktop/labuse-etatfix`
- [ ] `~/Desktop/labuse/.local/ortho-proxy-cache` — **100 Mo** — sûr — cache proxy ortho, reconstruit à la demande — `rm -rf ~/Desktop/labuse/.local/ortho-proxy-cache`

### MAC — À DÉCIDER (≈ 20–22 Go)

- [ ] **Vieux runs dans le Postgres LOCAL** (`~/labuse-pgdata`) : runs `q_v16`, `q_v13_sources1`, `q_v11_m137` et antérieurs, dans `dryrun_cascade_results`, `score_labuse`, `parcel_p_score_v2`, `parcel_residuel_runs`, `dryrun_parcel_evaluations` — **~8 à 10 Go récupérables après VACUUM** — à décider (confirmer la frontière « run précédent », cf. A1.1) — SQL en A1.1, puis `VACUUM (FULL, ANALYZE) <table>;`
- [ ] `~/labuse-backups/vps/hebdo-labuse-labuse-20261018-133004.dump` — **6,4 Go** — à décider — 3ᵉ dump VPS le plus récent (on garde les deux du 27/10) — `rm ~/labuse-backups/vps/hebdo-labuse-labuse-20261018-133004.dump`
- [ ] `~/Desktop/labuse-radaretat` (worktree) — **3,1 Go** — à décider — branche `audit/radar-etat-1` **mergée** MAIS contient des **livrables non suivis** `docs/audit-2026-10/radar-etat-1/` → **archiver d'abord**, puis `git -C ~/Desktop/labuse worktree remove --force ~/Desktop/labuse-radaretat`
- [ ] Schéma `poubelle` du Postgres LOCAL — **1,63 Go** — à décider — schéma « corbeille » explicite (34 tables : `m6_snapshot_mvt_post2a/b`, `m6_a02_backup_plu_dup`, `algo2_prop_features`…) — `DROP SCHEMA poubelle CASCADE;` (après vérif qu'aucun code ne le lit) puis `VACUUM`
- [ ] `~/labuse-backups/sources-maj-1/` — **275 Mo** — à décider — dumps de rollback d'avant la MAJ cadastre (10/10) ; supprimables si la MAJ cadastre est jugée stable — `rm -rf ~/labuse-backups/sources-maj-1`
- [ ] Caches reconstructibles du Postgres LOCAL : `mvt_tile_cache` (191 Mo) + `mvt_parcels` (251 Mo) + petits `*_cache` — **~0,44 Go** — à décider — reconstructibles par les jobs de tuiles — `TRUNCATE mvt_tile_cache;` (+ rebuild) ; `mvt_parcels` regénérée par le job tuiles
- [ ] `frontend/node_modules` des worktrees actifs `labuse-main` + `labuse-etatfix2` — **195 Mo ×2** — à décider — reconstructible par `npm ci` — `rm -rf ~/Desktop/labuse-main/frontend/node_modules` (réinstaller avant dev)

### VPS — SÛR (≈ 0,3 Go — faible intérêt)

- [ ] `/opt/labuse/app-avant-1028b` + `/opt/labuse/app-avant-etatfix-20261028-0249` — **~0,3 Go réels** — sûr mais faible — ⚠️ ces copies semblent peser 7,7 Go chacune mais **leurs données sont hard-linkées** (même inode, link count 3) ; les supprimer ne rend que le code/`dist`/`node_modules` non-linkés (~300 Mo). **Garder la plus récente** (rollback du déploiement courant). — `sudo rm -rf /opt/labuse/app-avant-etatfix-20261028-0249` (garder `app-avant-1028b`)

### VPS — À DÉCIDER (≈ 9 Go)

- [ ] **Vieux runs dans `dryrun_cascade_results` (PROD)** : `q_v11_m137` (15,9 M lignes, ~2,2 Go heap) + `q_v13_sources1` (17,6 M lignes, ~2,6 Go heap) — **~5 Go heap + part d'index ≈ ~7 Go du total de 16 Go** — à décider — on garde `q_v19_sources` (servi) + `q_v18_sources` (précédent) — `DELETE FROM dryrun_cascade_results WHERE run_label IN ('q_v11_m137','q_v13_sources1'); VACUUM (FULL, ANALYZE) dryrun_cascade_results;`
- [ ] Table `dryrun_cascade_results` **dans son ensemble** (16 Go, le plus gros objet de la prod) — à décider — c'est une table *dryrun* (la cascade **servie** vit dans `cascade_results`, 1,4 Go, séparée). Trancher : la prod a-t-elle besoin d'un *dryrun* en ligne ? Si non, gain bien supérieur aux ~7 Go ci-dessus.
- [ ] Tables PROD nommées obsolètes (`*_backup` / `*_snapshot` / `*_prebascule` / `*_legacy` / `*_pre_v8` / `*_avant` / `*_staging` / `*_rerun`) — **~2 Go** — à décider — `dryrun_parcel_evaluations` 325 Mo, `score_snapshot_parcelles` 321 Mo, `m6_a02_backup_plu_dup` 252 Mo, `m6_snapshot_mvt_post2a/b` 221 Mo ×2, `_cad_sm1_staging` 176 Mo, etc. — `DROP TABLE <t>;` au cas par cas + `VACUUM`

### GIT (`.git` partagé, 4,4 Go) — À DÉCIDER (≈ 3,5–4 Go, nécessite réécriture d'historique)

- [ ] Captures PNG dans l'historique (`docs/design` 1,83 Go, `docs/audit-2026-09` 830 Mo, etc.) — **~4,1 Go des 4,35 Go du pack** — à décider — **aucune suppression simple ne les récupère** (presque tout est encore suivi dans HEAD) ; il faut une **réécriture d'historique** + `push --force` + recréer tous les worktrees/clones. Détail, coût et alternative sans réécriture en A3. **Non exécuté ici** (hors périmètre lecture seule).

### Totaux récupérables

| Machine | Sûr | À décider | Remarque |
|---|---|---|---|
| **Mac** | **~9,8 Go** | **~20–22 Go** | disque à 649 Mo libres → prioritaire |
| **VPS** | ~0,3 Go | **~9 Go** | 21 Go libres, moins urgent |
| **Git** | 0 | ~3,5–4 Go | réécriture d'historique requise |

---

## A1 — le Mac

Vue d'ensemble des gros postes mesurés (`du -sh`) :

| Chemin | Taille | Ce que c'est | Verdict |
|---|---|---|---|
| `~/labuse-pgdata` | **55 Go** | base Postgres locale (dev/travail) | détail A1.1 |
| `~/labuse-backups` | **20 Go** | dumps VPS + rollback sources | détail A1.4 |
| `~/Desktop/labuse` | **17 Go** | clone principal (détaché) | détail A1.2 |
| `~/Desktop/labuse-main` + 6 worktrees | ~3,1–3,4 Go ×7 | worktrees | détail A1.3 |
| `~/.cache` | 3,8 Go | caches outils (non LABUSE) | A1.4, hors périmètre |
| `~/Library/Caches` | 3,5 Go | caches système/outils | A1.4, hors périmètre |
| `~/.openclaw` `~/.hermes` `~/.codex` `~/.claude` | 2,4 / 1,8 / 1,7 / 1,0 Go | agents | A1.4, taille seule |

### A1.1 — Base Postgres locale (`~/labuse-pgdata`, 55 Go)

Connexion lecture seule `psql postgresql:///labuse`. La base **`labuse` = 54 Go** (>99,5 % des données ; les autres bases `labuse_test`, `labuse_c5`, `labuse_pd1`… totalisent < 400 Mo, à garder, utilisées par les tests). Schémas : `public` 52 Go (271 tables), `poubelle` 1,63 Go (corbeille), `pg_catalog` 25 Mo. Heap 35 Go / index 8,5 Go.

**Top tables / index (local) :**

| Table / index | Total | dont vieux runs |
|---|---|---|
| `dryrun_cascade_results` (+ pkey 1,28 Go + index) | **12 Go** | `q_v13_sources1` 29,4 % ≈ 3,5 Go (ancien) ; servi = `q_v19_sources` |
| `score_labuse` | **8,8 Go** | 4 runs (q_v16/18/19/20) ; 3 non servis ≈ 75 % des lignes (volume surtout TOAST motifs) |
| `spatial_layers` | 4,2 Go | donnée vivante (à garder) |
| `cascade_results` | 3,75 Go | cascade servie vivante (à garder) |
| `parcel_p_score_v2` | 3,68 Go | 4 runs ; 3 non servis ≈ 2,7 Go |
| `p_model_dataset_v2bis` / `_v2` / `_` | 1,85 / 1,60 / 0,78 Go | générations successives du dataset d'entraînement ; `_v2` + `_` (≈ 2,4 Go) **candidats si superposés par `_v2bis`** (à confirmer côté code) |
| `tuyau_subdivise`, `spatial_layers_sub`, `p_model_ext_dataset`, `parcel_couche_intersection`, `parcels`… | 1–1,8 Go chacun | vivants (à garder) |
| `parcel_residuel_runs` | 391 Mo | 5 runs (seq 1,13,15,16,17) ; seq 13/15/16 ≈ 60 % |

**Runs — registre faisant foi (`residuel_runs`) :**

| run_seq | label | servi | épinglé | date |
|---|---|---|---|---|
| 1 | legacy mosaïque | non | **oui (pinned)** | 07–19/08 |
| 13 | q_v16 | non | non | 05/10 |
| 15 | q_v18 | non | non | 11/10 |
| 16 | q_v19 | non | non | 17/10 |
| **17** | **q_v20** | **OUI (servi)** | non | 21/10 |

Côté scoring (`score_labuse_runs`) : `q_v20` sert, sur cascade `q_v19_sources` (cohérent). **Frontière de conservation proposée : garder `q_v20` (servi) + `q_v19` + `q_v18` (marge rollback), épinglé seq 1 ; proposer à la suppression `q_v16` / `q_v13_sources1` / `q_v11` et antérieurs.** À toi de confirmer si « précédent » = q_v19 seul ou q_v19+q_v18.

**Caches reconstructibles (local) :** `mvt_parcels` 251 Mo, `mvt_tile_cache` 191 Mo (2 232 tuiles), + petits `fiche_cache`/`zone_isochrone_cache`/`commune_contexte_cache`… ≈ **445 Mo**, tous rebâtissables depuis les tables sources.

**Bloat (sans VACUUM) :** négligeable. Seules `spatial_layers` (~6,8 % mort ≈ ~115 Mo) et `parcel_p_score_v2` (~7,2 % ≈ ~235 Mo) ont du mort notable ; **~350 Mo** récupérables par VACUUM, estimé — levier mineur face aux vieux runs.

> SQL phase B (exemple, à adapter après confirmation de la frontière) :
> ```sql
> -- runs antérieurs au précédent, hors servi/épinglé
> DELETE FROM score_labuse        WHERE run_label IN ('q_v16');
> DELETE FROM parcel_p_score_v2   WHERE run_label IN ('q_v16','q_v18'); -- selon frontière
> DELETE FROM parcel_residuel_runs WHERE run_seq IN (13,15);           -- q_v16, q_v18
> DELETE FROM dryrun_cascade_results WHERE run_label IN ('q_v13_sources1');
> DELETE FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v13_sources1');
> VACUUM (FULL, ANALYZE) score_labuse;
> VACUUM (FULL, ANALYZE) dryrun_cascade_results;
> -- … idem par table
> ```
> ⚠️ `VACUUM FULL` exige un scratch ≈ taille de la table : **libérer d'abord le disque** (worktrees + dump VPS), ou utiliser `pg_repack`, ou dump→restore dans un cluster neuf.

### A1.2 — Clone principal `~/Desktop/labuse` (17 Go)

`du -sh` : `data` **7,0 Go** · `.git` **4,4 Go** (partagé par tous les worktrees — compté une seule fois) · `docs` 1,8 Go · `.venv` 1,4 Go · `qa` 809 Mo · `reports` 607 Mo · `outputs` 424 Mo · `captures` 280 Mo · `frontend` 216 Mo · `.local` 102 Mo.

**Données brutes `data/` (7,0 Go, gitignorées — `data/*` est couvert par `.gitignore`)** et leur re-téléchargeabilité :

| Bloc | Taille | Re-téléchargeable ? | Verdict |
|---|---|---|---|
| `data/cosia` | 3,3 Go | oui (IGN COSIA, archive 7z publique) | à garder (lourd à re-DL ; sert l'ingestion) |
| `data/ortho_irc` | 1,9 Go | oui (IGN ortho IRC) | à garder |
| `data/insee_rp` | 400 Mo | oui (INSEE) | à garder |
| `data/ml` | 399 Mo | **non — dérivé** (crops 277 Mo, flair 93 Mo, `embeddings.npy`, `probe_logreg.joblib`) | **à garder (artefacts/modèle)** |
| `data/rgealti` | 360 Mo | oui (IGN RGE Alti) | à garder |
| `data/dvf_histo` | 348 Mo | partiel (DVF data.gouv ; un millésime peut être retiré) | **à garder** |
| `data/plu_reglements` | 197 Mo | partiel (GPU/mairies ; PDF parfois retirés) | **à garder** |
| `data/ban`, `ortho_tiles`, `edf_hta`, `tcsp`, `cerfa`, `dvf`… | < 80 Mo | oui | à garder |

→ **`data/` entier = à garder** (source de l'ingestion locale ; blocs lourds à re-DL, deux blocs non re-téléchargeables). Pas proposé à la suppression.

Autres postes : `.venv` 1,4 Go reconstructible (`pip install`), mais c'est l'environnement de dev actif — à garder. `.local/ortho-proxy-cache` 100 Mo = **cache reconstructible → SÛR** (seul poste `.local` non trivial ; `pige-archives` 1,9 Mo à garder). `docs`/`qa`/`reports`/`captures` : contenu suivi en git (voir A3 pour le coût historique) — ne pas supprimer sur disque (ce sont les livrables versionnés).

### A1.3 — `labuse-main` et les worktrees

Un **seul** dépôt (`~/Desktop/labuse/.git`), 8 worktrees liés. Chaque worktree ≈ 3,1 Go = fichiers **suivis** dupliqués au checkout (`docs` 1,8 Go + `qa` 723 Mo + `captures` 280 Mo + `reports` 277 Mo). 3 worktrees portent en plus `frontend/node_modules` 195 Mo (reconstructible).

> Note : le mandat citait `labuse-docs2` et `labuse-postdeploy` — **ils n'existent plus** (déjà retirés). Jeu réel ci-dessous.

| Worktree | Branche | Mergée dans main ? | Arbre propre ? | Verdict |
|---|---|---|---|---|
| `labuse-main` | `main` | — (c'est main) | `?? logs/` (non suivi, mineur) | à garder |
| `labuse-menage` | `audit/menage-1` | — (courant) | propre | à garder (ce mandat) |
| `labuse-etat2` | `audit/donnees-etat-2` | **NON mergée** | propre | **à garder** (travail actif) |
| `labuse-etatfix2` | `fix/donnees-etat-fix-2` | **NON mergée** | propre | **à garder** (travail actif) |
| `labuse-recette-prod` | `fix/recette-prod-1` | **mergée** | propre | **SÛR à retirer** |
| `labuse-vitesse2` | `fix/vitesse-2` | **mergée** | propre | **SÛR à retirer** |
| `labuse-etatfix` | `fix/donnees-etat-fix-1` | **mergée** | propre | **SÛR à retirer** |
| `labuse-radaretat` | `audit/radar-etat-1` | **mergée** | `?? docs/audit-2026-10/radar-etat-1/` **non suivi** | **à décider** — archiver les livrables puis retirer |

Gain worktrees : **~9,7 Go sûr** (3 worktrees mergés propres) + **3,1 Go à décider** (radaretat, après archivage des livrables). Les deux branches non mergées (`etat2`, `etatfix2`) restent.

### A1.4 — Hors dépôt

**`~/labuse-backups` (20 Go) :**

| Élément | Taille | Verdict |
|---|---|---|
| `vps/labuse-labuse-20261027-173056.dump` | 6,5 Go | **à garder** (dump le + récent) |
| `vps/labuse-labuse-20261027-133004.dump` | 6,5 Go | **à garder** (2ᵉ + récent) |
| `vps/hebdo-labuse-labuse-20261018-133004.dump` | 6,4 Go | **à décider** (3ᵉ, supprimable) |
| `sources-maj-1/` | 275 Mo | à décider (rollback MAJ cadastre 10/10) |
| `M7_SECRETS.txt` | 339 o | **à garder (jamais supprimer)** |
| `labuse-c6-donnees-usage-2026-08-26.dump` | 304 Ko | à garder (négligeable) |
| `audit-paiement-rendus/` | 2,8 Mo | à garder (négligeable) |
| `watch_prod.log` | 904 Ko | rotation possible, négligeable |

**Caches outils (A1.4) — mesurés, PAS proposés à la suppression (non spécifiques LABUSE ou usage à préciser) :**

- `~/.cache` 3,8 Go : `codex-runtimes` 1,6 Go, `uv` 1,1 Go, `puppeteer` 1,0 Go, `torch` 89 Mo. → caches d'outils, reconstructibles mais partagés/hors LABUSE.
- `~/Library/Caches` 3,5 Go : `Google` (Chrome) 1,2 Go, `ms-playwright-mcp` 890 Mo, `camoufox` 670 Mo, `pip` 237 Mo, `node-gyp` 126 Mo, `pnpm` 106 Mo. → outils/navigateur, aucune part clairement LABUSE.
- `~/.npm` 1,4 Go, caches Playwright `~/Library/Caches/ms-playwright` 72 Ko.
- Agents : `~/.openclaw` 2,4 Go · `~/.hermes` 1,8 Go · `~/.codex` 1,7 Go · `~/.claude` 1,0 Go. **Taille seulement, rien proposé** (usage non établi, per mandat).

> Ces caches représentent ~11 Go cumulés. S'ils devaient être vidés, ce serait une décision outils/système hors de ce mandat ; je les documente sans les toucher ni les recommander.

---

## A2 — le serveur (`ssh labuse-vps`, lecture seule)

Hôte `vps-5563949c`, Ubuntu 24.04, TZ `Indian/Reunion`. **Un `pg_dump` planifié tournait pendant l'audit** (sauvegarde quotidienne) — les chiffres bougeaient d'eux-mêmes.

**Disque (`df -h`) :** un seul fs utile `/dev/sda1` **96 Go, 75 Go utilisés, ~21 Go libres (79 %)**. `/boot` et EFI négligeables.

**`/opt/labuse` :** `app` 7,7 Go (dont `data` 7,0 Go — mêmes blocs que le Mac, cf. A1.2), `venv` 904 Mo, + copies de déploiement `app-avant-*`.

> **★ Nuance importante :** les deux `app-avant-*` semblent peser ~7,7 Go chacune, mais leurs gros fichiers `data` sont **hard-linkés** avec `app` (même inode, link count 3 — vérifié sur `COSIA_D974_2025.7z`). `du --total` des trois dossiers = **8,0 Go** (pas 23 Go). Supprimer les deux copies ne rend que **~300 Mo** de code/`dist`/`node_modules` non-linkés. **Faible levier ; garder au moins la plus récente (rollback du déploiement courant).**

**Sauvegardes VPS :** pas de `~/labuse-backups` ni `/opt/labuse/backups` ; les vrais dumps vivent dans **`/var/backups/labuse/` (17 Go)** :

| Dump | Taille | Date | Verdict |
|---|---|---|---|
| `labuse-labuse-20261028-133004.dump` | 7,12 Go | 28/10 13:49 | **à garder** (le + récent complet) |
| `labuse-labuse-20261028-031157.dump` | 7,12 Go | 28/10 03:32 | **à garder** (2ᵉ) |
| `labuse-labuse-20261028-170218.dump` | en cours | 28/10 17:xx | ⚠️ **en écriture — ne pas toucher** |

Rotation à 7 dumps (script `backup.log`), dumps « lean » (`-Fc`, exclut `sauvegarde_*` et les grosses tables dryrun/cascade/p_model/snapshot). Pas de vieux dump à retirer aujourd'hui (seulement 3 présents). Les `.dump` sous `/var/lib/postgresql/` sont de minuscules dumps de schéma (2–47 Ko) — à ignorer.

**Journaux :** `/var/log/journal` 452 Mo, `caddy` 100 Mo, `dmesg` 65 Mo, reste petit. **Total < 1 Go — pas un levier** face à la base.

**Postgres PROD (SELECT seuls) :** base `labuse` **= 43 Go** (via `sudo -u postgres psql`, mot de passe de `labuse.env` **non affiché**). Servi (`served_manifest.json`) : scoring **q_v20**, cascade **q_v19_sources**, division q_v19, résiduel seq 17 (promu 27/10 par DEPLOY-1027). **Précédent** : q_v18 / q_v18_sources / seq 15. Épinglé : seq 1 (legacy). `run_bascule_journal` vide.

| Relation PROD | Total | Vieux runs |
|---|---|---|
| **`dryrun_cascade_results`** (+ pkey 2,3 Go + index) | **16 Go** | 4 runs : `q_v18_sources` 21,2 M, `q_v19_sources` 21,1 M, `q_v13_sources1` 17,6 M, `q_v11_m137` 15,9 M lignes |
| `score_labuse` | 5,2 Go | |
| `spatial_layers` | 3,1 Go | vivant |
| `parcel_p_score_v2` | 2,1 Go | |
| `cascade_results` (**cascade servie**, séparée) | 1,42 Go | à garder |

**★ Cible principale PROD :** dans `dryrun_cascade_results`, **`q_v11_m137` + `q_v13_sources1` (~33,5 M lignes, ~4,9 Go heap + part d'index)** sont bien antérieurs au servi (v19) et au précédent (v18) → candidats stales. À arbitrer plus largement : la prod a-t-elle besoin de *cette table dryrun* en ligne (la cascade servie est ailleurs) ? Si non, gain ≫.

**Tables nommées obsolètes (PROD, ~2 Go) :** `dryrun_parcel_evaluations` 325 Mo, `score_snapshot_parcelles` 321 Mo, `m6_a02_backup_plu_dup` 252 Mo, `m6_snapshot_mvt_post2a/b` 221 Mo ×2, `_cad_sm1_staging` 176 Mo, `p_model_static_pre_v8` 79 Mo, `parcel_residuel_base_legacy` 38 Mo, `*_prebascule`, `*_avant_littoral`, `parcel_residuel_rerun`… — à décider au cas par cas.

**Marge après sauvegarde complète :** 96 Go cap − 75 Go utilisés = **~21 Go libres**. Un dump `-Fc` complet (base 43 Go → ~7–10 Go compressé ; les dumps complets récents font 7,12 Go) **tient** (~11 Go de marge). Un dump **non compressé** (~43 Go) **ne tiendrait pas**. La rotation à 7 × 7,1 Go (~50 Go) **ne peut coexister** avec les 45 Go de data dir — aujourd'hui OK car seulement 3 dumps. Marge réelle mais mince ; le meilleur levier côté DB reste les vieux runs dryrun + les tables obsolètes.

---

## A3 — le dépôt git

**`.git` partagé = 4,4 Go** (`~/Desktop/labuse/.git`, `size-pack` 4,35 Go, 68 211 objets, bloat entièrement packé). 28 649 blobs uniques, 5,51 Go décompressés.

**Le bloat n'est PAS quelques fichiers géants** : le top-50 ne fait que 545 Mo. **94 % du pack = des PNG de captures** (6 227 objets, ~4,1 Go). Par sous-arbre :

| Sous-arbre | PNG dans l'historique | encore suivi dans HEAD |
|---|---|---|
| **`docs/design`** | **1,83 Go** (1354 PNG) | 189 seulement → ~1165 sont de **vieilles versions churned** (pur candidat réécriture) |
| `docs/audit-2026-09` | 830 Mo (919 PNG) | 946 |
| `docs/audit-2026-10` | 223 Mo | 894 |
| `docs/GABARIT` | 102 Mo | 165 |
| `reports/RECETTE-OUTILS-1`, `qa/m105b`, `captures/*`… | longue traîne | oui |

**Top objets (introduits par) :** PDF `qa/cosia/cartes_entrantes_recomposition.pdf` 51 Mo (`66ff750d7`, 04/08), `cartes_mouvements_cosia.pdf` 38 Mo (`7abc5265b`), CSV `qa/m38/vigilances_m38_digest.csv` 34 Mo, HTML `reports/j3-revue/DOSSIER-REVUE-J3.html` 20 Mo, PDF `docs/audit-2026-10/PARCOURS-FIX-1/PARCOURS.pdf` 19,4 Mo, zips `docs/mandats/O12_*` ~16 Mo, etc. Objets 26–50 = PNG `docs/audit-2026-09/RETOURS-*/captures/*`.

**Encore suivi vs retiré :** **5 199 PNG sont encore suivis dans HEAD** (sur 6 227). Donc `git rm --cached` seul **ne récupère rien** sur le pack — il faut une **réécriture d'historique**.

**Couverture `.gitignore` — fuite PAS refermée pour la plus grosse catégorie :** pas de règle large `*.png` / `**/captures/`. Sont **committables** aujourd'hui : `docs/design/*.png`, `docs/audit-2026-11/**/captures/*.png`, `reports/<new>/*.pdf`, `captures/*.png` (le `captures/` racine n'est **pas** ignoré), `docs/mandats/*.zip`. Seul `data/*` est bien couvert. → les futures captures d'audit **re-gonfleront** l'historique.

### Coût d'un nettoyage d'historique (NON fait)

- **Option A — réécriture (`git filter-repo`)** pour purger `docs/design/*.png` (vieilles versions), `docs/**/captures/*.png`, gros PDF/zip/HTML/CSV. **Gain ~3,5–4 Go.** Coût : **réécrit tous les SHA** → `push --force`, **tous les worktrees et clones doivent être recréés** (y compris le clone `~/Desktop/labuse` et les 8 worktrees), références/PR cassées, risque élevé si qqn a du travail non poussé. À faire en **fenêtre planifiée, dépôt au repos, une seule personne**, après sauvegarde du `.git`.
- **Option B — sans réécriture (recommandée d'abord)** : ajouter des règles `.gitignore` larges + `git rm --cached -r` des gros arbres (`docs/design` PNG, `captures/`) pour qu'ils **cessent d'être re-dupliqués dans les nouveaux commits**. **Ne réduit PAS l'historique** (les 4,1 Go restent dans le pack), mais **stoppe la croissance** sans risque. Les blobs déjà présents resteront jusqu'à une éventuelle Option A.

Recommandation : **B maintenant** (ferme la fuite), **A plus tard** en fenêtre dédiée si les 4 Go justifient le risque.

---

## A4 — éviter que ça revienne (propositions, non appliquées)

1. **Garde-fou gros fichiers au commit** (hook `pre-commit` ou `.github`) : refuser tout fichier > ~2 Mo (et tout `*.png`/`*.pdf` sous arbres d'audit) hors liste blanche. C'est la racine du bloat `.git`.
2. **`.gitignore` large** : `**/captures/`, `captures/`, `docs/design/*.png` (ou héberger les PNG de design ailleurs), `*.har`, `docs/mandats/*.zip`, `docs/**/*.png` sous arbres d'audit. Ferme la fuite A3 §gitignore.
3. **Purge auto des runs Postgres** : job (sur le modèle `scripts/coherence/`) qui garde **servi + N précédents** (N=2) hors `is_served`/`is_pinned`, puis `VACUUM`. Évite l'empilement q_v11→q_v20 (cause des 12–16 Go de `dryrun_cascade_results`).
4. **Retrait auto des worktrees mergés** : script qui `git worktree remove` les worktrees dont la branche est mergée dans main **et** l'arbre propre (sinon alerte « livrables non suivis », cf. `labuse-radaretat`).
5. **Rotation journaux** : journald déjà capé (~450 Mo) ; ajouter `logrotate` sur `/var/log/labuse` et `/var/log/caddy` si croissance.
6. **Alarme disque Mac** : le Mac est à **649 Mo** — ajouter un contrôle `df` (vigie/agent) alertant sous un seuil (ex. 5 Go), car c'est le poste qui coince le travail quotidien.

---

## Rappel — jamais proposé à la suppression (à garder)

- **Runs servis + précédent** (local & prod) : q_v20 (servi), q_v19/q_v18 (rollback), résiduel seq 17 + épinglé seq 1 ; cascade servie `cascade_results` + `q_v19_sources`.
- **2 sauvegardes les + récentes** Mac (deux dumps 27/10) et VPS (deux dumps 28/10) ; `~/labuse-backups/M7_SECRETS.txt` ; tout `.env` et `/etc/labuse/labuse.env`.
- **Tables clients & flux quotidiens** : comptes, projets, CRM, copilote, courriers, Bilans, Études ; BODACC, Sitadel, DPE, SIRENE, DVF.
- **Données non re-téléchargeables** : `data/ml` (dérivé + modèle `probe_logreg.joblib`), `data/dvf_histo` et `data/plu_reglements` (millésimes/PDF parfois retirés amont).
- **Modèle promotrice** (gitignoré : `docs/audit-2026-10/bilan-1/*.xlsx`, `reports/q-v14/*.pkl`) et tout ce dont dépend un test/témoin (bases `labuse_test*`, `labuse_c5`…).
- **Worktrees non mergés** `labuse-etat2`, `labuse-etatfix2` (travail actif).

*Fin de la PHASE A — aucune donnée supprimée, déplacée ou modifiée. Phase B sur feu vert, case par case.*

---

# PHASE B — EXÉCUTION (2026-10-28, branche `fix/menage-1`)

Exécution de la liste **exacte** validée par Vic (« Rien d'autre »). Chaque geste ci-dessous a été joué,
mesuré, prouvé. Branche `fix/menage-1`, poussée, **pas de merge**. `df` avant/après par machine.
**Note disque Mac :** au moment de l'exécution le Mac n'était plus à 649 Mo mais à **19 Gio libres**
(du disque s'était libéré depuis l'audit) → les `VACUUM FULL` étaient confortables ; on a quand même
appliqué la règle « libre > taille de la table » avant chacun.

## `df` avant / après

| Machine | Avant | Après | Remarque |
|---|---|---|---|
| **Mac** (`/System/Volumes/Data`) | 188 Gi util. / **19 Gi libres** / 91 % | 171 Gi util. / **37 Gi libres** / 83 % | **+18 Gio** (rm + poubelle + VACUUM FULL) |
| **Base locale** `labuse` | **54 Go** | **44 Go** | −10 Go (runs purgés + VACUUM FULL) |
| **VPS** (`/`) | 78 G util. / 19 G libres / 81 % | 71 G util. / **26 G libres** / 74 % | DROP 11 tables + rm copie + rotation dump ; **le gros (~7 Go dryrun) arrive au VACUUM FULL de la nuit** |
| **`.git`** partagé | 4,4 Go | 4,4 Go | **inchangé par conception** (Option B ne réécrit pas l'historique ; elle ferme la fuite) |

## MAC

**(1)(2)(3) `rm`** — faits, vérifiés absents ensuite :
- `~/labuse-backups/vps/hebdo-labuse-labuse-20261018-133004.dump` (6,4 Go) ✓
- `~/Desktop/labuse/.local/ortho-proxy-cache` (100 Mo) ✓
- `~/labuse-backups/sources-maj-1/` (275 Mo) ✓

**(5) `DROP SCHEMA poubelle CASCADE`** — **preuve d'absence de lecture** : `grep` sur tout le dépôt
(`.py/.sql/.ts/.sh/.yaml`) → les 12 occurrences de `poubelle` sont soit des **écritures** (la commande
CLI `circuit purge-orphelines` qui *déplace vers* `poubelle` : `CREATE SCHEMA` + `ALTER … SET SCHEMA`),
soit des **commentaires**. **Aucun `FROM/JOIN poubelle.…`, aucun `search_path` `poubelle`.** DROP joué :
**35 objets** supprimés (1,89 Go libérés immédiatement). Schéma `poubelle` : **absent** ensuite.

**(4) Purge des vieux runs du Postgres local + VACUUM FULL table par table.**
Frontière confirmée par le registre `residuel_runs` : seq 17 = **q_v20 servi**, seq 16 = q_v19, seq 15 = q_v18,
seq 1 = **épinglé** (gardés) ; seq 13 = **q_v16** (purgé). `q_v13_sources1` purgé de la cascade.
DELETE (runs **gardés après** : q_v18/q_v19/q_v20 ; cascade q_v18_sources/q_v19_sources ; seq 1/15/16/17) :

| Table | DELETE | VACUUM FULL : avant → après |
|---|---|---|
| `score_labuse` (q_v16) | 431 663 | 8 780 → **5 711 Mo** |
| `parcel_p_score_v2` (run_id q_v16) | 431 663 | 3 683 → **1 618 Mo** |
| `parcel_residuel_runs` (seq 13) | 431 663 | 391 → **298 Mo** |
| `dryrun_parcel_evaluations` (q_v13_sources1) | 431 663 | 221 → **140 Mo** |
| `dryrun_cascade_results` (q_v13_sources1) | 17 599 544 | 12 Go → **8 269 Mo** |

**Règle « libre > taille table » appliquée AVANT chaque VACUUM FULL** (ordre du + petit au + gros pour
libérer au fur et à mesure) — les 5 tables passaient (libre 27→37 Gio). Registres de runs
(`residuel_runs`, `score_labuse_runs`, `p_score_v2_runs`) **non touchés** (hors liste A1.1 ; la provenance
historique reste lisible).

## VPS — `ssh labuse-vps`, aucun redémarrage du service

**Sauvegarde fraîche d'abord.** Une sauvegarde `backup-postgres` (dump lean `-Fc`) tournait déjà au
lancement (lancée hors de moi, 19:32→19:53) → **dump frais complet `labuse-labuse-20261028-193252.dump`
7,12 Go** présent avant tout geste destructeur. Tous les gestes faits **hors des heures de dump** (03 h /
13:30 / 17 h) : exécution ~20 h.

**(7) Tables obsolètes — DROP une par une, seulement les non-lues (preuve).** `grep` de chaque table :
- **DROP (11, référencées UNIQUEMENT dans `registre/tables.py` comme « purger … », soit aucune lecture de données)** :
  `_cad_sm1_staging` (0 réf.), `m6_a02_backup_plu_dup`, `m6_snapshot_mvt_post2a`, `m6_snapshot_mvt_post2b`,
  `parcel_zone_plu_prebascule`, `backup_spaul_ppr_avant_littoral`, `parcel_au_statut_pre_m32`,
  `parcel_au_statut_prebascule`, `backup_sp_ppr_avant_littoral`, `m6_p103_backup_dvf_surfaces`,
  `cascade_ext_avant`. DROP sans CASCADE (une dépendance aurait fait erreur) → 11/11 OK, 0 survivant.
  **~919 Mo** rendus. *(Le `COPY m6_snapshot_mvt_post2b` vu pendant l'audit était le `pg_dump`, pas du
  code applicatif.)*
- **GARDÉES (un lecteur de code existe — par prudence, hors DROP, remontées ici)** :
  `score_snapshot_parcelles` (**table vivante** : modèle SQLAlchemy, écrite par le scoring, lue par
  `monitoring`/`brulantes`), `parcel_residuel_base_legacy` (cible de swap **vivante** dans
  `faisabilite/residuel_runs.py`), `p_model_static_pre_v8` + `parcel_residuel_pre_v8` (lues par
  `scripts/rollback_v8_calibre.py`), `parcel_residuel_rerun` (lue par `scripts/bascule_v8_calibre.py`).
  → gain conservateur (~0,9 Go vs ~2 Go estimés) : « seulement celles qu'aucun code ne lit ».

**(6) `dryrun_cascade_results` (PROD).** Servi = q_v20 sur cascade **q_v19_sources** ; précédent =
**q_v18_sources**. Cibles `q_v11_m137` + `q_v13_sources1` = bien antérieures → **DELETE 33 500 354 lignes
en 64 s** (restent q_v18_sources + q_v19_sources). **`pg_repack` INDISPONIBLE** (ni binaire, ni extension
dans `pg_available_extensions`). **Effet du verrou vérifié** : `dryrun_cascade_results` est **lue au
runtime** (`renouvellement`, `models`, `courrier_compose`, `regles/*`, `solaire`) → un `VACUUM FULL`
(ACCESS EXCLUSIVE) **bloquerait ces lectures** le temps de la réécriture. Donc, comme demandé,
**VACUUM FULL programmé LA NUIT** : timer systemd **one-shot** `labuse-menage1-vacuumfull` →
**jeu. 2026-10-29 01:30 +04** (avant le dump de 03 h), wrapper `/opt/labuse/menage1_vacuumfull_night.sh`
(`lock_timeout 10 min`, journal `/var/log/labuse/menage1_vacuumfull.log`, puis **re-fumée** readyz + BY0083).
À 20 h la table est encore à 16 Go (33,5 M tuples morts) ; **~7 Go seront rendus après le VACUUM FULL**.
*(Vérif : `systemctl list-timers labuse-menage1-vacuumfull.timer` ; résultat au journal ci-dessus.)*

**(8) `rm -rf /opt/labuse/app-avant-etatfix-20261028-0249`** — fait. Copie de retour arrière **la plus
récente GARDÉE = `app-avant-radarfix2`** (28/10 16:52 ; la copie `1028b` du rapport n'existe plus, elle a
été remplacée). Données **hard-linkées** → ~297 Mo réels rendus (le reste des blocs reste porté par `app`
+ `app-avant-radarfix2`). **Aucun redémarrage.**

**Fumée après gestes serveur.** `readyz` = **200** (public `app.labuse.immo` ET interne `127.0.0.1:8000`).
**Fumée BY0083** : la fiche a été **reconstruite en process** (chemin réel `_fiche_servie`, lecture seule,
sans HTTP) sur la base **post-gestes** → **OK**, run servi **q_v20**, **77 clés**, `commune=Saint-Paul`,
`adresse=143 Rue Évariste de Parny`. *(Le fetch HTTP direct renvoie 401 — l'app exige une session ; le
login « pilote » de compat est mort ; d'où la fumée en process, qui exerce le vrai code de la fiche.)*

## GIT — Option B uniquement (pas de `git rm --cached`, pas de réécriture)

- **`.gitignore`** : bloc « MENAGE-1 » large — `captures/`, `captures-*/`, `**/captures/`,
  `docs/design/**/*.png`, `docs/GABARIT/**/*.png`, `docs/audit-*/**/*.{png,pdf}`, `*.har`,
  `docs/mandats/*.zip`, `**/deck_*.html`, `reports/**/DOSSIER-*.{html,pdf}`. Vérifié : **n'ignore
  aucun fichier déjà suivi** (`git check-ignore` sur `git ls-files` = vide).
- **Hook `pre-commit`** (`scripts/git-hooks/pre-commit`, posé par `install-hooks.sh`, `core.hooksPath`
  déjà en place) : **refuse tout fichier mis en index > 2 Mio hors liste blanche** (liste vide
  aujourd'hui, extensible + commentée), message clair, `--no-verify` en secours. Testé : refuse un
  fichier 3 Mio (exit 1), laisse passer un petit (exit 0), liste blanche OK. **Ne retire rien de déjà
  suivi** (les 395 fichiers > 2 Mio existants restent — décision d'historique = Vic). `.git` reste à 4,4 Go.

## PRÉVENTION

- **(10) Job `purge-runs` au registre** (`labuse.jobs` + habillage « L'usine » + `HORLOGES.csv`).
  Garde **servi + 2 précédents** (récence) + runs référencés (lignée/exceptions/démo) + épinglés ;
  supprime le reste puis **VACUUM ANALYZE (pas FULL : aucun verrou exclusif, sûr en prod)**.
  Implémentation `jobs_impl.purge_runs` ; test `test_cron1_registre.py::test_purge_runs_gele_garde_servi_plus_deux`.
  **GELÉ par défaut** (`gel=…`) : geste destructeur — au registre (connu, monitoré, lançable à la main,
  crontab **commenté**), **à dégeler quand Vic valide l'automatisation**. (Historiquement cette rétention
  vivait à la bascule, `labuse purge-runs-morts`, « jamais un cron ».)
- **(11) Alarme disque Mac < 5 Go** : `deploy/mac/alerte_disque_mac.sh` + agent launchd
  `com.labuse.alerte-disque.plist` (toutes les 30 min, notif macOS, 1 alerte/jour, journal
  `~/.labuse/alerte_disque.log`), câblé dans `install_agents.sh` (5ᵉ agent). Testé : branche « bas »
  (notif) et « rétabli » OK.
- **(12) Retrait des worktrees mergés** : `scripts/ops/retrait_worktrees_merges.sh` — retire une worktree
  **seulement si** sa branche est mergée dans `main` **ET** l'arbre est propre ; **REFUSE** (et liste les
  fichiers) s'il reste des **non-suivis** (livrables). DRY-RUN par défaut (`--apply` pour agir), jamais la
  worktree principale/courante/sur `main`. Validé en **dry-run** sur le dépôt réel : garde `labuse`/
  `labuse-main`/`labuse-menage`, **retirable** `labuse-radarfix2` (mergée+propre), 0 refusé.
  *(Le jeu de worktrees a changé depuis l'audit A1.3 — liste réelle ci-dessus.)*

## Tests

`tests/test_cron1_registre.py` **9/9** (dont la garde du nouveau job), crontab généré **couvre** `purge-runs`
(gelé = ligne commentée), `test_usine_endpoint` (gelés 5→**6**) et `test_dashboardfix1_horloges`
(`HORLOGES.csv` ← `purge-runs`) **verts**. Import de `labuse.jobs`/`jobs_impl` OK (assertion registre↔usine
tenue). *(Les échecs `test_circuit_provenance` + 20 SKIP = base `labuse_test`/rôle `labuse` absents de cet
environnement local — pré-existants, sans rapport avec ces gestes.)*

## Reste (hors périmètre, non fait — rappel)

VACUUM FULL `dryrun_cascade_results` PROD = **programmé 01:30** (ci-dessus). Réécriture d'historique git
(Option A, ~4 Go) **non faite** (Option B seule demandée). Worktrees : **non retirés** (script livré, Vic
décide). Tables PROD gardées (lecteur de code) listées ci-dessus.

*Fin PHASE B — gestes exactement ceux validés, rien d'autre. Branche `fix/menage-1` poussée, pas de merge.*
