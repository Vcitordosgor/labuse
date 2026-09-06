# COMPTE-RENDU CIRCUIT-5 — Les verrous

Branche `feat/circuit-5`, créée depuis `origin/main` à jour (`48fd98d7` = merge CIRCUIT-4).
Reprise : « continue CIRCUIT-5 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md ».

## État d'avancement

- [x] Étape 0 — branche, baseline, lecture des comptes-rendus
- [ ] Lot 1 — verrou des tables
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

## Preuves des verrous (cassé → vert)

(complété lot par lot)

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
