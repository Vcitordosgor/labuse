# MANDAT DETTE-REPO — RAPPORT

**Branche** : `chore/dette-tests` · **Exécuteur** : Claude Code (Opus) · **État** : **Phase 2 exécutée — non mergée**
Zéro code de production touché (diff = 5 fichiers `tests/` + 2 docs). Aucun merge (Vic merge en `--no-ff`).

## État final de la suite (mesuré)

Avant : `17 failed, 1176 passed, 19 skipped, 66 errors`.
**Après : `1256 passed, 19 skipped, 3 xfailed, 0 failed, 0 errors` (55 s).** — 1256 + 19 + 3 = 1278 collectés. ✓

| Catégorie | Traité | Résultat |
|---|---|---|
| **C** (69, PROJ_DATA) | fixture conftest auto-découverte + échec bruyant | ✅ verts |
| **A.1** (4, protection) | `monkeypatch.delenv("LABUSE_DEV_MODE")` | ✅ verts |
| **A.2** (6, front impl) | assertions repointées sur le front refactoré | ✅ verts |
| **A.2** (3, front wording) | `xfail` motivé — **arbitrage Vic** (deltas ci-dessous) | ⏸ parqués |
| **E** (1, test_auth) | fuite corrigée **à la source** (2 fixtures audit) | ✅ vert |

**Garde-fous servis** : tiers du run servi `q_v7_defisc` mesurés en base — **120 / 1031 / 3587 / 72980 / 353945
au bit près** (`parcel_p_score_v2`). Golden 116/116 (face API) : **différé** — cf. § Golden.

---

## ⚠ ARBITRAGE VIC — 3 verrous de wording produit (deltas exacts)

