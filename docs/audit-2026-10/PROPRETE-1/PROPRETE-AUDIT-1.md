# PROPRETE-AUDIT-1 — à quel point LABUSE est propre, mesuré contre l'étalon

**Branche** `audit/proprete-1` · worktree `~/Desktop/labuse-proprete` · base `origin/main` `3e3a2afa` (04/10/2026) · **lecture seule** (aucun fichier d'app modifié, aucun outil ajouté à `pyproject.toml`/`package.json` — tout en `uvx`/`npx`/venv éphémère). Rejouable : `make proprete` → `scripts/proprete/run_all.sh`, sorties brutes dans `scripts/proprete/raw/`.

## Note globale : **D** — plancher tiré par la **sécurité (E)** et par la dette de dépôt/structure

Chaque domaine porte UNE note (la plus basse des sept = note globale, puis la moyenne) :

| # | Domaine | Note | Ce qui fixe la note |
|---|---------|------|---------------------|
| 1 | Dépôt | **D** | Pas de CI ni pre-commit ; ~2 Go d'artefacts générés commités (4545 fichiers), pack .git 4 Go ; 49 branches mergées non supprimées. Secrets : 0 réel. |
| 2 | Python | **D** (sécurité **E**) | 20 CVE / 7 paquets + 13 bandit HIGH (E) ; 7299 ruff + 748 fichiers non formatés ; 27 fichiers >800 l (app.py 8386) ; 376 fonctions CC>15. |
| 3 | TypeScript/React | **C** | Noyau exemplaire (tsc strict 0, 0 `@ts-ignore`, build propre) MAIS ESLint absent, 17 cycles, 1 CVE npm critical, 26 composants >400 l. |
| 4 | Tests | **D** | Couverture globale 47 % (plancher) ; cœur sous-couvert (`residuel.py` 49 %, `assemblage.py` 16 %, 8 blocs PDF 0 %) ; suite 13 min, non mesurée en CI ; 1 erreur de collecte. Discipline bonne (0 trivial, 0 toléré-rouge). |
| 5 | Base de données | **C** | 52 Go / 261 tables, dont ~18 Go de tables dry-run/doublons tronquables ; 80 index inutilisés (741 Mo) ; pas de système de migration. Pas de bloat aigu (autovacuum sain). |
| 6 | Scripts/config/docs | **D** | `.env.example` couvre 12 clés sur 108+ lues (122 `LABUSE_*` non documentées dont `SECRET_KEY`) ; aucun lockfile + 46 bornes `>=` ; 21 scripts + 33 CLI morts ; 3 docs d'audit périmés. |
| 7 | Architecture | **B** | Socle sain : factory BDD unique, registre auto-vérifié, dédoublonnages (médiane/export/résiduel/taxe) tenus. Dette = calcul métier épars dans quelques routes + couplage glue→API. |

**Moyenne ≈ D** (4 domaines sur 7 en D). Le produit a un **cœur sain** (architecture, registre, typage TS strict, duplication quasi nulle, aucun vestige mort) mais une **enveloppe négligée** (dépôt gonflé d'artefacts, aucune CI/garde automatisée, dépendances non patchées, configuration non documentée).

---

## Les 10 constats qui comptent

1. **Aucune CI, aucun pre-commit.** Rien n'empêche aujourd'hui de pousser du code non formaté, non typé ou cassé. C'est la cause-racine de la plupart des autres écarts (format, lint, CVE qui s'accumulent). Priorité FIX-1.
2. **Sécurité = seul risque E.** 20 CVE Python sur 7 paquets (`pypdf`, `torch`, `starlette`, `urllib3`, `anyio`, `setuptools`, `weasyprint`) + **1 CVE npm _critical_** (`maplibre-gl`) — toutes avec correctif publié, aucune n'exige de refactor. + 13 bandit HIGH (MD5/SHA1 ×12, tarfile unsafe).
3. **~2 Go d'artefacts générés commités** (4064 PNG, 152 PDF, HTML/HAR/CSV/ZIP) sous `qa/` (722 Mo), `docs/audit-2026-09` (913 Mo), `captures/` (267 Mo), `reports/` (175 Mo) ; pack `.git` à 4 Go (le ZIP `O12_PARTIEL_REVUE` seul revient 5× dans l'historique). Le dépôt se clone lourd pour rien.
4. **`api/app.py` = 8386 lignes** mélangeant 105 routes + 189 SQL bruts + 139 `SELECT` en f-string + texte client + fonctions à CC 139 (`_q_v2_where`). Point noir structurel n°1 (FIX-2).
5. **Dette de style purement mécanique et énorme mais plate** : 748/764 fichiers Python jamais passés au formateur, 7299 violations ruff dont 767 auto-corrigeables. Un commit `ruff format` + `--fix` règle la moitié sans risque fonctionnel.
6. **Base : ~18 Go récupérables** — `dryrun_cascade_results` 15 Go/74 M lignes + `dryrun_parcel_evaluations` 359 Mo (tables de dry-run tronquables) + `p_model_dataset_v2bis` 1,85 Go (doublon de `v2`) + 80 index jamais scannés (741 Mo). Aucun bloat de dead-tuples en revanche (autovacuum sain).
7. **`.env.example` ment par omission** : 12 clés documentées pour 108+ réglages réellement lus ; 122 variables `LABUSE_*` absentes dont `LABUSE_SECRET_KEY`, `LABUSE_STRIPE_*`, `LABUSE_SMTP_*`. Un opérateur ne peut pas configurer la prod depuis l'exemple.
8. **Builds non reproductibles** : aucun lockfile (`uv.lock`/`requirements.lock`), 46 dépendances en borne `>=` flottante. Surface de dérive et de supply-chain pour un produit en go-live.
9. **Code/scripts/docs morts identifiés** : 21 scripts orphelins + 33 commandes CLI jamais citées (campagnes q_v10/v8, arènes de scoring, o12) ; 6 fichiers TS morts + ~150 exports morts (barils `api.ts`/`types.ts`) ; 9 items Python ; 3 rapports d'audit qui **contredisent le code corrigé depuis** (pc_caducs 4+6, run11 « non servable », RAP L524-7).
10. **Le cœur de calcul est sous-testé** : couverture globale **47 %** (plancher), avec `faisabilite/residuel.py` à **49 %**, `assemblage.py` **16 %**, `exports/builder.py` **34 %** et **8 blocs PDF à 0 %** — et la suite n'est **mesurée par aucune CI** (`pytest-cov` même pas installé). La discipline est bonne (0 test trivial, 0 toléré-rouge, 0 `xfail`), mais la couverture dépend d'une base prod peuplée (257 tests `@db`, 2 runs contre `labuse` ont hangé). *(Install contradictoire README venv vs README_DEV conda : voir domaine 6.)*

