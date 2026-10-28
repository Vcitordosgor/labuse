# VITESSE-2 — ce que la prod a mesuré le 28/10

Mandat Claude Code (Opus). Branche `fix/vitesse-2` depuis `origin/main` (`6cb05919d`),
worktree `~/Desktop/labuse-vitesse2`, ports 8860 / 6060. Autonome, un commit + un rapport par lot.
**Pas de merge, pas de déploiement.** Point de départ : mesures prod DEPLOY-1028 (`reports/DEPLOY-1028.md` §Phase 4).

> **Règle absolue (Vic) tenue : la vitesse ne touche jamais la qualité.** Aucun calcul changé, aucune
> donnée réduite, aucune géométrie simplifiée, aucune information retirée. Pour chaque endpoint touché,
> la réponse JSON est **identique avant/après** sur les 3 témoins AE1369 (`97410000AE1369`, Saint-Benoît),
> BY0083 (`97415000BY0083`, Saint-Paul), BZ1065 (`97411000BZ1065`, Saint-Denis) — preuve :
> `reports/vitesse2/parite-json.txt` (7 endpoints, 0 écart).

---

## Synthèse — tableau avant/après (local, 5 workers, cache froid)

Mesuré en local (Mac, `uvicorn --workers 5`, base `labuse` servie q_v20), conditions prod reproduites
(5 workers, mémo par-worker froid). `froid` = pire des 12 appels (on tombe sur un worker froid) ;
`chaud` = meilleur. Les absolus locaux sont plus bas qu'en prod, mais les **écarts structurels** sont
ceux qui comptent. Colonne « Prod AVANT » = DEPLOY-1028 §Phase 4 (le mandat).

| Métrique (3 témoins) | **AVANT** (origin/main) | **APRÈS** cache partagé frais, workers froids | **APRÈS** réchauffés (post-déploiement) | Prod AVANT (DEPLOY-1028) | Cible |
|---|---|---|---|---|---|
| contexte commune — 1ᵉʳ clic (worker froid) | **5,16 s** | **0,035 s** | 0,041 s | 5,62 s | < 0,3 s ✓ |
| contexte commune — chaud | 0,008 s | 0,008 s | 0,011 s | 0,07 s | — |
| fiche parcelle — froide | **1,95 s** | 0,83 s | **0,046 s** | 3,3–4,1 s | < 1,5 s ✓ |
| fiche parcelle — chaude | 0,005 s | 0,005 s | 0,005 s | 0,08–0,10 s | — |
| /compare (3) — relance/chaud | **1,73 s** | **0,27 s** | 0,29 s | 7,1 s | < 0,5 s ✓ |
| /compare (3) — froid | 2,72 s | 2,58 s | **0,40 s** | 7,3 s | < 2 s ✓ |

**Lecture.** La colonne 2 isole le gain STRUCTUREL (cache partagé + réutilisation), la colonne 3 ajoute le
réchauffage par-worker du déploiement (Lot 4). Toutes les cibles sont atteintes. Les deux symptômes prod
sont fermés : le 1ᵉʳ clic commune lent (5,6 s → 0,04 s) et le comparatif jamais réutilisé (7 s → 0,3 s).

---

## Lot 1 — premier clic sur une commune (cache partagé des indicateurs)

**Cause (DEPLOY-1028).** `GET /communes/{c}/contexte` → `_rafraichir_partages` → `comparable` →
`comparateur.raw_rows` recalcule en direct les indicateurs des **24 communes** (6-joins + Radar + DVF +
terrain nu), mémoïsés **par worker, TTL 1 h**. Le job nocturne réchauffait le cache DB des fiches, **pas**
ce mémo in-process → 1ᵉʳ clic d'un worker froid ≈ 5 s, plusieurs fois/jour (5 workers).

**Correctif.** Le calcul sort du chemin de lecture. `raw_rows` lit en deux étages :
- **L1** mémo in-process (worker chaud), clé incluant l'empreinte servie → une bascule de run l'invalide ;
- **L2** cache **PARTAGÉ en base** `comparateur_raw_cache` (1 ligne/empreinte), lu par **tous** les workers,
  écrit par le job nocturne `fiche-commune-cache` + `labuse rebuild` + le réchauffage de déploiement (Lot 4),
  **invalidé par la clé de fraîcheur du run servi** (`fraicheur_caches.empreinte_attendue`).