Ces 3 tests verrouillaient une formulation servie ; le front l'a reformulée. Je **ne réécris pas** ces
verrous sans ton feu vert (boussole : jamais d'assouplissement silencieux). Ils sont `xfail(strict=False)`
en attendant. Décision par delta : **(a)** wording actuel validé → je mets le test à jour dessus ;
**(b)** wording d'origine à restaurer → ticket côté front (hors ce mandat, catégorie B).

| # | Test | Où c'est affiché | Ancien (verrou) | Actuel (servi) |
|---|---|---|---|---|
| 1 | `test_r3_tooltip_multiplicateur_de_rang` | tooltip du badge ×N (chaque ligne de résultat, `ResultsSection.tsx`) | « **Multiplicateur de rang** … au-dessus de la moyenne de **l'univers analysé** » | « ×N **vs moyenne du parc** » (via `CLIENT.mult.tip`, centralisé) |
| 2 | `test_r3_tooltip_jauge_completude` | jauge complétude — a **quitté** le panneau résultats (B2/M12), désormais sur la **carte Kanban** (`crm/Kanban.tsx`) | « part des sources disponibles » + « **N'est PAS une note de qualité du terrain** » | « part des sources disponibles, **pas une note de qualité** » (« du terrain » retiré ; tooltip déplacé) |
| 3 | `test_r3_matrice_non_thermique` | libellés du **tier P thermique** (badge/légende, `lib/status.ts`) | tier `'Brûlante **v2**'` / `'Chaude **v2**'` | `'Brûlante'` / `'Chaude'` (**suffixe « v2 » retiré**) |

> Note rassurante (#3) : l'invariant **matrice ≠ thermique** TIENT — la matrice Q×A rend toujours
> `'Priorité dossier'` (`STATUT_META`). Seuls les **noms** du tier thermique ont changé. Aucun `B`.

---

# Annexe — Diagnostic Phase 1 (conservé)

**État initial** : `POINT D'ARRÊT A`. Aucun code de production touché.

## Cadre de mesure (reproductible)

```bash
export LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse
export LABUSE_DEV_MODE=1 PYTHONPATH=src
.venv/bin/python -m pytest -q -p no:cacheprovider
```

- **Collection** : 1278 tests, **0 erreur de collection**.
- **Run complet mesuré** : `17 failed, 1176 passed, 19 skipped, 66 errors in 49.63s`.
- **83 cas** à classer = 17 failed + 66 errors. Correspond exactement à la dette annoncée au M26-A.

## Synthèse par catégorie

| Cat | Définition | Nombre | Traitement |
|---|---|---|---|
| **C** — dépendance d'environnement | pyproj ne trouve pas son répertoire de données PROJ (`DataDirError`) | **69** | Fixture / variable `PROJ_DATA` — **fix vérifié** |
| **A** — test non suivi (code/env a changé) | 4 protection + 9 front reliquats | **13** | Mettre à jour le test |
| **E** — ordre-dépendant | 1 (passe seul, échoue en suite) | **1** | Isoler le pollueur, corriger la fixture |
| **B** — bug réel dormant | — | **0** | — |
| **D** — test mort | — | **0** | — |

**Total : 69 + 13 + 1 = 83.** ✓  · **B = 0** (aucun bug produit dormant détecté après vérification directe).

---

## Catégorie C — PROJ_DATA absent (69 cas)

**Cause racine unique** : `pyproj.exceptions.DataDirError: Valid PROJ data directory not found`.
Le wheel `pyproj` installé sur ce poste ne contient **aucun** `proj.db` (pas de `proj_dir/share/proj`), et
`PROJ_DATA` n'est pas exporté. Tout code qui construit un `Transformer` (reprojection 4326↔2975) casse au setup.

**Répartition** (fichier → nb) :

| Fichier | Erreurs | Type |
|---|---|---|
| `tests/test_api.py` | 29 | ERROR (setup) |
| `tests/test_cascade.py` | 12 | ERROR (setup) |
| `tests/test_mutation_api.py` | 12 | ERROR (setup) |
| `tests/test_crm_columns.py` | 9 | ERROR (setup) |
| `tests/test_state.py` | 4 | ERROR (setup) |
| `tests/test_ai.py::test_evaluate_avec_ia_stocke_ai_payload` | 1 | FAILED |
| `tests/test_geo_surface.py` (×2) | 2 | FAILED |
| **Total** | **69** | |

**Fix vérifié (mesuré, pas estimé)** — un `proj.db` valide existe dans l'env conda de Postgres :
`/Users/openclaw/miniforge3/envs/labusedb/share/proj/proj.db`. Avec `PROJ_DATA` pointé dessus :

```
pytest test_api test_cascade test_crm_columns test_mutation_api test_state test_ai test_geo_surface
→ 79 passed, 0 failed, 0 errors
```

**Traitement proposé** (choix à confirmer) : fixture `conftest.py` en portée session qui **auto-découvre** le
répertoire PROJ (recherche `proj.db` sous `sys.prefix`, envs conda usuels, `/opt/homebrew/share/proj`) et appelle
`pyproj.datadir.set_data_dir(...)` / pose `PROJ_DATA` **avant** le premier import géo — jamais un chemin poste-spécifique
en dur. Si aucun `proj.db` n'est trouvé → `skipif` motivé (« données PROJ absentes »). Documenté dans `docs/TESTS.md`.

---

## Catégorie A — 13 cas

### A.1 · `tests/test_protection.py` (4 cas)

`test_quota_fiches_gel_jusqua_minuit`, `test_rate_limit_defi_puis_gel`,
`test_quota_tuiles_gel_jusqua_minuit`, `test_quota_carto_geojson_ile`.

**Cause** : ces 4 tests attendent `429` (gel quota / rate-limit) mais reçoivent `200/204/404`. Le cadre de run
**mandaté** exporte `LABUSE_DEV_MODE=1`, et — comme le documente le test voisin `test_dev_mode_exempte_rate_limit_et_quota` —
**DEV_MODE désactive rate-limit ET quota**. Ces 4 tests posent bien leurs env vars de quota mais **ne neutralisent pas**
le `LABUSE_DEV_MODE` ambiant, contrairement à leur frère `test_dev_mode_absent_la_garde_reste_active` (qui, lui,
fait `monkeypatch.delenv("LABUSE_DEV_MODE", raising=False)` et passe).

**Vérifié** : suite `test_protection.py` **sans** `LABUSE_DEV_MODE` → `13 passed`.

**Fix** : ajouter `monkeypatch.delenv("LABUSE_DEV_MODE", raising=False)` dans ces 4 tests (aligne sur le frère existant).
Test-only, zéro code produit. La garde de prod est déjà couverte et **verte** (`test_dev_mode_absent...`).

### A.2 · `tests/test_front_reliquats.py` (9 cas)

Tests de caractérisation front : ils lisent des `.tsx` et cherchent des marqueurs (chaîne/attribut/constante).
Le front a été **refactoré après** l'écriture des tests R1–R5 (commits M12/M19/M20/M-RENOUV/S13–S20) :
centralisation des libellés client (`lib/strings.ts` / `CLIENT.*`), outils servis via `registry.ts` + `ModulePanel.tsx`,
onglet fiche devenu littéral d'union (`'pourquoi'`) au lieu d'une constante `TAB_POURQUOI`, tooltips reformulés.
**Les fonctionnalités existent toujours** (composants `ScoreurAdresse`, `PourquoiPas`, `AskBar` présents ; « Scorer une
adresse » toujours surfacé) — seuls les marqueurs ont bougé/été renommés.

| Test | Marqueur attendu | Réalité actuelle | Nature |
|---|---|---|---|
| `test_r1_replie_par_defaut` | `useState(false)` dans AskBar | état repli refactoré (`data-askbar-open` toujours présent) | impl |
| `test_r1_redeploiement_sans_perte` | `dernière réponse gardée` dans AskBar | déplacé → `lib/strings.ts` | impl (relocalisation) |
| `test_r1_nav_onglets_hors_du_panneau_ia` | `...TABS` dans Fiche | `...TABS` déplacé → `ScoringV2.tsx` | impl |
| `test_r3_tooltip_multiplicateur_de_rang` | « Multiplicateur de rang » / « au-dessus de la moyenne de l'univers analysé » | reformulé « ×N vs moyenne du parc » (`data-mult-tip` présent) | **wording ⚠** |
| `test_r3_tooltip_jauge_completude` | « part des sources disponibles » dans ResultsSection | déplacé → `crm/Kanban.tsx`, formulation à revalider | **wording ⚠** |
| `test_r3_matrice_non_thermique` | `label: 'Chaude v2'`/`'Brûlante v2'` ; pas de `label: 'Chaude',` | suffixe « v2 » retiré des labels du **tier P thermique** (`TIER_V2_META`) ; matrice Q×A = `'Priorité dossier'` **intacte** | impl (renommage) |
| `test_r5_scoreur_trouvable_depuis_le_header` | `data-scoreur-open` dans Header | outil surfacé via `registry`/`ModulePanel` | impl |
| `test_r5_scoreur_champs_et_prix_manuel` | attributs `data-scoreur-*` dans ScoreurAdresse | markup ScoreurAdresse remanié | impl |
| `test_r5_pourquoi_pas_onglet_conditionnel` | constante `TAB_POURQUOI` dans Fiche | onglet = littéral `'pourquoi'` (union type) | impl |

**Vérification anti-B faite** : le seul marqueur suspect (`label: 'Chaude',` réapparu) a été inspecté directement dans
`frontend/src/lib/status.ts` → le `Chaude` bare est dans `TIER_V2_META` (échelle **thermique tier P**, où « Chaude » est
légitime) ; la matrice Q×A rend bien `'Priorité dossier'`. **L'invariant « matrice ≠ thermique » tient. Ce n'est pas un B.**

**⚠ Arbitrage à trancher (2–3 tests, lignes « wording »)** : `test_r3_tooltip_multiplicateur_de_rang` et
`test_r3_tooltip_jauge_completude` **verrouillent des formulations produit**. Les mettre à jour pour matcher le code
actuel = **ratifier une reformulation** qui n'a peut-être pas été validée (boussole : « jamais d'assouplissement
silencieux de critères »). → Je te présente les deltas de wording avant de réécrire ces verrous ; les 6–7 autres sont
du pur détail d'implémentation (relocalisation/renommage) que je mets à jour sans risque produit.

---

## Catégorie E — 1 cas

`tests/test_auth.py::test_local_par_defaut_tout_ouvert` — vérifie qu'en local (sans `LABUSE_AUTH_PASSWORD` ni env
pilote) tout est ouvert (`/pipeline/meta` → 200, `/login` → 302).

