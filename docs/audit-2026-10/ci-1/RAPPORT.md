# RAPPORT CI-1 — aucun code cassé n'arrive dans main

Branche `feat/ci-1`, worktree `~/Desktop/labuse-ci`. Rien sur le VPS. Aucune écriture dans la base
applicative `labuse` (deux autres sessions tournaient) : la suite tourne sur une base de test DÉDIÉE
`labuse_test_ci`, isolée du `labuse_test` partagé des autres worktrees.

> État : Lot 1 ✅ · Lot 2 ⏳ · Lot 3 ⏳ · Lot 4 ⏳ · Lot 5 ⏳ (ce rapport se remplit lot par lot).

---

## Étape 0 — état des lieux

- `pwd` = `/Users/openclaw/Desktop/labuse-ci` · branche `feat/ci-1` (depuis main `0a9b927c`) · arbre propre.
- Outils : `.venv` du dépôt principal (Python 3.12.13, pytest 9), Node 22, `npm ci` dans le worktree.

---

## Lot 1 — repartir au vert

### Méthode

La suite « verte documentée » l'était sur un poste dont la base `labuse_test` avait **accumulé** du
schéma et des données au fil des runs — ce qui **masquait** des trous. La CI, elle, part d'une base
PostGIS **vierge**. On a donc joué la suite sur une base fraîche (`labuse_test_ci`) : c'est la vérité
pertinente pour la CI. Résultat initial : **79 échecs** / 3621 passés.

Triage (3 sondes de lecture + vérifications manuelles) → 3 familles :

1. **Trous de schéma conftest** (la base de test ne reconstruisait pas tout ce que le boot de l'app
   crée) → **comblés dans `tests/conftest.py`** : résout **36 échecs** d'un coup.
2. **Tests PÉRIMÉS, produit correct** (assertions figées sur d'anciennes chaînes/chemins/symboles,
   crontab/CSV non suivis, calibrage PLU changé) → **réparés vers la réalité actuelle**.
3. **Tests « données réelles »** (exigent run servi / DVF / PLU / scoring seedés) → **marqués `reel`**,
   exclus de la CI (rejoués au banc de nuit en prod).
4. Cas nécessitant un **arbitrage produit** → `xfail(strict=False)` motivé + **signalés à Vic** ci-dessous.

Arbitrage Vic (13/10) : (1) données réelles → `reel` hors CI ; (2) tests périmés → réparer vers la
réalité actuelle, `xfail` seulement les irréparables.

### 1. Correctif de fond — `tests/conftest.py` aligné sur le boot de l'app

Le boot (`api/app.py::_lifespan`, tuple `_heal_steps`) appelle une séquence de `ensure_tables` que
conftest ne reproduisait pas → sur base vierge, tables/colonnes absentes en cascade
(`crm_columns`, `division_or_candidates`, `share_links`, `mairies`, colonne `parcels.cadastre_disparue_le`…).
conftest reproduit désormais **la même séquence, dans le même ordre** (modules, ia, events, partners,
projets, protection, courrier, comptes+scoping, crm_columns, veilles, copilote_v2, dashboard, pige,
promo, zone) + matérialise les artefacts d'ingestion hors ORM. Tout est idempotent. **+36 tests.**

Aussi : `tests/test_marche_commune.py::_has_data` rendu défensif (requête DB au niveau MODULE, dans un
`skipif`, qui ERRORait à la collecte sur base/colonne absente → skip propre).

### 2. Corrections produit/outillage réelles (gaps que la CI DOIT garder)

| Point | Cause | Correction |
|---|---|---|
| `test_deps_declared` | `freezegun` importé par `scripts/chasse/horloge.py` mais non déclaré | ajout `freezegun>=1.5` à l'extra `[dev]` de `pyproject.toml` |
| `test_proxy_dev_couvre_routes_api` | 3 routes servies non couvertes (`/flash-omnibox.js`, `/ordinateur.js`, `/socle`) | ajoutées à `NON_PROXIFIE` (pages/scripts/assets rendus serveur, jamais `fetch`) avec justification |

### 3. Tests PÉRIMÉS réparés (produit vérifié correct)

Front (grep de source, refactors) — fichiers de test uniquement :

