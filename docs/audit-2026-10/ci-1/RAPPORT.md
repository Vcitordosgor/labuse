# RAPPORT CI-1 — aucun code cassé n'arrive dans main

Branche `feat/ci-1`, worktree `~/Desktop/labuse-ci`. Rien sur le VPS. Aucune écriture dans la base
applicative `labuse` (deux autres sessions tournaient) : la suite tourne sur une base de test DÉDIÉE
`labuse_test_ci`, isolée du `labuse_test` partagé des autres worktrees.

> État : Lot 1 ✅ · Lot 2 ✅ · Lot 3 ✅ · Lot 4 ✅ · Lot 5 ✅ · Preuve ✅ · Rebase sur main ✅.

## Rebase sur main (SOLIDITE-1) — conflits + isolation

`feat/ci-1` rebasée sur `origin/main` (qui a reçu SOLIDITE-1 : registre des jobs modifié — `ingest-ban`
retiré, `agents-sources` manuel, +3 jobs). Résolution :

- **Conflits de registre** (`HORLOGES.csv`, `test_cron1_lot3`, `test_dashboardfix1_horloges`,
  `test_ops_healthz`) : résolus en prenant **la version de main** (le registre de main fait vérité ;
  ses tests sont déjà « planifiés-dynamiques », même intention que mon Lot 1). Vérifiés verts contre
  le registre de main.
