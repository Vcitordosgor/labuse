# Lancer la suite de tests

Référence opérationnelle de la suite `tests/` : commande, extras, variables, skips connus.
Assainissement : mandat DETTE-REPO (cf. `docs/mandats/DETTE_TESTS_RAPPORT.md`).

## Commande

```bash
LABUSE_DEV_MODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q
```

- Base **dédiée** `labuse_test` auto-créée (jamais la base applicative — cf. `tests/conftest.py`).
- **M31 PC1** : `conftest` **charge le `.env`** (via `python-dotenv`) avant de dériver l'URL de test
  → plus besoin d'exporter `LABUSE_DATABASE_URL` à la main. Avant ce correctif, sans l'export, les
  tests qui ouvrent `session_scope()` directement (facturation, audit_stripe, comptes, fiche_ask,
  alertes) **erroraient** (`role "labuse" does not exist`) au lieu de tourner, car le repli codé
  `labuse:labuse@localhost` ne matche pas un poste à auth peer (`openclaw`). Un `.env` valide (celui
  qui fait déjà tourner l'app) suffit désormais. Un `LABUSE_DATABASE_URL` exporté reste prioritaire (CI).
- Attendu (poste correctement configuré) : **suite verte — 1312 passed, 22 skipped, 0 failed, 0 error**,
  SANS aucune var d'env. Voir aussi `qa/m31/M31_RAPPORT.md`.

### Run servi — POINT DE VÉRITÉ UNIQUE (M31, arbitrage Vic)

Le run servi vit dans **`config/served_run.txt`** (fichier versionné, 1ʳᵉ ligne non commentée). Les
trois surfaces le lisent : backend (`Q_A_RUN_LABEL`), bundle front (`vite.config.ts` → `VITE_RUN_LABEL`),
tuiles (`build-mvt` → `mvt_meta.run_label`). `test_run_serving_coherence.py` vérifie qu'elles == le
fichier. **Pour basculer** : changer la ligne du fichier, puis `npm run build` + `labuse build-mvt`.
`LABUSE_SERVED_RUN` reste un **override de DEV** (loggé WARNING au démarrage) — jamais requis en prod.

## Extras Python requis

`pip install -e ".[dev]"` + `".[ml]"` + `".[ai]"` (venv **Python 3.12**, cf. `README_DEV.md`) :

| Extra | Apporte | Sans lui |
|---|---|---|
| `[dev]` | pytest, httpx… | la suite ne tourne pas |
| `[ml]` | pandas, torch, scikit-learn | tests P (`test_p_v2_*`, arène) cassent |
| `[ai]` | `anthropic` | l'interpréteur Copilote tombe en `ia_indisponible` |

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `LABUSE_DATABASE_URL` | base applicative ; la base de test en dérive (`…/labuse_test`) | `…labuse:labuse@…/labuse` |
| `LABUSE_TEST_DATABASE_URL` | force une base de test explicite | dérivée de l'URL app |
| `LABUSE_DEV_MODE=1` | **exempte rate-limit + quota** (audit/crawl local) | absent |
| `PROJ_DATA` | répertoire des données PROJ de pyproj (voir ci-dessous) | auto-découvert |

> ⚠ **`LABUSE_DEV_MODE=1` désactive les gardes rate-limit/quota.** Les tests qui vérifient CES
> gardes (`test_protection.py`) neutralisent explicitement le flag (`monkeypatch.delenv`). Ne pas
> retirer cette neutralisation : sans elle, la garde ne peut pas être testée sous le mode dev mandaté.

## Données PROJ (pyproj) — ordre de résolution

Certains wheels `pyproj` (build source sur macOS 13, cf. `README_DEV.md`) **n'embarquent aucun
`proj.db`**. Sans lui, toute reprojection (4326↔2975) casse → ~69 tests en erreur au setup.
`tests/conftest.py::_ensure_proj_data()` résout dans cet ordre, **au démarrage de la collecte** :

1. **`PROJ_DATA`** déjà posé et pointant un dossier avec `proj.db` → respecté tel quel.
2. Données déjà trouvables par pyproj (wheel avec `proj.db` embarqué) → rien à faire.
3. **Auto-découverte** d'un `proj.db` (env courant `sys.prefix`, wheel pyproj, `/opt/homebrew`,
   `/usr/local`, `/usr/share`, envs conda `miniforge3/miniconda3/anaconda3/mambaforge`).