| Test | Cause | Réparation |
|---|---|---|
| `ProspectionSolaire.test.tsx` (H13.3) | libellé source « 2025 » codé en dur → « millésime servi en page Sources » (CHASSE-DONNEES-FIX-1 E-80) | assertion mise à jour |
| `test_front_reliquats::test_r1_lien_voir_fiche` | bouton « Voir l'entièreté » retiré (RECETTE-2 A13b) | garde la SUPPRESSION (assert absence) |
| `test_front_reliquats::test_m135_carte_fraction` | assert brittle `"RR"` matchait « TE**RR**AIN » | assert retiré (3 autres couvrent l'intention) |
| `test_front_reliquats::test_omnibox_parcelinput` | composant `ParcelInput`→`EntreeParcelle` (saisie unifiée RECETTE-1 F2) | marqueurs mis à jour (cascade `o5-idu`, `temps-idu`→`diligence-idu`) |
| `test_front_reliquats::test_calculette_fonciere` | idem `ParcelInput`→`EntreeParcelle` | assertion mise à jour |
| `test_retours11f2::test_lotS_f7_pct_qpv` | `k != "pct_qpv"`→`k not in ("pct_qpv", "millesime")` | chaîne attendue mise à jour |
| `test_retours11f3::test_f11_wording` | chaînes déplacées `_q_v2_fiche`→`_pm_block` | cible corrigée |
| `test_retours11f4::test_f5_prix_de_sortie` | libellé rendu `Prix de sortie — bâti secteur`→`Prix de l'ancien (secteur)` (FICHE-FIX-4 J) | attendu mis à jour |
| `test_retours16_permis::test_v2_puce` | chips `badge-nongeo`/`etat` retirés de la ligne (RECETTE-1 H2) | garde la suppression + `data-permis-row-etat` |
| `test_renouvellement_liste::test_densifier` | « Déjà bâti » retiré du filtre (RECETTE-1 E2) | garde le retrait |
| `test_front_chiffres2::test_f04` | `FinancierQuestionnaire.tsx` renommé (Bilan BILAN-1/2) | chemin → `lib/api.ts`, liaison vérifiée |
| `test_front_chiffres2::test_f96` | symbole `_MILLESIME_SERVI`→`_MILLESIME_SERVI_REPLI` | import corrigé |

Back / outillage :

| Test | Cause | Réparation |
|---|---|---|
| `test_mp_exports::test_editeur_identite` | identité éditeur mise à jour (Saint-Paul→Saint-Denis) | attendu = ville servie actuelle |
| `test_prospect` (×2) | stub `Ctx` périmé : manquait `surface_incertaine` / `terrain_sur_dessin` / `regles_non_modelisees` (champs ParcelContext ajoutés par CONTENANCE-1, lus par `parcel_faisabilite`) | stub aligné sur `ParcelContext` (surface claire → chemin nominal) |
| `test_backup_tuile::test_repertoire_absent_dit_non_configure` | `_age_backup` retombe sur le miroir local `~/labuse-backups` (DASHBOARD-FIX-1) → « local » sur un poste qui l'a | `monkeypatch.setenv("HOME", tmp_path)` → déterministe (« non_configure » en CI comme en local) |
| `test_projets_fix_vivier` (×4) | le seed insérait le dryrun sous `Q_A_RUN_LABEL` ; `_cadrage_total` joint le dryrun sur `runs.cascade()` (`q_v18_sources` ≠ `q_v18`) → vivier 0 | seed du dryrun sous `runs.cascade()` |
| `test_rate_limit_off::test_banc_ne_depend_pas_de_dev_mode` | le grep trouvait `LABUSE_DEV_MODE` dans des **docstrings** expliquant la non-dépendance | strip commentaires + chaînes (`tokenize`) avant la recherche — on vérifie la dépendance de CODE, pas le mot |
| `test_donnees_fix1_discordance::test_discordance_egout` | nouveau motif prioritaire « faîtage sous BD TOPO » (RECETTE-2 A4) captait l'input | input ajusté (faîtage ≈ BD TOPO) pour exercer le motif « égout ↔ BD TOPO » voulu |
| `test_cron1_lot3` / `test_ops_healthz` / `test_dashboardfix1_horloges` (×3) + `HORLOGES.csv` | commit `474eff54` (13/10) a retiré `ingest-ban` du registre et passé `agents-sources` en `planifie=False`, sans suivre les tests ni le CSV | tests comparés aux jobs **planifiés** (dynamique, registre fait foi) + `HORLOGES.csv` régénéré (horloges = planifiés) |

### 4. Marqués `reel` (données réelles — hors CI, banc de nuit en prod)

Marqueur `reel` ajouté à `pyproject.toml`. CI jouera `-m "not local and not reel"`.

- `test_circuit_p_lot1::test_detail_reservoir_robinet_pompe_rapides`
- `test_cloisonnement_1::test_copilote_questions_et_plafond_cloison`
- `test_score_e::test_build_ecartee_exclue_et_non_estimable`
- `test_served_cascade::test_default_run_est_le_run_servi_pas_q_v8`
- `test_zone_recette::test_flash_par_adresse_trouve_la_parcelle`
- `test_simulplu` (×2)
- `test_golden_run_servi::test_golden_grave_sur_le_run_servi` (golden régénéré à la bascule du run)
- `test_circuit_p2_lot3::test_agents_avec_credit_journalise` (appelle le vrai SDK Anthropic)

> Note Lot 2 : certains de ces `reel` sont peut-être « seed-complétables » pour revenir en famille
> « base de test » et renforcer la CI — à réévaluer au Lot 2.

### 5. ⚠ `xfail` + À ARBITRER PAR VIC (quarantaine motivée, `strict=False`)

Ces cas ne sont PAS des tests périmés anodins : le garde-fou a attrapé quelque chose de réel, mais
la résolution demande un arbitrage produit/registre hors du périmètre « mise en place CI ».

1. **`test_faisabilite::test_u1pru_stationnement_exempte_non_borne` + `::test_plafond_densite_borne_les_zones_denses`**
   — la zone **U1pru est devenue NON-calculable** depuis PLU-CALIBRAGE-6 (son retrait
   `retraits.limites_separatives` est resté feuille « propose »), comme U3a/U6a. Le MOTEUR reste
   correct (régime exempt Art.12 + plafond densité existent, `engine.py`), mais SEULE U1pru portait ces
   capacités → **plus exerçables via une zone calculable**. **À décider :** recalibrer U1pru (décision
   PLU, hors CI) ou retirer ces deux tests.
2. **`test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens`** — le garde-fou du registre des
   lectures a attrapé une **dérive réelle accumulée** : **11 lecteurs non déclarés** (`dvf_mutations`
   par bilan/reperes.py, `dvf_mutations_parcelle` par api/fiche_blocs3.py, `owner_enrichment` par
   rgpd_dirigeants.py, `parcel_anc` par api/app.py, `parcels` par api/bilan.py + bilan/reperes.py +
   cadastre_disparue.py + facturation.py + financier_questionnaire.py, `pm_dirigeants` par api/app.py +
   rgpd_dirigeants.py) **+ 1 déclaration périmée** (`dvf_mutations` déclarée lue par api/projets.py qui
   ne la lit plus). **À faire :** tâche de **maintenance du registre** (`registre/lectures.py`) —
   déclarer finement chaque arête (table→chiffre→robinet).
3. **`test_garanties::test_g5_jamais_verifie_est_gris` + `::test_g6_vert_apres_raccords`** —
   `etat_reservoir({})` (réservoir `one_shot` non sondé) rend `("mint","à jour")` au lieu de
   `("gris","jamais vérifiée")`. **Divergence code↔test** sur une règle produit (que doit afficher un
   réservoir jamais sondé ?). **À décider :** corriger `circuit_etats.etat_reservoir` ou le test.
4. **`test_exports2_lot2::test_faux_constructible_jamais`** — CHASSE-FIX-2 (D04) fait désormais
   imprimer le `libelle` du bloc potentiel (`exports/verdicts.py:79-80`). Le test injecte
   VOLONTAIREMENT un `libelle` POSITIF (« Fort potentiel ») pour vérifier qu'un non-constructible ne
   l'affiche JAMAIS. Sous le code actuel ce libelle positif **fuiterait** → « réparer » le test
   pourrait **bénir une vraie régression de faux-constructible**. **À décider :** `verdicts.py`
   doit-il filtrer un libelle positif sur cause de non-constructibilité ?

### Résultat Lot 1

Suite Python, filtre CI, base vierge `labuse_test_ci` :
`pytest -m "not local and not reel"` → **3686 passed, 6 xfailed, 78 skipped, 42 deselected, 0 failed** (~2 min).
Les 6 `xfailed` = les cas d'arbitrage §5. Les `local` (base réelle) et `reel` (données réelles) sont
déselectionnés (joués au banc de nuit en prod).

Front : `tsc -b` ✅ · `vitest` **256/256** ✅ · `vite build` ✅.

Aucune écriture dans la base applicative `labuse` : tout sur `labuse_test_ci` (auto-créée, isolée).