**Mesuré** : passe **seul**, passe aussi après `test_protection.py`, **échoue uniquement en suite complète**
(`AssertionError`). Pollueurs **identifiés par bissection** : `test_audit_conformite.py` ET `test_audit_secu.py`
— leurs fixtures `app_client` chargent des settings « pilote » via `monkeypatch` mais faisaient `return TestClient(...)`
**sans teardown** : `monkeypatch` restaure bien l'env, mais le **cache lru `config.get_settings` garde les settings
pilote** → `test_auth` (plus tôt en ordre alpha… en réalité plus tard) voit une auth active à tort.

**Corrigé à la source** (pas seulement la victime) : les 2 fixtures passent en `yield TestClient(...)` +
`config.get_settings.cache_clear()` au teardown — chaque test dirty nettoie derrière lui. Le prochain test dans
n'importe quel ordre ne retombera plus dessus.

---

## B (bugs réels dormants) — AUCUN

Après vérification directe des cas ambigus (protection, matrice non-thermique), **aucun** échec ne révèle un bug produit
dormant. Rien à arbitrer côté chiffres servis. Un seul point d'arbitrage **produit** subsiste et il est de nature
**wording** (cf. A.2 ⚠), pas un bug.

## D (tests morts) — AUCUN

Aucun test ne cible du code supprimé (pas de Score V legacy, pas de vue morte parmi les 83).