4. **Aucun trouvé → ÉCHEC BRUYANT** (`RuntimeError` actionnable listant les emplacements cherchés).
   Jamais un skip silencieux de 69 tests : une machine mal configurée doit le savoir.

Correctif si l'échec se déclenche, au choix : poser `PROJ_DATA` vers un dossier contenant `proj.db`
(ex. l'env conda de PostGIS), ou `pip install --force-reinstall --no-cache-dir pyproj`.

> ⚠ **Bascule prod/VPS** : si le serveur porte le même wheel `pyproj` sans `proj.db`, il aura le
> **même défaut** (reprojection cassée au boot). Le kit VPS doit garantir `proj.db` (PROJ système)
> **ou** `PROJ_DATA`. Point consigné au rapport de mandat (§C).

## Skips connus (conditionnels, motivés)

Tous les skips portent une condition + un motif (jamais un `skip` nu). Les 19 skips par défaut :

| Motif | Nombre | Condition |
|---|---|---|
| `base applicative indisponible` — QA Saint-Paul | 12 | base *applicative* (pas la base de test) éteinte |
| `LABUSE_QA_TARGET non défini` — QA distante (geste M7) | 1 | cible VPS non fournie |
| `frontend/dist absent` | 1 | front non construit sur la machine |
| `pg_dump 16 < serveur PostgreSQL 18` | 1 | incompatibilité de version de dump (env local) |
| `pas de parcelles en base de test` / Flash non testable | 3 | base de test sans jeu de données |
| `module Flash / run de référence` | 1 | couvert par la QA merge |

## Verrous de wording produit (arbitrage clos)

3 tests de `test_front_reliquats.py` (tooltips ×N / jauge complétude, libellés du tier P) verrouillent
une **formulation produit servie**. Arbitrage Vic 07/2026 : les wordings actuels sont **validés** (tests
remis à jour dessus, plus de `xfail`). Toute reformulation future de ces libellés cassera ces tests **par
conception** — c'est le garde-fou : un changement de wording servi passe par une décision, pas en silence.
Détails dans `docs/mandats/DETTE_TESTS_RAPPORT.md §A.2`.

## Golden & invariant des tiers

Hors suite pytest, garde-fou du run servi :

```bash
LABUSE_API_BASE=http://127.0.0.1:8010 PYTHONPATH=src .venv/bin/python qa/golden_check.py   # 116/116
```

Nécessite l'API locale démarrée sur la base applicative. Invariant des tiers du run servi
`q_v7_defisc` (vérifiable en base sans l'API) : **120 / 1031 / 3587 / 72980 / 353945** au bit près
(`parcel_p_score_v2`, run le plus récent).

> ⚠ **PIÈGE RATE-LIMIT — des FAIL golden NON DÉTERMINISTES qui ne sont PAS une régression.**
> `golden_check.py` fait **116 parcelles × 2 GET = 232 requêtes** à l'API, contre un quota
> applicatif de **60 req/min** (`api/protection.py`). Au-delà, l'API renvoie **HTTP 429 « Trop de
> requêtes »** et les fiches concernées reviennent `obtenu='<absent>'` sur TOUS leurs champs
> (`api.fiche.*`) → FAIL comptés comme « incohérence base↔API (runtime) ». Le nombre **fluctue
> d'un run à l'autre** (0, 10, 32…) selon le quota résiduel — vécu le 29/07, à l'origine d'une
> fausse alerte de régression après un rollback pourtant complet.
> **Reconnaître le piège** : un FAIL rate-limit a `obtenu='<absent>'` sur *tout* le bloc `api.fiche`
> (jamais un désaccord de valeur), varie entre exécutions, et **la face DB reste 116/116** (les FAIL
> `db.*`/`tier_v2` sont, eux, de vrais désaccords de données — déterministes).
> **Contre-mesures** : (a) lancer l'API en **dev mode** (`LABUSE_DEV_MODE=1`) qui exempte
> rate-limit + quota ; ou (b) espacer les requêtes (le golden pourrait throttler à < 60/min) ; ou
> (c) allowlister l'IP QA (`qa_allowlist`, voie M7). Pour prouver un rollback/une bascule, se fier
> à la **face DB du golden** (déterministe), pas au compte brut PASS/FAIL bruité par l'API.
</content>
