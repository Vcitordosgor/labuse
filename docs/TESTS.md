# Lancer la suite de tests

Référence opérationnelle de la suite `tests/` : commande, extras, variables, skips connus.
Assainissement : mandat DETTE-REPO (cf. `docs/mandats/DETTE_TESTS_RAPPORT.md`).

## Commande

```bash
export LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse
LABUSE_DEV_MODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q
```

- Base **dédiée** `labuse_test` auto-créée (jamais la base applicative — cf. `tests/conftest.py`).
  `conftest` lit `LABUSE_DATABASE_URL` **avant** le `.env` → l'exporter dans la commande.
- Attendu (poste correctement configuré) : **suite verte**, 19 skips motivés, **3 xfail** (verrous de
  wording produit parqués, cf. plus bas). Aucun `failed`, aucun `error`.

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

## xfail parqués (arbitrage produit en attente)

3 tests de `test_front_reliquats.py` (`test_r3_tooltip_multiplicateur_de_rang`,
`test_r3_tooltip_jauge_completude`, `test_r3_matrice_non_thermique`) sont `xfail(strict=False)` :
ils **verrouillent une formulation produit** qui a été reformulée dans le front. Les mettre à jour
reviendrait à ratifier la reformulation en silence → **arbitrage Vic requis** (deltas exacts dans
`docs/mandats/DETTE_TESTS_RAPPORT.md §A.2`). Ils repassent `XPASS` si le wording d'origine revient.

## Golden & invariant des tiers

Hors suite pytest, garde-fou du run servi :

```bash
LABUSE_API_BASE=http://127.0.0.1:8010 PYTHONPATH=src .venv/bin/python qa/golden_check.py   # 116/116
```

Nécessite l'API locale démarrée sur la base applicative. Invariant des tiers du run servi
`q_v7_defisc` (vérifiable en base sans l'API) : **120 / 1031 / 3587 / 72980 / 353945** au bit près
(`parcel_p_score_v2`, run le plus récent).
</content>