## Ce qui est déjà propre (à préserver)

- **Architecture du cœur** : une seule factory de connexion BDD (`db.py`), registre des chiffres **auto-vérifié par test** (liste d'exceptions vide), le front ne fabrique plus aucun chiffre client (acquis FRONT-CHIFFRES-1/2), dédoublonnages médiane/export/résiduel/taxe **tenus**.
- **TypeScript** : `strict: true` déjà actif, `tsc --noEmit` et `vite build` à **0 erreur**, **0 `@ts-ignore`/`@ts-expect-error`**, 0 dépendance réellement morte, discipline Tailwind à 99 % de classes sémantiques.
- **Qualité de fond Python** : duplication **0,61 %** (jscpd), **0 `except:` nu**, aucun module vestige (`flash/`, `renouvellement`, « Densifier » tous LIVE), TODO stables (42, ~3 mois).
- **Git** : 0 secret réel (28 détections = HTML scrapé, fixtures, maquettes), 0 `.env`/`__pycache__`/`.DS_Store` suivi, 86 % des messages de commit suivent la convention `MANDAT — sujet`, 0 branche morte >30 j.
- **Base** : pas de bloat de dead-tuples, `deploy.sh` idempotent et sauvegardé.

---

## Détail par domaine

### 1 · Dépôt — D
Secrets (gitleaks, 3985 commits) : **28 détections, 0 secret LABUSE réel** — `qa/` HTML scrapé leboncoin (15), maquettes docs (7), fixtures de tests (4), `basemaps.ts` (2, faux-positifs sur `key:` littéral). Artefacts : **597 fichiers >1 Mo**, **4545 binaires générés** commités ; pack `.git` **4,02 Go**. Branches : **49/50** déjà mergées dans `origin/main`, jamais supprimées (0 morte >30 j, projet récent). **Pas de CI** (`.github`, gitlab, circle absents), **pas de pre-commit**. Hygiène `.gitignore` bonne (rien à ignorer qui soit suivi). Conventions de commit : **86 %** lisibles.

### 2 · Python — D (sécurité E)
`ruff check` (E/F/W/I/B/UP/SIM/C4/PL) : **7299** (top : PLC0415 import-in-function 2828, E501 1190, PLR2004 688 ; **8 F821 undefined-name** = vrais risques ; 767 auto-fix). `ruff format --check` : **748/764 non formatés**. Typage : **79,9 %** des `def` annotés en retour, `ty` sur le cœur = **47 erreurs**, mypy absent. `vulture` ≥80 % : **9 morts**. `deptry` : 843 bruts mais **0 réel** (faux-positifs `-e .` + alias `cv2`/`yaml`/`fitz`). `bandit -ll` : **13 HIGH** (MD5/SHA1 ×12 + tarfile), **338 MEDIUM** (SQL f-string B608 ×312). `pip-audit` : **20 CVE / 7 paquets**. `radon` : moyenne **5,76 (B)**, mais **754 CC>10 / 376 CC>15** (pire `render_fiche_pdf` CC 314). **27 fichiers >800 l** (`app.py` 8386). Hygiène : 31 `print()` dans `src/`, **635 `except Exception` larges**, 42 TODO. Noms FR/EN mélangés (~10 %). Vestiges : **aucun mort**.

### 3 · TypeScript/React — C
`tsc --noEmit` **0 erreur** (strict déjà actif) ; durcissements restants : exactOptionalPropertyTypes +109, noUncheckedIndexedAccess +162. **ESLint ABSENT** → 39 `eslint-disable` dormants. `knip` : 6 fichiers morts + 150 exports + 152 types + 9 exports dupliqués. `madge` : **17 cycles** (hubs Admin/Outils/Radar). Trappes : 66 `any`, **0 `@ts-ignore`/`@ts-expect-error`**. **26 composants >400 l** (`api.ts` 2632, `Fiche.tsx` 2054). Styles : 501 hex inline hors `ui/` dans ~15 `.tsx` (le reste discipliné). `npm audit` : **11 (1 critical `maplibre-gl` + 7 high)**. Build **OK 4,52 s**, dist 3,9 Mo. 0 dépendance réellement morte.

### 4 · Tests — D
**3645 tests collectés, 1 erreur de collecte** (`test_marche_commune.py` ouvre une connexion DB à l'import → casse `pytest --co` sur tout poste sans le rôle `labuse`). Ignorés : **48 skipped** au runtime (11 `skipif` + 78 `pytest.skip` + **0 `xfail`**), **tous conditionnés à l'environnement/aux données, aucun rattaché à un ticket**. **0 test toléré rouge** (aucune liste, 0 `xfail_strict`) — le « 3 tolérés » du mandat n'a aucune trace en config. **Couverture globale 47 %** (plancher : 998 tests en timeout de 60 s sur `labuse_test` faute de données prod ; `pytest-cov` n'était même pas installé). Cœur sous-couvert : `faisabilite/residuel.py` **49 %**, `assemblage.py` **16 %**, `exports/builder.py` **34 %**, **8 `exports/blocs/*` à 0 %**, `cascade/*` 22-28 %, `scoring/p_v2/pipeline` 15 % — bien couverts en revanche : `zonage.py` 94 %, `registre/donnees.py` 100 %, `score_labuse.py` 90 %. Suite **811 s (13 min 31)**, non découpée (pas de CI). Couplage base : **257 `@pytest.mark.db` + 18 `@pytest.mark.local`** ; **2 runs contre la vraie base `labuse` ont hangé (>5 min)**. Front : **vitest 225 tests / 50 fichiers verts**, mais couverture front indisponible (`@vitest/coverage-v8` absent). **0 test trivial / auto-mockant** (bon signe).

### 5 · Base de données — C
**52 Go / 261 tables**. Plus grosses : `dryrun_cascade_results` **15 Go/74 M lignes**, `parcel_p_score_v2` 7,7 Go, `spatial_layers` 4,1 Go, `score_labuse` 3 Go. Tables de run/doublons : **~18 Go** tronquables (`dryrun_*` + `p_model_dataset_v2bis` doublon de `v2` + `parcel_residuel_runs` + `score_snapshot_parcelles`). **Pas de dead-tuple bloat** (autovacuum sain). **80 index `idx_scan=0`** non-uniques = 741 Mo. Scans séquentiels lourds : `spatial_layers` 3,6 M. **Pas de système de migration** (alembic absent) : schéma = 38 tables ORM + 224 `CREATE TABLE` dans `src/` + 151 dans `scripts/` → source fragmentée, dérive non vérifiable. Réglages PG corrects pour la taille (shared_buffers 2 Go, effective_cache_size 4 Go — un peu bas).

### 6 · Scripts/config/docs — D
**21/199 scripts orphelins** ; **33/207 commandes CLI** jamais citées (+ doublons `evaluer-veilles`/`radar-fusion`/`fraicheur-etat`). Config : prix 349/79 € réécrits en clair hors `config.py`, 2 YAML cascade, 2 YAML solaire, 3 stores scoring. **`.env.example` : 12 clés vs 108+ lues (122 `LABUSE_*` non documentées)**. `docs/audit-2026-09` : 2144 fichiers / 913 Mo / 109 sous-dossiers ; **3 rapports contredisent le code actuel**. README contradictoires (venv vs conda). `deploy.sh` **idempotent** mais **aucun lockfile** + 46 bornes `>=`. 1 secret DEV en clair (`docker-compose.yml` `POSTGRES_PASSWORD:labuse`).

### 7 · Architecture — B
Imports remontants service→API : 119 / 34 fichiers mais **98 % paresseux** et **cœur moteur à 0 import top-level d'API** (pas d'inversion de couche) ; connecteurs propres. Calcul métier dans des routes : `scoreur.py:75`, `moteurs.py:219-235` (barème à constantes magiques), `traducteur.py:57/68`, `projets.py:440`. **0 SQL dans le front**. Texte client dans le moteur = verdicts calculés (légitimes). **Connexion BDD : factory unique** `db.py` (seul écart : un `create_engine` isolé `cli.py:2964`). **Registre auto-vérifié**. **Points d'entrée uniques** confirmés (médiane/export/résiduel/taxe).