- **Isolation de suite (dette pré-existante de main, exposée par la CI base-vierge)** : sur base
  PostGIS vierge, 14 tests tombaient par POLLUTION inter-tests (collisions d'IDU figés `97499000ZZ0001`…).
  **Cause racine trouvée** : un test rendait au pool une connexion en **AUTOCOMMIT** → `db_session` la
  réutilisait → ses INSERT étaient auto-committés (fuite) et `begin_nested()` cassait (« SAVEPOINT can
  only be used in transaction blocks »). **Correctif racine (1 ligne)** : `db_session` force
  `isolation_level="READ COMMITTED"` à la prise de connexion → transaction réelle, pool guéri quel que
  soit le leak → les 14 disparaissent. (Pistes écartées car cassant d'autres tests : savepoint global,
  TRUNCATE avant chaque test.) + 2 robustesses ciblées : `test_vefa_moteur_unique` purge sa plage d'id
  (il committe via `session_scope`), `test_lot4_communes::test_v4a` marqué `reel` (enforcement FK
  dépendant du référentiel commune).

Validé sur base NEUVE (miroir exact CI) : **3702 passed, 6 xfailed, 0 failed/0 error**.

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

---

## Lot 2 — trier les tests (3 familles par marqueur)

### Taxonomie retenue

| Famille | Marqueur | Base | CI ? |
|---|---|---|---|
| **unitaires** | *(aucun)* | AUCUNE | oui |
| **base de test** | `db` | PostGIS **vide** + petites fixtures | oui (conteneur PostGIS) |
| **données réelles** | `reel` (+ `local`) | base complète | **non** (banc de nuit en prod) |

`network` (sortant) exclu de la CI. Documenté dans `docs/TESTS.md` § « Familles de tests ».
Cibles ajoutées au `Makefile` : `test-unit`, `test-db`, `test-ci`, `test-reel`, `test-front`.

### Tri effectué

La famille « unitaires » devait être **sans base** (socle du hook pre-push rapide, Lot 4). Or ~36
tests NON marqués touchaient en réalité la base. Détectés en pointant la base sur un port mort
(5999) et marqués `db` :

- **module entier `db`** (tous les tests passent par la base) : `test_comptes`, `test_facturation`,
  `test_fiche_ask`, `test_rebranchement1_lot3`, `test_copilote2_fiche`, `test_partners_api_v1`,
  `verrous/test_v6b_coherence` (composé avec `verrous`).
- **par fonction** (fichiers mixtes — seuls les tests qui touchent la base) : `test_copilote2_memoire`
  (3), `test_ai_core` (1), `test_sources_fix1` (1), `test_veille_fix1` (1), `test_retours11f3`
  (`test_avenant_r11`, que le fork front avait signalé), `test_pont_tier` (1 paramétré),
  `verrous/test_garanties` (g3/g4/g7 « prouve casse » — lecture seule, 0 écriture dans `labuse`).

### Résultat Lot 2

- **unitaires SANS base** (`make test-unit`, base pointée sur port mort) : **2326 passed, 146 skipped,
  6 xfailed, 0 failed, 0 error** → la famille « unitaires » tourne vraiment sans base.
- **base de test AVEC base** (`make test-db`, `labuse_test_ci`) : **1260 passed, 32 skipped, 0 failed**.
- Sélection CI (`make test-ci` = unitaires + base de test) : inchangée vs Lot 1 → verte.

---

## Lot 3 — la vérification GitHub

Fichier `.github/workflows/ci.yml` — déclenché à **chaque push (main et toute branche)**,
3 jobs **parallèles**, `concurrency` annule les runs superposés, caches pip/npm pour tenir < 10 min.
Aucun secret, aucun accès prod/.env/base réelle : tout sur une base de test éphémère.

| Job | Contenu |
|---|---|
| **python** | conteneur `postgis/postgis:18-3.5` (MÊME majeure que la prod, PostgreSQL 18) ; libs système weasyprint (pango/cairo) pour les tests PDF ; `pip install -e ".[dev,ci]"` ; `pytest -m "not local and not reel and not network"` |
| **frontend** | `npm ci` · `npx tsc -b` · `npx vitest run` · `npx vite build` (cache npm) |
| **secrets** | `scripts/ci/scan_secrets.sh` |

Décisions :
- **PostGIS 18** = majeure de la prod (`deploy/scripts/vps_setup.sh` installe PostgreSQL 18/PostGIS 3) —
  le docker-compose DEV est en 16, mais la CI doit refléter la PROD.
- **Pas de torch en CI** : la sélection CI importe `pandas`/`scikit-learn` (via scoring p_model/p_v2)
  et `openpyxl` (Bilan xlsx), jamais `torch`/segmentation-models (ML lourd, hors chaîne servie).
  Nouvel extra `pyproject [ci]` = pandas/scikit-learn/joblib/openpyxl (léger, rapide, cacheable).
- **weasyprint** importé paresseusement (pango requis au rendu seulement) → apt des libs pango/cairo
  pour les tests qui génèrent un PDF.
- **Scan de secrets maison** (`scripts/ci/scan_secrets.sh`, bash 3.2, `git grep`, zéro dépendance ni
  licence) : interdit tout `.env` suivi (hors `*.example`) + motifs à forte confiance (PEM, Stripe
  LIVE, Anthropic, AWS, Google, Slack, GitHub, URL avec mot de passe). Allowliste intégrée pour ne
  PAS flaguer les clés de TEST (`sk_test_`…), les placeholders `.env.example`, les URLs base locale.
  **Prouvé** : 0 trouvé sur l'arbre ; attrape un `sk_live_`/`sk-ant-` planté (exit 1). Réutilisé par
  le hook pre-push (Lot 4).

> La **preuve de bout en bout** (push → coche verte / commit cassé → croix rouge + mail) est au §
> « Preuve » en fin de rapport : elle nécessite un push sur GitHub (action sortante) — effectuée
> après les lots 4 et 5, en confirmant avec Vic.

---

## Lot 4 — le filet local avant envoi

Hook `scripts/git-hooks/pre-push`, installé par **une commande unique** :
`bash scripts/ci/install-hooks.sh` (pose `core.hooksPath=scripts/git-hooks` — hook versionné,
partagé par tous les worktrees). Documenté dans `docs/EXPLOITATION.md` § « Vérification avant envoi ».

À chaque `git push`, en < 2 min et **sans base** (famille unitaire) :
1. scan de secrets (`scripts/ci/scan_secrets.sh`, réutilisé du Lot 3) ;
2. front : `tsc -b` + `vitest` (pas `vite build` : trop lent pour un pre-push) ;
3. Python : `pytest -m "not db and not local and not reel and not network"`.

Échec → **push refusé**, message clair + rappel `git push --no-verify` (urgence seulement — la CI
GitHub re-vérifie après l'envoi). Le hook retrouve le `.venv` même depuis un worktree lié (via
`git rev-parse --git-common-dir`) et exige `pytest` (jamais un python système nu).

**Mesuré** (poste, arbre propre) : **EXIT 0 en 94 s** — 2326 unitaires (41 s) + front (tsc+vitest) +
scan. Mécanisme de **refus prouvé** (une étape qui échoue → `✗ PUSH REFUSÉ` + exit 1).

> Non installé pendant cette session : `core.hooksPath` est une config git PARTAGÉE (elle
> toucherait les autres worktrees des sessions en cours). C'est **à Vic** de lancer
> `bash scripts/ci/install-hooks.sh` dans son dépôt principal.

---

## Lot 5 — l'alerte

**Choix : notification native GitHub** (mail à l'auteur du push quand sa CI échoue). C'est le « au
plus simple » du mandat ET le seul respectant « aucun secret dans GitHub » : l'alerte unique de
SOLIDITE-1 (SMTP Brevo) exigerait de poser `SMTP_*`/`ADMIN_EMAIL` en secrets GitHub — écarté.

Comme Vic est celui qui pousse sur `main`, il reçoit le mail à chaque croix rouge. Réglage à cocher
une fois (documenté dans `docs/EXPLOITATION.md` § « L'alerte ») :
**GitHub → Settings → Notifications → Actions → Email + « failed workflows only ».**

Aucun changement de workflow nécessaire (la notification est native). Le mail pointe le run ; le
détail (job, test) est sur la page du run.

---

## Preuve (bout en bout sur GitHub)

`feat/ci-1` a été poussée (branche, PAS mergée). Dépôt : `github.com/Vcitordosgor/labuse`.

### a) Vert — `feat/ci-1`

Run **38475032453** → **success** : Python ✅ · Front ✅ · Secrets ✅.
(`https://github.com/Vcitordosgor/labuse/actions/runs/38475032453`)

### b) Le filet LOCAL refuse un commit cassé

Branche jetable `ci-1-preuve-cassee` + `frontend/src/_ci_preuve_cassee.ts` :
`export const preuve: number = "pas un nombre"`. Le hook pre-push, joué sur ce commit :

```
▶ Front — tsc -b
src/_ci_preuve_cassee.ts(1,14): error TS2322: Type 'string' is not assignable to type 'number'.
…
✗ PUSH REFUSÉ — une vérification a échoué (détail ci-dessus).
```
`exit 1` → le push est bloqué en local.

### c) Rouge + mail — contournement `--no-verify`

Poussé avec `git push --no-verify` (le cas d'urgence documenté). Run **38475959465** →
**failure** : **Front → failure** (tsc TS2322), Python ✅, Secrets ✅.
(`https://github.com/Vcitordosgor/labuse/actions/runs/38475959465`) La croix rouge déclenche la
notification native GitHub (mail à l'auteur du push). Branche jetable **supprimée** ensuite
(local + distant) ; `feat/ci-1` n'a jamais porté le commit cassé.

### d) Ce que la preuve a VRAIMENT prouvé — la CI attrape le « marche sur ma machine »

Avant même le commit cassé volontaire, les premiers runs ont attrapé **7 écarts réels** invisibles
en local (c'est tout l'intérêt du mandat) ; chacun corrigé puis re-vérifié vert :

1. `postgis/postgis:18-3.5` **inexistant** → `18-3.6` (image PG18 publiée).
2. 2 **snapshots** front sensibles au fuseau (Mac UTC+2 vs CI UTC) → `TZ=Indian/Reunion` forcé + snapshots régénérés.
3. `pytest` nu n'ajoute pas le CWD → `import scripts` KO → `python -m pytest`.
4. Base PostGIS **vierge** (ce que la CI a, pas le poste) → conftest réécrit en **parité boot convergé** (scoping en dernier + `compte_id` R9 + colonnes Filosofi).
5. `anthropic` absent (`[ai]`) → routeurs non montés → `pip install .[dev,ci,ai]` ; Postgres CI exigeait un mot de passe → `POSTGRES_HOST_AUTH_METHOD=trust` ; tuiles servies → test `reel`.
6. `pip install -e .` flottait vers les **dernières** versions (561 warnings, routes différentes) → `-c requirements.lock` = **parité PROD** (warnings 561→15).
7. `/socle` (montage conditionné à `frontend/dist`) absent dans le job Python → **stub `dist`**.

> C'est la démonstration la plus forte : la suite était « verte » en local pour chacun de ces points,
> et rouge en CI. Désormais la CI (base vierge, versions figées, env propre) voit ce que le poste cache.
