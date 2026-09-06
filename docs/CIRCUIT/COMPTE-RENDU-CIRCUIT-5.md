# COMPTE-RENDU CIRCUIT-5 — Les verrous

Branche `feat/circuit-5`, créée depuis `origin/main` à jour (`48fd98d7` = merge CIRCUIT-4).
Reprise : « continue CIRCUIT-5 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md ».

## État d'avancement

- [x] Étape 0 — branche, baseline, lecture des comptes-rendus
- [x] Lot 1 — verrou des tables
- [ ] Lot 2 — verrou des sources (68 = 68)
- [ ] Lot 3 — verrou des versions
- [ ] Lot 4 — verrou des communes
- [ ] Lot 5 — verrou des concepts et des moteurs
- [ ] Lot 6 — commande, porte, page, VERROUS.md

## Étape 0 — baseline (06/09/2026)

`main` est occupée par le worktree `~/Desktop/labuse-merge` → branche créée par
`git checkout -b feat/circuit-5 origin/main` (même contenu, l'autre worktree n'est pas touché).

Suites au départ (base locale accumulée, pas d'A/B fraîche) :

- **pytest** : `4 failed, 2615 passed, 50 skipped` en 81 s
  (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` requis, sinon `test_non_contradiction`
  erre à la collecte sur libgobject/WeasyPrint — FZ-002 pré-existant).
  Les 4 échecs sont **pré-existants par construction** (la branche = `origin/main` + le seul
  commit du mandat) :
  - `test_courrier_boucle.py::test_boucle_piste_courrier_reponse` — IntegrityError FK
    `pipeline_entries`→compte (accumulation de `labuse_test`)
  - `test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque` — idem
  - `test_dashboard.py::test_ia_log_attribue_au_compte` — idem
  - `test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel` — AssertionError
- **tsc** : 0 erreur
- **vitest** : 181 passed (43 fichiers)

Règle tenue pendant tout le mandat : zéro échec NOUVEAU par rapport à cette baseline.

## Décisions prises en autonomie

- D0-1 : `main` étant réservée par le worktree `labuse-merge`, la branche part de
  `origin/main` (identique) plutôt que de déplacer le checkout — option la plus sûre.
- D0-2 : baseline notée avec ses 4 échecs d'accumulation de base de test plutôt que de
  recréer `labuse_test` (une recréation aurait changé l'environnement de tout le poste
  en début de mandat) ; le critère devient « zéro échec nouveau ».
- D1-1 : les moteurs lisent aussi des tables FABRIQUÉES (produits de la pompe :
  `parcel_flags`, `score_e`, `p_model_*`…) — la carte les déclare dans une famille propre
  (`TABLES_FABRIQUEES`, avec leur fabricant) plutôt que de les coller à un réservoir
  arbitraire ou de les laisser orphelines. Le verrou couvre l'union (réservoirs ∪
  fabrications ∪ exploitation).
- D1-2 : DOUTE du CSV résolus par le code : `rpg_proxy_ign` → kind `safer` (layers_ingest),
  `inpn_espaces_proteges` → kind `ens`, `deal_wms_wfs` → canal sans table propre (QPV/NPNRU
  portent les tables), `spanc_epci` → manuel sans table.
- D1-3 : `p_model_static_pre_v8`/`parcel_residuel_pre_v8` (lecteur `bascule_gardes.py`)
  restent orphelines « archiver, à débrancher d'abord » — l'option sûre : pas de débranchage
  de garde en autonomie.
- D1-4 : `labuse tables purger --apply` PAS joué (geste de Vic) ; le mode liste seul a été
  vérifié ; V1c retourne `a_decider` (jamais `casse`) tant que chaque orpheline a son
  action — un déploiement ne doit pas être bloqué par des tables que seul Vic peut purger.
- D1-5 : les 9 « réservoirs sans lecteur » et les 4 « à rattacher » ne sont PAS corrigés en
  autonomie (pas de donnée inventée au registre, pas de ligne catalogue créée) — listés
  pour le Résumé « à décider » (lot 6).

## Lot 1 — verrou des tables (livré)

**La carte** : `src/labuse/registre/tables.py` — 80 réservoirs déclarés (tables +
couches `spatial_layers` + millésime ; les hors-vitrine avec leur note), 74 fabrications
de la pompe, 78 tables d'exploitation, 5 relations PostGIS. Les orphelines sont
**calculées** (schéma − carte), jamais énumérées : seules les actions proposées sont
curées (`ACTIONS_PROPOSEES`).

**Les verrous** (`src/labuse/circuit_verrous.py`, joués par `labuse circuit verrous`) :
- **V1a** (statique) : les noms de tables dans les requêtes de `registre/moteurs/` et les
  `Donnee.table` des passe-plats ⊆ carte. Seul un candidat qui EST une relation du schéma
  est une violation (élimine les faux positifs : imports Python, `parcels.surface_m2`,
  tuilages WMTS distants). Sur la base réelle : **ok** (6 modules, 168 données).
- **V1b** (exécution) : `journal_requetes()` (event `before_cursor_execute`) capture les
  tables touchées pendant `sonde_circuit.verifier_robinets` — 10 tables, toutes dans la
  carte. Les suffixes `__attente`/`__precedente` (échange CIRCUIT-3) sont rattachés à leur
  table de base.
- **V1c** : orphelines listées avec action, jamais un DROP — verdict **à décider**
  (32 orphelines, 1,56 Go, `TABLES-ORPHELINES.md`). Une orpheline NOUVELLE sans action
  proposée = verrou **cassé** (trou de curation).
- **V1d** : réservoir sans lecteur au registre = **à décider** — 9 trouvés (dont DPE :
  nulle part dans le registre alors que `dpe_records` nourrit scoring et passoire ;
  MOBPRO : abandonné par ZONE-DONNÉES mais resté en vitrine).

**Preuves cassé → vert** (`tests/verrous/test_lot1_tables.py`, 15 tests, marque `verrous`) :
- V1a : fonction témoin `moteur_temoin.py` lisant `zz_orpheline_temoin` (posée dans le
  schéma injecté) → `casse`, le détail nomme fichier et table ; témoin ne lisant que la
  carte → `ok`.
- V1b : sonde monkeypatchée lisant `zz_orpheline_v1b` (table posée exprès en base de test)
  → `casse` ; sonde fidèle → `ok`.
- V1c : `zz_perdue_expres` dans le schéma sans action → `casse` ; avec action → `a_decider`.
- V1d : réservoir `zz_reservoir_muet` (table que personne ne lit) → listé `a_decider`.
  (Premier essai avec `tables=("parcels",)` : NON détecté car « lu » via la table partagée —
  le test le prouve en creux, un réservoir qui partage une table lue n'est pas muet.)
- `-m local` : `jouer_tous()` sur la base réelle `labuse` → **0 cassé** (2 à décider).

**CLI** : `labuse circuit verrous [--complet] [--sans-journal]` (une ligne par verrou :
phrase, verdict, preuve ; sort en erreur au premier cassé ; journalise geste `controle`,
cible `verrous`) · `labuse tables purger [--apply]` (déplace vers le schéma `poubelle`,
`ALTER TABLE … SET SCHEMA` — jamais un DROP ; `--apply` NON joué : geste de Vic).
PIÈGE connu : `python -m labuse.cli` ne voit pas les commandes tardives (garde `__main__`
en milieu de fichier) → passer par le binaire `labuse` (PYTHONPATH sur le worktree).

**Trouvailles chemin faisant** :
- La vitrine locale compte DÉJÀ **68** réservoirs servis (le merge CIRCUIT-4/RETOURS a
  amené EDF HTA/TCSP) ; 80 lignes en base → 12 hors vitrine pour le lot 2 (3 DOUBLON,
  2 hub, 7 a_faire dont 2 « RETIRÉ »).
- `data_sources` 96 (Cadastre d'époque) et 97 (CatNat GASPAR) manquaient au pont
  `NOM_VERS_SLUG` et à `reservoirs.csv` → slugs `cadastre_epoque`/`catnat_gaspar` créés
  dans la carte (le pont sera complété au lot 2).
- Le registre référençait déjà `annuaire_service_public` (mairies) et `rnic_anah`
  (RNIC) : des slugs SANS ligne `data_sources` — au Résumé « à décider » (avec
  `rpls_commune` et `commune_conso_enaf`, servies sans slug ni ligne).
- `spatial_layers` porte une couche archivée `plu_gpu_zone__archive_m40` (3 lignes) —
  relevée dans TABLES-ORPHELINES.md, pas une table à purger.

## Preuves des verrous (cassé → vert)

Chaque verrou a son couple de preuves DANS les tests (`tests/verrous/`) — rejouables à
chaque suite, pas des sorties d'un soir. Les sections de lot ci-dessus citent le cas
construit et le verdict des deux sens.

## Dettes reprises des comptes-rendus 0→4 et P

Lues dans COMPTE-RENDU-CIRCUIT-1→4 et P (P3 surtout), vérifiées dans le code :

- **La sonde écrit des libellés, pas des ids** (dette CIRCUIT-P3) : `circuit_ecarts.robinet_a/robinet_b`
  et `circuit_eau_ancienne.robinet` portent des chaînes d'affichage (« attrs.degre (DEAL brut) »,
  « fiche parcelle / filtres ») — DDL dans `sonde_circuit.py`. Le rattachement au registre passe
  aujourd'hui par `circuit_etats.robinets_touches()` (join par `chiffre_id`). → lot 3.3.
- **Eau DPE non attribuable** : lignes d'eau ancienne avec `chiffre_id` hors registre
  (« (chiffres DPE) ») → invisibles au niveau robinet. → lot 3.3.
- **Lignes `data_sources` hors vitrine** (CIRCUIT-0 lot 1) : doublons id 2/65/67, retirés 49/50,
  hubs 11/12/14, a_faire 80/89/95 (+ ECLN/LOVAC voulues-absentes). La vitrine = `WHERE_AFFICHEES`
  (`sources_catalog.py:36`) : statuts `connecte|manuel`, préfixes `DOUBLON/RETIRÉ/DORMANT` dans
  `technical_notes`, `affichage_desactive`, `masquees`. → lot 2 (statut de première classe).
- **Tables mortes CIRCUIT-0** : `parcel_residuel_base_legacy`, `parcel_au_statut_pre_m32`,
  `m6_snapshot_*`, `*_pre_v8` — aucun SELECT dans `src/labuse/api/`. → lot 1.3.
- **Nombre de réservoirs** : base locale = **66** servis (68 = production, EDF HTA 93 / TCSP 94 /
  Réunion Express 95 sont sur `fix/retours-12` non mergé). Le verrou « 68 = 68 » est donc une
  **égalité de comptes vivante** (data_sources servies = vitrine = registre = page), jamais un
  68 littéral (interdit « valeur codée en dur »).
- **Matière première du lot 1** : `docs/CIRCUIT/inventaire/reservoirs.csv` porte déjà
  `tables_servies` + `millesime_servi` par réservoir (79 lignes) ; les ids réservoir du registre
  (`Donnee.reservoirs`) sont ceux de ce CSV.
- **Référentiel 24 communes** : `ingestion/run_all.py:REUNION_COMMUNES` (97401→97424),
  exposé `INSEE_24`/`NOMS_24` dans `filtres/cadre.py`.