---

## Découpage proposé en mandats de correction

### PROPRETE-FIX-1 — sans risque, sans changement de comportement (≈ 2–3 j)
*Format, imports, fichiers/branches/tables morts, dépendances, config, garde-fous.*
- `ruff format` + `ruff check --fix` (767 auto), élaguer 82 F401 + 9 vulture + 6 fichiers TS morts + barils `api.ts`/`types.ts` (TOP-20 #2, #10).
- **Sécurité** : bumper les 7 paquets CVE Python + `maplibre-gl`/`tailwindcss` npm ; MD5/SHA1 → `usedforsecurity=False` (TOP-20 #4, #5, #16).
- **Base** : `TRUNCATE` les tables dry-run (+15 Go), `DROP` `p_model_dataset_v2bis` (1,85 Go), `DROP` 80 index inutilisés (741 Mo) — après vérification qu'aucun run actif ne les écrit (TOP-20 #1, #3, #6).
- **Dépôt** : supprimer 49 branches mergées ; sortir les artefacts générés du suivi + étendre `.gitignore` (TOP-20 #7, #11).
- **Config** : compléter `.env.example` (122 vars), ajouter un lockfile + épingler, supprimer 21 scripts + 33 CLI morts, archiver/corriger les 3 docs périmés (TOP-20 #8, #9, #12, #13).
- **Garde-fous** : mettre en place CI (lint/format/types/tests) + pre-commit + config ESLint — ce qui **verrouille** tout le reste (TOP-20 #14, #15).

### PROPRETE-FIX-2 — structurel (≈ 5–8 j)
*Découpage des fichiers géants, cycles, complexité, altitude.*
- Découper `api/app.py` (8386 l) en routeurs par domaine ; extraire le SQL vers une couche d'accès ; casser les fonctions CC>15 (`render_fiche_pdf` 314, `_q_v2_where` 139) (TOP-20 #19).
- Découper les gros composants TS (`api.ts` 2632, `Fiche.tsx` 2054, `ModulePanel` 1844) et casser les 17 cycles `madge` (TOP-20 #20).
- Rapatrier le calcul métier des routes (`scoreur`/`moteurs`/`traducteur`/`projets`) vers le moteur (TOP-20 #17).
- Durcir `tsconfig` (exactOptionalPropertyTypes, noUncheckedIndexedAccess) une fois la dette résorbée (TOP-20 #18).
- **Couverture du cœur** : corriger l'erreur de collecte (`test_marche_commune.py`), installer `pytest-cov`/`@vitest/coverage-v8`, borner les requêtes de test, et remonter `residuel.py`/`assemblage.py`/`exports/blocs/*` vers ≥ 80 % sur une base de test peuplée — préalable à une CI qui mesure vraiment.
- (À arbitrer) doter la base d'un vrai système de migration pour fixer la source du schéma ; réduire les 635 `except Exception` larges.

*Rien n'a été exécuté : cet audit est en lecture seule.*