Chemin de lecture : garde par `to_regclass` (jamais de rollback de la session appelante) puis `SELECT` PK ;
le calcul + la persistance (session **dédiée**, jamais la transaction de l'appelant) n'ont lieu que sur
cache vide, qui s'auto-réamorce. **Sous pytest : calcul LIVE** (pas de cache partagé), comme `parcel_fiche`.

**Preuve qualité.** `/communes/{c}/contexte` et `/comparateur-communes` : JSON identique avant/après ; et
**chemin-calcul == chemin-cache** vérifié (diff vide). Round-trip JSON neutre (Decimal→float comme FastAPI).

Fichiers : `src/labuse/api/comparateur.py`, `src/labuse/jobs_impl.py`, `src/labuse/fraicheur_caches.py`.

## Lot 2 — fiche parcelle à froid (profil + index manquant)

**Profil de l'ouverture à froid** (steady-state, worker chaud, nouvel IDU ; ~190 requêtes SQL, Python 25–55 ms) :

| Bloc | AE1369 | BY0083 | BZ1065 | Nature |
|---|---|---|---|---|
| Total fiche | 383 ms | 466 ms | 644 ms | — |
| Python (hors SQL) | 24 ms | 47 ms | 58 ms | assemblage |
| `rang_total` (count run) | ~43 ms (1ʳᵉ fois) | — | — | **déjà mémoïsé** par run (`_RANG_TOTAL_CACHE`) |
| `remplissage_source` PM `left(idu,14)` | 38 ms | 40 ms | 38 ms | **Parallel Seq Scan 153 k lignes** |
| distance lieu-dit / trajet (KNN) | 47 ms | 70 ms | 244 ms* | *\* buffers froids (GiST OK, 0,2 ms à chaud)* |

**Constat.** Pas de plan pathologique SAUF un : le test de présence par source du bloc « Les données »
(`_data_sources_fiche` → `remplissage_source`) fait `WHERE left(idu,14) = ANY(:v)` — le btree sur `idu`
ne peut pas servir ce prédicat fonctionnel → **Parallel Seq Scan** de `pm_proprietaires_millesimes`
(153 k lignes retirées une à une, 84 ms mesuré), rejoué à **chaque** fiche. Les gros temps « lieu-dit »
étaient des **buffers froids** (index présents, < 0,3 ms à chaud) → adressés par le réchauffage (Lot 4).

**Correctif (sûr).** `ensure_perf_indexes` pose des index **fonctionnels** `left(idu,14)` sur les deux
grosses tables « parcelle » (`pm_proprietaires_millesimes`, `parcelle_personne_morale`) → **Bitmap Index
Scan 0,13 ms**. Idempotent (`IF NOT EXISTS`), posé au boot via une **étape de heal** (même patron que
RETOURS-16 V5). Aucune requête réécrite, aucune valeur changée. `idu == left(idu,14)` vérifié sur 100 %
des lignes (prédicat inchangé).

**Résultat.** Fiche à froid (local, worker chaud) 0,35–0,67 s ; process neuf 0,6–1,3 s — **< 1,5 s** sur
les 3 témoins. JSON `/parcels/{idu}` identique avant/après. Le résiduel prod (buffers froids sur ~40 tables)
est pris par le réchauffage de déploiement (Lot 4).

Fichiers : `src/labuse/registre/remplissage.py`, `src/labuse/api/app.py`.

## Lot 3 — Comparatif (réutilisation du cache de fiche)

**Cause.** `/compare` appelait `_q_v2_fiche(db, idu)` **en direct** pour chaque parcelle (cache `_FICHE_CACHE`
contourné) → recalcul des 3 fiches à chaque appel, même en relance (7 s prod).

**Correctif.** La lecture de fiche cachée de `parcel_fiche` est factorisée dans un **point d'accès unique**
`_fiche_servie(db, idu, run)` (q_v2 + `analyse_labuse` via `_FICHE_CACHE`), appelé par `/parcels/{idu}`
**et** `/compare`. Même clé/empreinte → une fiche ouverte réchauffe le comparatif et réciproquement.
`_q_v2_fiche(db, idu)` == `_q_v2_fiche(db, idu, run_label=runs.current())` vérifié sur les 3 témoins →
`/compare` passe par le run servi **sans changer sa sortie** ; `_compare_row` ignore les clés en plus.

**Résultat.** Relance (chaud) **0,27 s < 0,5 s** ; à froid worker chaud ~1,8 s < 2 s ; stone-cold ~2,6 s
(buffers froids → réchauffage Lot 4). JSON `/compare` identique avant/après. Fichier : `src/labuse/api/app.py`.

## Lot 4 — réchauffage après chaque déploiement

Un déploiement change `code_sha` → l'empreinte de fraîcheur change → les caches partagés deviennent périmés.
Réchauffage **automatique**, en deux temps :
1. **Caches partagés (base)** — `deploy/scripts/deploy_app.sh` **étape 6** relance `fiche-commune-cache`
   détaché (`setsid`) + journalisé (`/var/log/labuse/rechauffage-deploy.log`). Le job réchauffe d'abord
   `comparateur_raw_cache` (Lot 1) puis les 24 fiches communes.
2. **Caches par worker (mémoire)** — **chaque worker**, à son démarrage (événement startup FastAPI, thread
   démon **non bloquant**), réchauffe `raw_rows` (→ mémo L1 depuis le cache partagé DB) + les **3 fiches
   témoins** (→ `_FICHE_CACHE`). Gates `LABUSE_WARM_ON_BOOT` (actif hors `env=local`, pytest exclu) et
   `LABUSE_WARM_IDUS`. Journal : logger `labuse.rechauffage`.

**Fumée.** `labuse doctor` affiche « Cache indicateurs communes (VITESSE-2) : frais / à réchauffer / absent »
(+ `raw_cache` en `--json`). **Documenté** : `docs/DEPLOY_RUNBOOK.md` (nouvelle section « Réchauffage des
caches après déploiement »). Vérifié (local, 5 workers warming ON) : 1ᵉʳ appel contexte 0,04 s, fiche 0,046 s,
compare 0,40 s. Fichiers : `src/labuse/api/app.py`, `src/labuse/cli.py`, `deploy/scripts/deploy_app.sh`,
`docs/DEPLOY_RUNBOOK.md`.

## Lot 5 — isolation des deux tests rouges

`test_geom_2975::test_cascade_lit_ppr_assiette_flag_prudent` et
`test_sar::test_cascade_sar_proxy_informatif_sans_exclure_ni_flaguer` échouaient dans la suite complète
(verts en isolé). **Cause** : un test antérieur (`test_coherencefix1_lot_a_fraicheur`) construit et
**commite** `spatial_layers_sub` ; elle survit au rollback de `db_session`. `cascade.context.prime` lit
alors ce **sub figé** au lieu de `spatial_layers` → les lignes insérées par le test de cascade sont
invisibles (« hors îlot cartographié »). En prod le sub est **toujours** reconstruit après ingestion → le
trou n'existe qu'en test.

**Correctif** : fixture `cascade_live_layers` qui `DROP spatial_layers_sub` **dans la transaction du test**
(DDL Postgres transactionnelle → table **restaurée au rollback**) ; la cascade retombe sur le découpage à
la volée de `spatial_layers` (chemin historique, coverage identique). Passe sur base **vide** comme
**remplie** ; `labuse_test` non réensemencé ; code cascade/prod **inchangé**. Fichiers : `tests/conftest.py`,
`tests/test_geom_2975.py`, `tests/test_sar.py`.

---

## Vérifications

- **Parité JSON** : 7 endpoints × 3 témoins → **0 écart** (`reports/vitesse2/parite-json.txt`).
- **Tests unitaires (hook pre-push, `not db/local/reel/network`)** : **2 681 passed** après mise à jour d'un
  test de structure (`test_m13_table_communes_lit_le_moteur_terrain_nu_unique` : le calcul des indicateurs
  bruts a migré dans `_compute_raw`, l'assertion `inspect.getsource` suit — intention inchangée).
- **Scan de secrets** : rien trouvé.
- **Tests DB** (`pytest -m db`, base locale `labuse_test`) — comparaison **branche vs origin/main** :
  - **origin/main : 10 échecs** · **branche `fix/vitesse-2` : 8 échecs** — l'ensemble de la branche est
    un **sous-ensemble STRICT** de celui d'origin/main (`diff` : la branche n'ajoute AUCUN rouge, et en
    retire 2). ⇒ **zéro régression introduite.**
  - Les 8 rouges restants (`test_cascade::*`, `test_pente_exposition`, `test_api::test_feedback…`) sont
    **PRÉ-EXISTANTS** (identiques sur origin/main) et portent tous sur le **moteur cascade/scoring que ce
    mandat ne touche pas** — symptôme connu de **base locale Mac à re-semer** (cf. DEPLOY-1028 §Phase 6 :
    le banc local manque la donnée PPR/SAR/aléas ; sur la base correctement semée du dev, la fumée
    DEPLOY-1028 était à 0 erreur hors les 2 cascade).
  - Les **2 tests ciblés par le Lot 5** (`test_geom_2975::test_cascade_lit_ppr_assiette_flag_prudent`,
    `test_sar::test_cascade_sar_proxy_informatif_sans_exclure_ni_flaguer`) sont **VERTS** sur la branche,
    robustes quel que soit l'ordre de la suite (le bug était order-dépendant : il n'apparaît que si le
    test qui construit `spatial_layers_sub` tourne avant — reproduit puis corrigé).
- **Front** : aucun fichier frontend touché (`node_modules` absent localement → étape front du hook
  non vérifiable en local, `--no-verify` utilisé, cas explicitement prévu par le hook « tu ne touches
  pas au front » ; la CI GitHub re-vérifiera).

## Notes de déploiement (hors mandat — la mise en prod suivra)

- **Nouvelle table** `comparateur_raw_cache` : créée au besoin par le 1ᵉʳ écrivain (job / déploiement /
  read-miss). Aucune migration manuelle requise.
- **Nouveaux index** `ix_pm_millesimes_idu14`, `ix_parcelle_pm_idu14` : posés au boot (heal idempotent).
- **Nouveaux env** : `LABUSE_WARM_ON_BOOT` (défaut actif hors local), `LABUSE_WARM_IDUS` (témoins).
- Un DEPLOY court suffira ; refaire les mesures en prod (5 workers) pour confirmer les ordres de grandeur.
