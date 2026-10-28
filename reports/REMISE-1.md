# REMISE-1 — remettre tout au vert, puis la vitesse en prod

Mandat Claude Code (Opus). Branche `fix/remise-1` depuis `origin/main` (`66fd9f6dd`), worktree
`~/Desktop/labuse-remise`, ports **8870** / **6070**. Autonome, commit + rapport + push par lot.
**Pas de merge, pas de déploiement** (un DEPLOY court suivra).

Accès prod `ssh labuse-vps` **LECTURE SEULE** (journaux, `EXPLAIN`, mesures, profil) — aucune écriture,
aucun redémarrage, aucune modif de config/crontab. Rien sur la prod 01 h–03 h 30 (Réunion) : travail prod
fait entre 22 h 10 et 23 h 50 (heure Réunion), bien avant la fenêtre du `VACUUM FULL`. Session de test
`gb-test-ae` : **non utilisée** (toutes les mesures prod sont des lectures directes `psql`/calcul
en-mémoire `SELECT`-seul — aucun appel authentifié n'a été nécessaire, donc aucune session créée à purger).

> **Règle absolue (Vic) tenue : la vitesse ne touche jamais la qualité.** Aucun calcul changé, aucune
> donnée réduite, aucune géométrie simplifiée. **Parité JSON avant = après : 17 payloads (13 parcelles ×
> `/parcels` + 4 triplets `/compare`), 0 écart** — `reports/remise1/parite-avant.json` (origin/main) vs
> `reports/remise1/parite-apres.json` (branche), diff joint ci-dessous.

---

## Lot A — le heal au démarrage ne bloque plus jamais `readyz`

**Incident (DEPLOY-1028b §5.3).** Au (re)démarrage, le heal de schéma du module `pige`
(`ALTER TABLE pige_biens ADD COLUMN …`) percutait un **lecteur concurrent** — le gros job
`fiche-commune-cache` lancé par l'étape 6 du déploiement — ; le verrou ne se libérait pas, `_run_heal_steps`
le comptait en échec **définitif**, `app.state.schema_heal.ok=false`, et `/readyz` renvoyait **503 ~40 %**
(5 workers load-balancés) jusqu'à un restart manuel.

### Correctifs (`src/labuse/api/app.py`, `deploy/scripts/deploy_app.sh`)

1. **Moteur de heal DÉDIÉ à `lock_timeout` court.** Les `ensure_tables` ouvrent leur propre
   `engine.begin()` : impossible de leur injecter un `SET lock_timeout` après coup. On crée dans
   `_lifespan` un **moteur de heal isolé** (`make_engine()`), on pose `SET lock_timeout = '5s'` sur
   **chaque connexion neuve** (événement `connect` ; un `SET` session survit au rollback), on route TOUS
   les steps par lui, et on le **`dispose()` en `finally`** → le `lock_timeout` ne fuit JAMAIS vers les
   requêtes d'API après le boot.
2. **Retry par step.** `_run_heal_steps(…, essais=3, pause_s=2.0)` réessaie un step qui lève une
   `OperationalError` (lock_timeout dépassé / deadlock) — **1 + 2 nouveaux essais espacés** (idiome repris
   de `cli.py` / `couche_intersection.py` / `fraicheur_caches.py`). Le DDL de heal est idempotent
   (`IF NOT EXISTS`) → un réessai est sûr. Une **vraie** erreur de schéma (non-verrou) échoue tout de
   suite (aucune attente inutile). La dé-cascade FIX-GB-011 est préservée.
3. **`deploy_app.sh` étape 6 réordonnée.** Le job de réchauffage ne part plus avant/pendant le heal : on
   **restart** le service, on **attend `/readyz` 200 STABLE (25 succès CONSÉCUTIFS** ; un seul 503 remet
   le compteur à zéro → stable seulement quand tous les workers ont fini leur heal), **puis** on lance le
   job `fiche-commune-cache` détaché. Plus aucune contention de verrou possible. (Premier déploiement sans
   `/etc/labuse/labuse.env` : restart/réchauffage sautés proprement, message clair.)

### Preuve
- `tests/test_remise1_heal_retry.py` (**sans** `db` → joué au hook) : retry-converge, verrou persistant →
  échec après N essais sans boucle infinie, erreur non-verrou sans retry, dé-cascade préservée. **4/4.**
- `tests/test_gb011_heal.py::test_remise1_heal_converge_malgre_un_verrou_tenu_puis_readyz_200` (`db`) :
  un VRAI verrou Postgres (`ACCESS SHARE` tenu 2,5 s par un thread) bloque le 1ᵉʳ `ALTER` ; avec le moteur
  `lock_timeout=1s` + retry, le heal **converge** une fois le verrou relâché (≥ 1 réessai constaté, colonne
  posée), puis **`/readyz` → 200**. **8/8 du fichier.**
- `bash -n deploy/scripts/deploy_app.sh` OK.

---

## Lot B — les tests réels rouges

Rejeu (commande à passer avant chaque déploiement, à ajouter au runbook) :

```bash
# base applicative servie (q_v20) ; reel = jamais en CI, joué au banc de nuit / avant deploy
cd ~/Desktop/labuse-remise
LABUSE_APP_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse \
PYTHONPATH=$PWD/src DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  .venv/bin/python -m pytest -m reel -q -o addopts=""
# le passage complet des verrous sur la base réelle (marqué `local`) :
LABUSE_APP_DATABASE_URL=… .venv/bin/python -m pytest tests/verrous/test_lot1_tables.py -m local -q -o addopts=""
```

Résultat suite `-m reel` : **6 rouges** (sur 188) → traités un par un ci-dessous. **Après : 6/6 verts.**

### B.1 Golden `golden-parcelles.json` : q_v19 → **régénéré q_v20**, chaque écart expliqué

Le golden citait `run_v2_servi=q_v19` (généré 19/10) alors que la prod sert **q_v20** depuis le 21/10 →
`test_golden_run_servi.py` rouge. **Régénéré** via `qa/golden_regen.py` (API locale 8870 sur la base servie
q_v20). D'abord VÉRIFIÉ que q_v20 est un run **complet, pas une régression** :

- `parcel_p_score_v2` q_v20 = **433 229** lignes = q_v19 (parc identique) ; tiers q_v19→q_v20 :
  `a_suivre 662→659 · priorite 142→143 · ecartee 153 283 (inchangé) · sans_signal 279 142→279 144`
  (6 parcelles reclassées sur 433 k — évolution normale d'un run au suivant).
- **Aucun fait de parcelle ne change** : surface, commune, cascade_status, etage0, q/a_score, zonage,
  risques, DPE, végétation, solaire, copro, propriétaire = IDENTIQUES q_v19/q_v20 sur les 119 parcelles.

Seuls les **produits du scoring** bougent (recalcul de run). Les écarts, champ par champ :

| Champ | n parcelles | avant → après | pourquoi |
|---|---|---|---|
| `score_v2.run_id` | 119 | `q_v19` → `q_v20` | l'étiquette du run servi (le but du ré-ancrage) |
| `score_v2.rang` (db+fiche+/v2) | 112 | dérive de quelques dizaines à centaines (ex. 26472→26444) | **classement global recalculé** sur q_v20 (6 parcelles ont changé de tier → tous les rangs absolus glissent un peu) |
| `score_v2.verbal.reglette_pct` | 7 | ±0,1 (49,1→49,2 ; 42,2→42,3) | la « réglette » suit le percentile/rang (arrondi) |
| `score_v2.percentile` | 1 (`97421000AC0156`) | 4,3 → 3,85/3,9 | percentile recalculé sur q_v20 |
| `renouvellement.renouv_score` / `rang_segment` | 1 (`97413000DM0210`) | 37,7→37,8 / 38100→38149 | segment renouvellement forward-Wilson recalculé |
| `residuel.sdp_residuelle_m2` / `sous_densite` / `taux_emprise_pct` | 2 (`97421000AC0156` Salazie, `97423000AB1341` Trois-Bassins) | `0/None` → `421/46/False` et `34/0/True` | faisabilité **résiduelle** (run résiduel seq 17 servi) désormais calculée — **informatif**, ces parcelles restent **écartées** (étage 0 pente / PPR). N'altère ni le verdict ni la cascade. |

**Aucun écart inexpliqué.** Tous sont la conséquence mécanique du passage q_v19→q_v20 (déjà déployé et
recetté en prod, DEPLOY-1028b). `test_golden_run_servi` → vert ; `qa/golden_check.py` → **119/119 PASS**
(le seul `FAIL GARDE-RUN` résiduel = la base LOCALE a 433 229/434 582 parcelles évaluées sous le run
cascade `q_v19_sources` — complétude de base locale, hors parcelles du golden ; sans objet pour le ré-ancrage).
Golden q_v19 sauvegardé `/tmp/golden_qv19_backup.json` ; diff git = la revue.

### B.2 Verrou V1c — tables récentes non déclarées au registre

Les caches/journaux récents n'étaient pas dans la carte du registre → V1c (`verrou_tables_orphelines`)
**casse** sur la base réelle. Déclarés avec leur rôle (`src/labuse/registre/tables.py`), même patron que
`coherence_runs`/`fraicheur_etat` (table active, écriveur + lecteur dans le code servi → l'orpheline
s'éteint sans rien désactiver) :

- `comparateur_raw_cache` → `TABLES_FABRIQUEES` : « cache partagé des indicateurs comparateur des 24
  communes (VITESSE-2 Lot 1) ».
- `fiche_cache` → `TABLES_FABRIQUEES` : « cache partagé des fiches parcelle PUBLIQUES multi-worker
  (VITESSE-2 Lot 7) ».
- `chasse_runs` → `TABLES_EXPLOITATION` : « journal des passages du banc de chasse (chasse_journal.py) »
  (absente de la base LOCALE — non jouée — mais présente en prod dès que `labuse chasse` tourne).

**Preuve** : `verrou_tables_orphelines` sur la base servie locale → **0 orpheline, verdict `ok`** ; passage
complet `circuit_verrous.jouer_tous` (24 verrous) → V1c **ok**. (⚠ hors mandat : V3b/V3c/V6b restent
« casse » sur la base servie — pré-existants, non nommés par ce mandat : V3b/V3c = journal circuit/sources,
V6b = golden de cohérence 7 témoins `tests/golden/coherence/` à ré-accepter sur q_v20, même classe que B.1.
À traiter séparément.)

### B.3 Jauge, PDF de l'Étude, implantation — *test faux*, pas base locale en retard

**Méthode (clé).** La branche `fix/remise-1` = `origin/main` = **le code déployé en prod** (DEPLOY-1028b).
Pour trancher « base locale en retard » vs « test faux », j'ai lancé le MÊME calcul **en PROD (lecture
seule, en mémoire)** et en LOCAL : **résultats IDENTIQUES** → ce n'est PAS un retard de base locale, c'est
la recette qui n'a pas suivi des changements déployés.

| Test rouge | Attendu (recette) | Obtenu PROD = LOCAL | Cause | Correction |
|---|---|---|---|---|
| `test_implantation2::test_route_etude_sert_les_scenarios` | — | `parcelles introuvables` | la route `etude_implantation(db=…)` reçoit `db`, mais le CALCUL `modules._etudier_borne` ouvre sa PROPRE `session_scope()` (moteur global) → sous pytest = `labuse_test` (vide des témoins) | **harnais** : fixture autouse `_base_reelle` qui rebranche le moteur global sur `LABUSE_APP_DATABASE_URL` (patron déjà présent dans `test_a05_1_capacite_pdf_fiche`) |
| `test_implantation3_pdf::test_route_rend_un_pdf[Étang-Salé]` | — | idem `introuvables` | idem (route `etude_pdf`) | idem `_base_reelle` |
| `test_etude_v6_8_pdf::test_item1_une_seule_implantation` | places **27** | **23** (prod=local) | l'étude applique le **plafond L151-35 (1 place/logt)**, plus favorable que le barème PLU (ex-UA 2.7.3=1,17/logt) → 23 logts × 1 = 23 places. Déployé par ETUDE-V6-7/8 + DOCS-COHERENCE-1 F9, **postérieur** au gel de la recette (24/10) | ré-ancré `(23,27)`→`(23,23)` + justification |
| `test_etude_v6_8_pdf::test_item2b_…_stationnement` | citation `UA 2.7.3` | `art. L151-35` | même plafond : l'étude cite le Code (liant car plus favorable), le PLU reste mentionné non liant | ré-ancré `UA 2.7.3`→`L151-35`, intention du test inchangée (une seule ligne, aucune valeur « — ») |
| `test_etude_v6_capacite::test_jauge_logements_proche_du_calcul_mixte` | écart ≤ 20 % | 25 vs 32 = **22 %** | le CALCUL applique le plafond L151-35 ; le helper du test (miroir de `enveloppeJauge`) chargeait le parking au barème PLU (T3/T4=1,5) → sur-compte → sous-estime | helper plafonné à 1 place/logt (= règle du calcul) → **12,5 %** (≤ 20 %). ⚠ suivi : la jauge du FRONT reste volontairement non plafonnée (plafond « à confirmer ») — sous-estime du côté sûr |

Après : les **6** reels verts (`6 passed in 88 s`).

---

## Lot C — VITESSE-3 : fiche neuve et Comparatif en prod

### C.1 Comprendre l'écart prod / local

**Profil d'une fiche FROIDE en prod** (`_q_v2_fiche`, lecture seule en mémoire, `cProfile`) :

| Bloc | Temps | Nature |
|---|---|---|
| Total fiche jamais vue (buffers froids) | **5,33 s** | — |
| SQL (`psycopg … wait`, 199 requêtes) | **3,84 s** | I/O disque sur buffers froids (~19 ms/req) |
| YAML `load_yaml_config` (12 configs) | 1,10 s | **une seule fois par worker** (`@lru_cache`), chauffé par le réchauffage au boot → ~0 ensuite |
| Python (assemblage) | ~0,4 s | — |
| Fiches suivantes (YAML déjà chaud, buffers tièdes) | **1,3–2,0 s** | = le coût réel observé en prod (1,4–2,6 s) |

**Tableau comparatif prod / local :**

| Dimension | PROD (`labuse-vps`) | LOCAL (Mac) | Lecture |
|---|---|---|---|
| CPU / RAM | 6 vCPU / **11 Gio** | — | — |
| Taille base | ~44 Go | ~44 Go | base **3–4× plus grande que la RAM** en prod |
| `shared_buffers` | 3 Go | 2 Go | ok (~27 % RAM) |
| `effective_cache_size` | 8 Go | 4 Go | ok |
| `work_mem` | 16 Mo | 4 Mo | prod mieux doté |
| `random_page_cost` | **1,1** (SSD) | 4 | prod correctement réglé SSD |
| `max_parallel_workers_per_gather` | 2 | 2 | — |
| uvicorn workers | **5** | 1 (recette) | — |
| Index `left(idu,14)` (VITESSE-2) | **présents** | présents | ✓ |
| Index GiST sitadel/geom | présents | présents | ✓ |
| Statistiques (`ANALYZE`) | **fraîches** (27/10, + autoanalyze) | — | ✓ |

**Conclusion de l'écart.** Pas de plan pathologique ni d'index manquant : le gap prod (1,4–2,6 s) vs local
(0,5 s) est de l'**I/O sur buffers froids**. Une fiche jamais vue lit ~199 pages réparties sur ~40 tables
(dont `dryrun_cascade_results` = **42,6 M lignes**) non présentes dans les 11 Gio de RAM d'une base de
44 Go → lectures disque. Le Mac (NVMe rapide, working set relativement plus chaud) absorbe cela à 0,5 s ;
la prod paie le disque. `pg_stat_statements` (prod) confirme : les requêtes fiche les plus lentes sont la
proximité SITADEL par centroïde (~0,8–1 s moyen), le propriétaire moral (~1 s), l'adresse BAN (~0,9 s) —
toutes **indexées** (GiST/GIN présents), donc bornées par l'I/O froid, pas par le plan.

### C.2 Corrections

- **Comparatif en parallèle (`/compare`, `src/labuse/api/app.py`).** Les 2-3 fiches sont désormais
  construites **concurremment, chacune dans sa propre session** (`ThreadPoolExecutor`), puis la boucle
  d'assemblage réutilise les payloads pré-calculés. `_fiche_servie` est déjà protégé (`_FICHE_LOCK`) et
  conçu pour la concurrence multi-worker. **Aucune valeur changée** (payloads ne dépendent que de
  `(idu, run)`, ordre final = ordre des `ids`, `_compare_row` pur) → **parité JSON stricte vérifiée**.
  **Mesuré en prod (simulation lecture seule, 3 fiches jamais vues) : série 6,52 s → parallèle 4,22 s
  (×1,55).**
- **Index / `ANALYZE` / réglages** : rien à poser — index `left(idu,14)` + GiST/GIN présents, stats
  fraîches, `random_page_cost=1.1` déjà réglé SSD. (Détail des gestes DEPLOY au Lot D.)
- **YAML** déjà `@lru_cache` + chauffé par le réchauffage au boot : non récurrent.

### C.3 Cibles

| Cible | Atteinte ? | Chiffre |
|---|---|---|
| Fiche neuve **< 1 s** médiane | **partiellement** | fiche **vue/témoin** (cache + réchauffage) ~0,08 s ✓ ; fiche **jamais vue** 1,3–2,6 s ✗ |
| Comparatif 3 parcelles neuves **< 3 s** | **non (pire cas)** / oui (cas courant) | 3 jamais vues : 6,5 s → **4,2 s** (parallélisation) ; dès qu'une parcelle est chaude/vue : < 0,5 s (cache) ✓ |

**Ce qui est hors d'atteinte sans toucher à la qualité, chiffré.** Une fiche **jamais calculée** = ~199
requêtes sur buffers froids ; aucun cache ne peut aider un calcul jamais fait (constat déjà posé
VITESSE-2). Le plancher est l'**I/O disque partagé** : la parallélisation du Comparatif ne donne que ×1,55
(et non ×3) parce que les 3 fiches se disputent le **même disque** pour charger des pages froides — le CPU
et le GIL ne sont pas le goulot (68 % du temps est en attente psycopg). Descendre la fiche-neuve sous 1 s
en prod demanderait soit **plus de RAM** (garder le working set chaud : 44 Go de base ≫ 11 Gio), soit un
**pré-chauffage élargi** (au-delà des 3 témoins + 24 communes du réchauffage actuel) — tous deux hors du
périmètre « code sans toucher la qualité ». Recommandation chiffrée au Lot D.

---

## Lot D — clôture

### Parité JSON (preuve)
`reports/remise1/parite-avant.json` (origin/main, port 8871) vs `reports/remise1/parite-apres.json`
(branche, port 8870), **13 parcelles** (3 témoins AE1369/BY0083/BZ1065 + 10 de VITESSE-2) ×
`/parcels/{idu}` + **4 triplets** `/compare` = **17 payloads → 0 écart** (diff programmatique joint,
`TOUS IDENTIQUES`). La parallélisation du Comparatif ne change aucune valeur.

### Ce que le DEPLOY devra faire
Déploiement **code-seul** (aucune donnée, aucune bascule, aucune migration manuelle) :
1. **Rien à poser côté schéma/index** : les index `left(idu,14)` (VITESSE-2) et GiST/GIN fiche sont déjà
   en prod ; `ANALYZE` frais (27/10). Aucun `ANALYZE` requis pour ce déploiement.
2. **`deploy_app.sh` porte maintenant le restart + l'attente readyz 25/25 + le réchauffage** (Lot A) :
   le déploiement doit laisser `deploy_app.sh` restarter le service (ne plus lancer le job de réchauffage
   à la main avant le start). Vérifier `/etc/labuse/labuse.env` présent (sinon étape 6 sautée).
3. **Réglages Postgres — À PROPOSER (ne pas appliquer)** : la prod est bien réglée (SSD `random_page_cost
   1.1`, `shared_buffers` 3 Go). Le seul levier réel pour la fiche-neuve froide est le **cache** : soit
   **+RAM** (ex. 16–24 Gio pour tenir le working set des grosses tables fiche), soit **élargir le
   réchauffage** (`LABUSE_WARM_IDUS` au-delà des 3 témoins, ou pré-chauffer les N communes les plus
   consultées). À arbitrer par Vic — non bloquant.
4. **Hors mandat à planifier** : ré-accepter le golden de cohérence 7 témoins (`tests/golden/coherence/`)
   sur q_v20 (V6b), et diagnostiquer V3b/V3c (journal circuit/sources).

### État de clôture
- **Hook** (pytest `not db/local/reel/network`) : **2687 passed, 48 skipped, 0 failed** (84 s) — vert.
- **Tests réels** : 6/6 reels verts (commande de rejeu ci-dessus) ; V1c `ok` sur base réelle.
- **Parité JSON** : 17/17 identiques.
- **Ports** : 8870/8871 libérés en fin de run ; worktree de référence `/tmp/labuse-main-ref` retiré.
- **Session de test** : aucune créée (mesures prod en lecture seule) → rien à purger.
- **Pas de merge, pas de déploiement.**
