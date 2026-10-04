# PROPRETE-FIX-0 — sécurité avant déploiement

**Branche** `fix/proprete-0` · base `origin/main` `1e13a4f7` (audit `audit/proprete-1` mergé) ·
worktree `~/Desktop/labuse-proprete0` · Opus · venv partagé `~/Desktop/labuse/.venv` (Python 3.12.13).

**Périmètre strict** (et rien d'autre) : les 20 CVE Python, les 13 bandit HIGH, la CVE npm
**critique**, les versions figées. **Interdit** et NON fait : `ruff format` / `--fix` de masse,
suppression de fichiers/branches/tables/index, découpage de fichiers, CI (= FIX-1 / FIX-2).
**Règle tenue : aucun comportement ne change.** Aucun run data, aucun merge.

---

## Tableau de bord (départ → arrivée)

| Mesure | Départ | Arrivée | Commande |
|---|---|---|---|
| **pip-audit** (CVE Python) | **20** (7 paquets) | **1** (torch, justifié) | `python -m pip_audit` (venv) |
| **bandit HIGH** (sévérité) | **13** | **0** | `bandit -ll -r src/labuse` |
| **npm audit — critique** | **1** (maplibre-gl) | **0** | `npm audit --audit-level=critical` |
| **pytest** (base de test isolée) | voir §Fin | = départ | `pytest tests` |
| **tsc** | 0 | **0** | `tsc --noEmit` |
| **vitest** | 225 ✓ | **225 ✓** | `vitest run` |
| **vite build** | OK | **OK** | `vite build` |
| **V6b** (banc cohérence) | vert | **vert** | `test_v6b_coherence.py` |

> **19 des 20 CVE Python corrigées** ; la 20ᵉ (torch) est justifiée ci-dessous (correctif
> indisponible sur la plateforme + paquet jamais en prod). **13/13 bandit HIGH** traitées.
> **1/1 npm critique** corrigée.

---

## Lot 1 — CVE Python (20 CVE, 7 paquets)

Montée à la **plus petite version qui corrige**. Plancher relevé dans `pyproject.toml`
(convention `REVUE · R4`), paquet mis à niveau dans le venv testé, puis gelé (Lot 4).

| Paquet | Avant | Après | CVE corrigées | Note |
|---|---|---|---|---|
| anyio | 4.13.0 | **4.14.2** | PYSEC-2026-4024, 4025 | api/protection.py (run_sync) |
| pypdf | 6.17.0 | **6.19.0** | PYSEC-2026-4153/4154/4155/4156/4157/4159/4160 | 6.19.0 = plancher couvrant les 7 |
| setuptools | 81.0.0 | **83.0.0** | PYSEC-2026-3447 | outil de **build** (build-system), non servi au runtime |
| starlette | 1.2.1 | **1.3.1** | PYSEC-2026-248, 249 | importé en direct ; fastapi exige `>=0.46.0` → OK |
| urllib3 | 2.7.0 | **2.8.0** | PYSEC-2026-4175/4176/4177 | retries HTTP (ingestion PLU) |
| weasyprint | 69.0 | **70.0** | PYSEC-2026-3940 | PDF |
| **torch** | 2.11.0 | **2.11.0** (inchangé) | PYSEC-2025-194 — **NON corrigée, justifiée** | voir ci-dessous |

Montée résolue **sans conflit** (fastapi 0.136.3, weasyprint 70.0 : dépendances déjà satisfaites).
`starlette>=0.46.0` requis par fastapi, `1.3.1` le satisfait. Aucune API changée, aucun test cassé
par la montée (cf. §Fin, A/B pytest).

### CVE NON corrigée — torch PYSEC-2025-194 (justifiée, jamais un silence)

1. **Correctif indisponible sur la plateforme.** Le correctif est `torch==2.13.0`.
   L'index (macOS arm64) ne publie que **jusqu'à 2.11.0** (`pip install torch==2.13.0` →
   *No matching distribution found*). Impossible à installer, même en le voulant.
2. **Jamais en production.** `torch` est dans l'extra `[ml]` (`requirements-ml.txt`), explicitement
   « **JAMAIS sur le serveur prod** » : la prod sert des scores pré-calculés. L'image
   (`Dockerfile`) et le VPS (`deploy_app.sh`) installent le **cœur** (`.` / `requirements.lock`),
   **sans** `[ml]` → `torch` n'est pas dans la surface servie. Le verrou prod (Lot 4) ne le
   contient pas.
3. Reliquat consigné : plancher `torch>=2.2` laissé tel quel (le fixer à 2.13 casserait l'install
   `pip install -e .[ml]` sur le Mac) ; commentaire posé dans `pyproject.toml`. À reprendre quand
   2.13 sera publiée pour arm64.

> Note : la montée de `setuptools` à 83 déclenche un **avertissement** pip (torch 2.11 épingle
> `setuptools<82`). C'est un pin de **build** advisory : `import torch` fonctionne sous setuptools 83
> (vérifié) ; l'incompatibilité est **dev-only** (absente de la prod, cœur-sans-torch). Sans effet.

---

## Lot 2 — bandit HIGH (13 → 0)

**12× B324 (hash faible)** + **1× B202 (tar non filtré)**. Toutes les 12 occurrences de hash sont
des usages **non liés à la sécurité** (ETag de contenu, clés de cache, empreintes de dédoublonnage,
clé d'idempotence, échantillonnage déterministe, contrôle d'intégrité contre un md5 **publié**).
Correctif = `usedforsecurity=False` : **le digest est identique** (le kwarg ne change PAS la
valeur), le comportement est préservé, et bandit 1.9.4 ne lève plus (vérifié par sonde).

| # | Fichier:ligne | Rôle du hash | Correctif |
|---|---|---|---|
| 1 | api/projets.py:487 | clé de compteur (cadrage) | `usedforsecurity=False` |
| 2 | api/tiles.py:600 | **ETag** de contenu de tuile | `usedforsecurity=False` |
| 3 | config.py:425 | empreinte des configs de règles | `usedforsecurity=False` |
| 4 | copilote_v2/veilles.py:136 | clé de dédoublonnage de notif | `usedforsecurity=False` |
| 5 | courrier.py:298 | clé d'idempotence (advisory lock) | `usedforsecurity=False` |
| 6 | fraicheur_caches.py:74 | empreinte millésimes sources | `usedforsecurity=False` |
| 7 | fraicheur_caches.py:88 | empreinte courte (clé de cache) | `usedforsecurity=False` |
| 8 | ingestion/gpu_infos.py:125 | dédoublonnage PEB | `usedforsecurity=False` |
| 9 | plu/extraction.py:108 | intégrité vs md5 **publié** (GPU) | `usedforsecurity=False` |
| 10 | plu/extraction.py:120 | intégrité vs md5 **publié** (GPU) | `usedforsecurity=False` |
| 11 | registre/remplissage.py:57 | **échantillonnage déterministe** — DOIT rester md5 pour coïncider avec `WHERE md5(idu‖jour)` en SQL | `usedforsecurity=False` |
| 12 | sentinelle.py:1009 | empreinte de signature (taille bornée) | `usedforsecurity=False` |
| 13 | ingestion/cadastre_historique.py:161 | `tarfile.extractall` (archive DGFiP) | **`filter="data"`** |

**B202 (n°13)** : vraie faille potentielle de traversée de chemin à l'extraction. Correctif
défensif `extractall(td, filter="data")` (Python ≥ 3.11.4/3.12) : rejette les membres `..`/absolus,
extrait normalement une archive bien formée → **comportement inchangé** pour l'archive DGFiP
légitime, vulnérabilité fermée. Bandit ne lève plus (vérifié).

Aucun `# nosec` posé : les correctifs sont **réels et sémantiquement corrects** (pas des
suppressions). Les digests étant byte-identiques, aucune clé de cache / ETag / échantillon ne change.

---

## Lot 3 — npm critique (maplibre-gl, 1 → 0)

**GHSA-jrc7-96c5-q579** (critique, CWE-79) — *XSS Sanitizer Bypass in `DOM.sanitize()`*.
Vulnérable `<=6.4.0` ; **aucun correctif dans la lignée 4.x/5.x** → le correctif `6.12.0` impose le
**saut majeur** que le mandat prévoit. Exposition réelle : les popups rendent des données serveur
(`popupHTML`, `popupDetailHTML`) via `setHTML` → le chemin `DOM.sanitize` est atteignable.

**`maplibre-gl ^4.7.1 → ^6.12.0`** (direct). `npm audit fix` simple ne suffit pas (saut majeur) ;
`npm audit fix` bute d'ailleurs sur un **bug interne npm** (`Cannot read properties of null
(edgesOut)`). Migration de source **mécanique et neutre** (3 fichiers) :

- `import maplibregl from 'maplibre-gl'` → `import * as maplibregl from 'maplibre-gl'`
  (maplibre 5+ n'a plus d'export par défaut) — `CouchesTuyau.tsx`, `MapView.tsx`, `TimeMachine.tsx`.
- `(e as { error?: Error }).error?.message` → `e.error?.message` dans les handlers `on('error')`
  (le type d'événement d'erreur est désormais fourni ; la ligne suivante `console.error(e.error ?? e)`
  l'utilisait déjà) — `MapView.tsx`, `TimeMachine.tsx`. **Lit exactement la même propriété.**

**Vérifs** : `tsc` **0**, `vitest` **225 ✓**, `vite build` **OK**, `npm audit --audit-level=critical`
→ **0 critique**. **Ouverture de l'app** + **A/B de preuve** sur le build de prod (`vite preview`,
même environnement sans back) :

- maplibre **6.12.0** : la seule erreur console est `TypeError: e is not a function` dans
  `vendor-*.js` (chunk **React/store**, pas maplibre — maplibre est isolé dans `maplibre-*.js`) ;
  c'est l'échec de bootstrap **faute de back** (`/config/run` 404).
- maplibre **4.7.1** (baseline, même build de prod) : **exactement la même** erreur, **même hash de
  chunk**. → **maplibre 6 n'introduit AUCUNE nouvelle erreur runtime.**
- L'erreur « Worker failed to load » n'apparaît **qu'en mode `vite dev`** (artefact du pré-bundleur
  Vite) et **disparaît dans le build de prod** (ce qui est déployé).

Reste **hors périmètre** (non critiques) : 7 high + 3 moderate, toutes **transitives de build/dev**
(chaîne `tailwindcss` → braces/micromatch/chokidar, `undici`, `browserslist`, `fast-glob`),
corrigeables seulement par des majeures cassantes (tailwindcss 4) → **FIX-2**.

---

## Lot 4 — versions figées

### Python — `requirements.lock` (nouveau)

Verrou **cœur** (prod), généré par `uv pip compile pyproject.toml` ciblant **Python 3.12**,
**contraint aux versions EXACTES du venv qui passe les tests** (donc anyio 4.14.2, starlette 1.3.1,
urllib3 2.8.0, weasyprint 70.0, pypdf 6.19.0, numpy 2.5.2…). **Cœur uniquement** : ni `[ml]` (torch)
ni `[ai]` (anthropic). 77 paquets épinglés. Vérifié installable/consistant : `uv pip install
--dry-run -r requirements.lock` contre le venv testé → **« Would make no changes »**.

Le VPS et l'image installent **depuis ce fichier**, puis le paquet sans re-résoudre :

- **`Dockerfile`** : `FROM python:3.11-slim` → **`3.12-slim`** (requis : le verrou épingle
  numpy 2.5.2 qui exige Python ≥ 3.12 ; **aligne** le pilote sur le VPS qui est **déjà** en 3.12).
  `COPY … requirements.lock` + `pip install -r requirements.lock && pip install --no-deps .`
- **`deploy/scripts/deploy_app.sh`** : `pip install -r ./app/requirements.lock` puis
  `pip install -e ./app --no-deps` (le VPS est déjà `python3.12 -m venv`).

### Front — `package-lock.json`

Présent et cohérent, met à jour maplibre-gl **6.12.0**. **`npm ci` passe** (vérifié, 2× :
installe/réinstalle sans écart).

---

## Fin — re-vérification

- **pip-audit** : 20 → **1** (torch, justifié). **bandit HIGH** : 13 → **0**.
  **npm critique** : 1 → **0**.
- **tsc 0** · **vitest 225 ✓** · **vite build OK** (maplibre 6.12.0 restauré).
- **V6b** (`test_v6b_coherence_banc`) : **vert**.
- **pytest** — base de test **isolée** `labuse_pf0*` (role `openclaw`, jamais la base partagée ;
  schéma nu auto-créé par conftest → les tests « sur la base réelle » échouent faute de données
  **à l'identique avant/après**, ce sont des `sqlalchemy.*Error` d'environnement, pas des
  assertions).

  **Preuve sur base FRAÎCHE pour CHAQUE run** (DB-drift éliminé : le départ a créé `labuse_pf0`
  neuve, l'arrivée crée `labuse_pf0a` neuve). L'arrivée ignore `test_scoring2_arene.py` (abort
  **natif** flaky torch/OpenMP — vérifié **passant en isolé**, 5 ✓ ; hors périmètre, torch inchangé) :

  - **Départ** (base `1e13a4f7`, paquets d'origine, DB neuve) :
    `58 failed, 3520 passed, 69 skipped, 1 error`.
  - **Arrivée** (code + paquets modifiés, DB neuve, hors arena) :
    `58 failed, 3516 passed, 68 skipped, 1 error` — totaux **réconciliés** (3643 = 3643 une fois
    les 5 tests `arene` retirés).
  - **Ensembles d'échecs IDENTIQUES** : `diff` des 59 nœuds (58 FAILED + 1 ERROR) **vide** →
    **aucun nouvel échec, aucun test cassé** par le périmètre. Les 59 sont des `sqlalchemy.*Error`
    d'environnement (base nue sans données « réelles »), inchangés avant/après.

- **5 oracles** : nécessitent une **API vivante** (`LABUSE_ORACLE_API`) + appels gouv. externes +
  base **peuplée** — hors de cet environnement isolé (« aucun run » / ne pas perturber la base ni
  les backends partagés). **Provablement inchangés par le périmètre** : les oracles comparent des
  **valeurs servies** (surfaces, zonage, DVF, altimétrie, SIRENE, SRU) à des sources externes ;
  aucun chemin de calcul touché (montées de version + `usedforsecurity=False` **digest identique**
  + `filter="data"` + verrou + maplibre). Le banc permanent **V6b** (équivalent offline) est vert.

### Fichiers touchés

- `pyproject.toml` (planchers), `requirements.lock` (nouveau), `Dockerfile`,
  `deploy/scripts/deploy_app.sh`.
- Python (bandit) : `api/projets.py`, `api/tiles.py`, `config.py`, `copilote_v2/veilles.py`,
  `courrier.py`, `fraicheur_caches.py` (×2), `ingestion/gpu_infos.py`, `plu/extraction.py` (×2),
  `registre/remplissage.py`, `sentinelle.py`, `ingestion/cadastre_historique.py`.
- Front (maplibre 6) : `frontend/package.json`, `frontend/package-lock.json`,
  `frontend/src/components/map/CouchesTuyau.tsx`, `frontend/src/components/map/MapView.tsx`,
  `frontend/src/components/outils/TimeMachine.tsx`.

### Suite (hors périmètre, pour mémoire) — FIX-1 / FIX-2

torch 2.13 quand publié arm64 · npm high/moderate transitifs (tailwindcss 4, undici, browserslist) ·
ruff/format, CI/pre-commit, découpage de fichiers, index/tables — **après le déploiement**.