---

## Golden 116/116 — face API différée (honnête)

Le run golden complet (comparaison des 116 parcelles, face **API**) exige l'API locale démarrée sur la base
applicative. Or, au moment de la clôture, la **base applicative est sous un job de calcul division en cours**
(6 backends `INSERT INTO division_or_candidates`, actifs **> 13 min**, antérieurs à ce mandat) : le `_lifespan`
du serveur bloque sur un `ALTER TABLE parcels ADD COLUMN` en attente d'un verrou de relation tenu par ce job.
Contention **d'environnement**, sans rapport avec ce mandat.

Ce qui EST mesuré et vert :
- **Tiers du run servi au bit près** : `120 / 1031 / 3587 / 72980 / 353945` (`parcel_p_score_v2`, run récent) —
  la face « chiffres servis » du golden, lisible en base sans l'API.
- **Diff test-only** : `git status` = 5 fichiers `tests/` + 2 docs, **zéro `src/`**. Le run servi, le scoring,
  les moteurs, le champion P sont **intouchés** → golden invariant par construction.

À rejouer dès la base libérée (`qa/golden_check.py`, cf. `docs/TESTS.md`). Aucun `PASS` inventé (boussole :
« non vérifiable se dit »).

## Point de bascule prod/VPS (consigné)

Le défaut C n'est **pas** propre aux tests : le wheel `pyproj` sans `proj.db` casserait aussi le **serveur** (au
boot, il pose `PROJ_DATA` ? non — c'est `conftest` de test qui le fait). **Le kit VPS doit garantir un `proj.db`
système ou `PROJ_DATA`**, sinon reprojection cassée en prod. (Constaté ici en démarrant l'API : il a fallu poser
`PROJ_DATA` à la main pour le serveur.) Voir `docs/TESTS.md` § Données PROJ.

## Livrables & commits

Diff **test-only** (zéro production), un commit par catégorie :

- **[dette-tests · C]** `tests/conftest.py` — fixture PROJ auto-découverte + échec bruyant.
- **[dette-tests · A.1]** `tests/test_protection.py` — neutralisation `LABUSE_DEV_MODE` (×4).
- **[dette-tests · A.2]** `tests/test_front_reliquats.py` — 6 assertions repointées ; 3 verrous wording `xfail`.
- **[dette-tests · E]** `tests/test_audit_conformite.py` + `tests/test_audit_secu.py` — teardown `cache_clear`.
- **[dette-tests · docs]** `docs/TESTS.md` + ce rapport.

Aucun skip nu (skips conditionnels motivés ; 3 `xfail` documentés). **Aucun merge** (Vic merge en `--no-ff`).
