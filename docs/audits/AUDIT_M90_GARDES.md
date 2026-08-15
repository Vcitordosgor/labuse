# AUDIT M90 — Gardes-fous : ne jamais confondre panne et régression

**Mandat M90 · Phase 1 (mesure) · branche `audit/m90-gardes-env` · NON mergé**

Doctrine : *un garde qui échoue pour une raison d'environnement doit le dire* ·
*les retards d'environnement restent séparés du bit de santé du process* ·
*mesurer avant d'affirmer* · *on ne desserre jamais un seuil parce qu'il sonne*.

Pour chaque garde : **(1)** modes d'échec d'environnement possibles · **(2)**
distingue-t-il aujourd'hui la panne de l'écart métier ? · **(3)** ce que
l'opérateur voit RÉELLEMENT (message actuel, pas celui qu'on voudrait).

---

## Résumé exécutif

Le motif du mandat est confirmé **empiriquement** sur la suite pytest :
`20 failed, 1528 passed, 31 skipped` — et ces 20 rouges mélangent **au moins
trois causes-racines indiscernables** sous un même « FAILED » :

| Cause-racine | Nature | Tests concernés (mesuré) |
|---|---|---|
| `parcel_anc` absente de la base de test | **panne d'env** | ~10 : test_api (5), test_verdict_effectif (3), test_prospection (1), test_flash_report (1) |
| Doubles de test périmés (`_Ctx` sans attribut, `session=None`) | **dette de test** (ni panne ni régression) | ~6 : test_phase2_layers (3), test_residuel (3+) |
| Vrais écarts métier | **régression / constat réel** | ~4 : test_deps_declared (imports non déclarés), test_faisabilite (verdict wording), test_front_reliquats |

Personne devant « 20 failed » ne peut dire lequel est une panne et lequel est
une régression. **C'est exactement la classe que ce mandat traite.**

**Bonne nouvelle mesurée** : la majorité des gardes du dépôt suivent DÉJÀ la
doctrine (troisième état explicite). Les trous sont **concentrés** sur 3-4 points.

---

## Inventaire des gardes

### A. `qa/golden_check.py` — le golden API (garde central)

| | |
|---|---|
| **Modes d'échec env** | API injoignable (connexion refusée / mauvais port) · quota 429 sur les GET par parcelle · base PostgreSQL injoignable · run cascade introuvable |
| **Distingue aujourd'hui ?** | **PARTIELLEMENT.** ✅ API injoignable : préflight `_api_reachable()` (M81) → code 2 « API INJOIGNABLE … PAS un écart métier ». ✅ Run introuvable : `sys.exit(2)` « refus de retomber sur un run mort ». ❌ **429 par parcelle** : après le préflight (qui ne teste QUE `/healthz`, une requête), chaque GET fiche/v2 peut prendre un 429 → `compare_entry` voit `{"erreur":"HTTP 429"}` ≠ données → **compté comme FAIL métier** (incident M87 ET M89). ❌ **Défaut de port** : `API_BASE` défaut = `http://127.0.0.1:8010` alors que l'app tourne sur `:8000` — piège historique (33 faux FAIL / 6 jours). Aujourd'hui le préflight l'attrape (« INJOIGNABLE à :8010 ») mais le défaut reste un piège armé. |
| **Message réel** | 429 : `FAIL {idu} — N écart(s)` + liste de champs `attendu=… obtenu='HTTP 429'` → **ressemble à une régression massive**. Injoignable : message clair (bon). |

### B. `src/labuse/bascule_gardes.py` — 13 gardes de bascule/service

`check_run_absent`, `check_disque`, `ensure_backups`, `verify_completude`,
`check_peremption`, `check_golden_regenere`, `check_fraicheur`,
`check_coherence_idurba`, `check_coherence_renouvellement`,
`check_peremption_tuiles`, `check_sources_declarees`, `check_unicite_pm`,
`check_coherence_tables_run_scopees`.

| | |
|---|---|
| **Modes d'échec env** | Table run-scopée absente · base injoignable · disque plein · run de référence vide (rien à dimensionner) |
| **Distingue aujourd'hui ?** | ✅ **Très bien, dans l'ensemble.** Troisième état explicite partout : `ABSENTE` / `PÉRIMÉE` / `MÉLANGÉE` (via `to_regclass`), horizon `inconnu`, cadence `non bornable`, et surtout `check_disque` lève « **GARDE DISQUE INOPÉRANTE** … refus de démarrer plutôt qu'un OK aveugle » quand elle ne peut pas mesurer. Les non-bloquantes disent « NON bloquant, à voir ». ❌ **Un seul trou** : si la **base PostgreSQL elle-même est injoignable**, `engine()`/`session_scope` lèvent une `OperationalError` **générique non nommée** — pas de « base injoignable = environnement » ; le garde crashe comme s'il avait trouvé un problème métier. |
| **Message réel** | Tables absentes/périmées : nommé, distinct, non bloquant (bon). Base down : traceback `psycopg.OperationalError` brut (mauvais). |

### C. `src/labuse/ingestion/fraicheur.py` (M84) — fraîcheur live

| | |
|---|---|
| **Modes d'échec env** | Source amont muette (retard d'ingestion) · service tiers injoignable (sonde georisques) · horizon amont NULL |
| **Distingue aujourd'hui ?** | ✅ **Modèle du bon comportement.** Statuts `en_retard` / `a_jour` / non bornable ; retard amont **séparé du bit `ok`** (feedback M84 gravé : « retard amont chronique ≠ dégrade uptime »). Sonde georisques injoignable → note `injoignable ({type})`, jamais un FAIL. Seuil = 2× cadence, jamais desserré. |
| **Message réel** | `⚠ FRAÎCHEUR — « dpe » : … Source en retard — NON bloquant, mais à voir` + chip Sources. Clair et honnête. |

### D. `marche_service.garde_fou_signal` (MANDAT_DVF-B) — garde-fou 2×

| | |
|---|---|
| **Modes d'échec env** | Terme manquant (pas de référence DVF, effectif insuffisant) |
| **Distingue aujourd'hui ?** | ✅ **L'exemple canonique.** Retourne `{declenche, mesurable, note}` : un écart **non mesurable** (référence absente / effectif sous le seuil) → `mesurable:False`, ne se déclenche pas, **le dit** (« écart non mesurable ») au lieu de se taire ou de crier. Troisième état natif. |
| **Message réel** | « Écart à la référence de secteur non mesurable (pas de référence DVF fiable) ». Exact. |

### E. Suite `pytest` + `tests/conftest.py`

| | |
|---|---|
| **Modes d'échec env** | Base de test injoignable · PostGIS absent · **table optionnelle absente du fixture** (`parcel_anc`, `anc_maille_taux`) · module Python optionnel · symbole d'import supprimé |
| **Distingue aujourd'hui ?** | ✅ **Bien pour la plupart** : `conftest` SKIP proprement si base/PostGIS injoignable (« Base de test indisponible ») ; ~31 skips propres via `pytest.skip` / `importorskip` / `skipif` (données commune absentes, `pg_dump` absent, `frontend/dist`, API live, `weasyprint`/`pypdf`). ❌ **Trou `parcel_anc`** : la table n'est PAS créée au session-setup du conftest (contrairement à `parcel_terrain`, `rnic_coproprietes`, etc.). Les routes fiche appellent `anc_service.statut_anc` / `flash/data.py` qui font `SELECT zone_anc FROM parcel_anc` → **500 → le test assert sur la route rougit** avec `ProgrammingError: relation "parcel_anc" does not exist`. **Une panne d'env déguisée en régression SQL.** ❌ **`test_pdf_premium.py`** : `ImportError: cannot import name 'RUN' from labuse.api.pdf_premium` → **interrompt la COLLECTE de toute la suite** (erreur, pas skip). Symbole `RUN` supprimé du module, test jamais mis à jour. |
| **Message réel** | `ProgrammingError: relation "parcel_anc" does not exist` (ressemble à une migration cassée) · `ERROR … Interrupted: 1 error during collection` (bloque tout). |

### F. `tests/test_non_contradiction.py` (M73)

| | |
|---|---|
| **Modes d'échec env** | API live `:8000` injoignable · fiche indisponible (≠200) · `weasyprint`/`pypdf` absent |
| **Distingue aujourd'hui ?** | ✅ **Bon.** SKIP propre : `pytest.skip("API live {BASE} injoignable : {exc}")`, `skip("{idu} : fiche indisponible ({status})")`, `importorskip`. Les rouges qu'il produit sont de vrais écarts (libellé technique, aléa incohérent, bloc ANC/réhab absent). ⚠ Note mineure : `RUN="q_v8_calibre"` en dur alors que le servi est `q_v9_m81` — non bloquant (référence non comparée), mais constant périmé. |
| **Message réel** | Skip explicite si env absent ; AssertionError nommée si vrai écart. |

### G. `tests/test_deps_declared.py` — imports tiers déclarés

| | |
|---|---|
| **Distingue ?** | N/A env — c'est un garde d'HYGIÈNE qui trouve un **vrai** manque (`PIL/fitz/requests/urllib3` non déclarés dans `pyproject.toml`). Rouge légitime, PAS une panne. À traiter hors M90 (dette de déclaration), mais **il pollue le compte de rouges** et brouille la lecture. |

### H. `qa/*.mjs` (Playwright e2e) — dont `qa/e2e_429.mjs`

| | |
|---|---|
| **Distingue ?** | Manuels (`node qa/…`, app requise sur `:8000`). `e2e_429.mjs` teste justement que l'UX d'un 429 affiche « Trop de requêtes », pas « serveur périmé » — **côté produit, la distinction 429≠panne existe déjà**. Hors chaîne CI automatique ; env-fragiles mais lancés à la main en connaissance de cause. |

### I. `/healthz` vs `/readyz` (endpoints)

| | |
|---|---|
| **Distingue ?** | ✅ **Séparation propre du bit de process et de l'état données** : `/healthz` = « le PROCESS répond, zéro accès DB » ; `/readyz`/`/demo-status` = état des données. La doctrine « bit de santé séparé du résultat métier » est déjà appliquée ici. |

### J. Vérification de branche (doctrine `feedback_verif_branche_avant_commit`)

| | |
|---|---|
| **Distingue ?** | Garde **humain/procédural**, pas du code (`git branch --show-current` avant chaque commit). Hors périmètre logiciel — rien à traiter, sauf à vouloir l'outiller (hook). |

---

## Les trous (là où panne et régression se confondent)

Classés par gravité / récurrence mesurée :

1. **golden — 429 par parcelle compté en FAIL** (incident M87 ET M89, 2×). Le préflight ne couvre qu'`/healthz`. Un 429 sur un GET fiche/v2 se lit comme une régression massive de champs. **Priorité haute** (récurrent, déjà mordu deux fois).
2. **pytest — `parcel_anc` absente du fixture → ~10 rouges `ProgrammingError`** lus comme une migration/régression SQL. **Priorité haute** (10 tests, cité nommément dans le mandat).
3. **pytest — `test_pdf_premium.py` `ImportError: RUN`** interrompt la COLLECTE entière (erreur, pas skip). **Priorité haute** (masque toute la suite, empêche même de VOIR les autres états).
4. **golden — défaut de port `:8010`** (l'app tourne `:8000`). Piège armé ; atténué par le préflight mais le défaut devrait pointer le bon port ou l'exiger explicitement. **Priorité moyenne.**
5. **bascule_gardes — base PostgreSQL injoignable → `OperationalError` générique** non nommée « environnement ». **Priorité moyenne** (peu fréquent mais non distingué).

## Ce qui est DÉJÀ conforme (à ne pas toucher — ne pas desserrer)

- `garde_fou_signal` (mesurable / non mesurable) — modèle.
- `fraicheur` M84 (en_retard / a_jour / non-bornable ; retard séparé du bit ok ; sonde « injoignable »).
- `bascule_gardes` : `ABSENTE`/`PÉRIMÉE`/`MÉLANGÉE`, « GARDE DISQUE INOPÉRANTE », « NON bloquant, à voir ».
- golden : préflight `_api_reachable` (M81), refus du run mort.
- `/healthz` vs `/readyz` : bit process séparé de l'état données.
- ~31 skips propres de la suite (données commune, modules optionnels, fichiers, API live).

## Distinctions dans les DEUX sens (rappel doctrine)

Une panne ne doit pas passer pour une régression **ET** une régression ne doit
pas se déguiser en panne. Concrètement pour Phase 2 :
- Le traitement `parcel_anc` doit rendre « indéterminé » **uniquement** quand la
  table est absente — jamais avaler un vrai `ProgrammingError` sur une colonne
  renommée (ça, c'est une régression).
- « Indéterminé » n'est pas « OK » : il ne desserre aucun seuil, ne valide rien,
  ne fait pas passer un tier. Il dit *on n'a pas pu mesurer*.

---

## STOP — arbitrage du périmètre (Vic)

Le mandat prévoit qu'*« il est possible que seuls quelques gardes méritent le
traitement »*. Les 5 trous ci-dessus sont candidats ; les tests périmés (`_Ctx`,
`session=None`) et `test_deps_declared` sont de la **dette de test/hygiène
séparée**, pas la classe « panne vs régression » — proposés HORS périmètre M90.

Question ouverte pour Phase 2 (voir arbitrage joint) : quels trous traiter, et
pour `parcel_anc` — **fixture** (créer la table vide au session-setup, comme
`parcel_terrain`) ou **skipif** (le test déclare son prérequis et sort en
« indéterminé ») ?

---

## Phase 2 — traitement (arbitrage Vic)

Périmètre retenu : golden (429 + port) · test_pdf_premium · bascule base injoignable
· parcel_anc (« les deux selon le cas »). Hors périmètre confirmé : tests périmés
(`_Ctx`, `session=None`) et imports non déclarés (dette de test/hygiène séparée).

1. **golden 429 → INDÉTERMINÉ** — `_env_error()` classe l'échec d'un GET par parcelle :
   429 = « quota dépassé », erreur de connexion = « injoignable en cours de run » →
   la parcelle est **INDÉTERMINÉE**, jamais FAIL. Un 4xx/5xx *propre* reste métier (une
   régression ne se déguise pas en panne). Code retour **2** (non concluant) s'il n'y a
   que des indéterminées — ni 0 (OK) ni 1 (FAIL). *Vérifié* : sous RPM=3, 4 parcelles
   INDÉTERMINÉ, 0 FAIL, code 2.
2. **golden défaut de port** — défaut `:8010` → `:8000` (le port réel de l'uvicorn local).
   La cible distante passe toujours par un env/`--base-url` explicite. *Vérifié* : golden
   sans `--base-url` → 119/119.
3. **test_pdf_premium** — `import RUN` retiré (symbole supprimé quand le footer a migré vers
   `pied_de_page_pdf` : régression d'origine ÉTEINTE) ; sous-test mort supprimé. La collecte
   n'est plus interrompue ; le test de rendu (footer compris) conserve la protection utile.
4. **parcel_anc** — garde-source AU POINT UNIQUE `anc_service.statut_anc` + `couverture_anc`
   (`to_regclass('parcel_anc')`) : table absente → « Absent » (un état) / couverture 0, jamais
   un 500. **Pas de fixture** : le flash omet déjà l'ANC via `avail` et `test_collect_parcelle_pauvre`
   vérifie cette omission — la matérialiser la casserait (mesuré). L'absence d'une *colonne* reste
   levée (régression de schéma non masquée). Le même garde a été appliqué à `parkings_aper`
   (`viabilisation_build`, gisement M75), **même classe démasquée** en corrigeant parcel_anc.
5. **bascule base injoignable** — `BaseInjoignableError` + points d'accès `_connect()`/`_scope()`
   dans `bascule_gardes` : un `OperationalError` (PostgreSQL down) devient « BASE INJOIGNABLE …
   panne d'environnement, PAS un écart métier ». *Vérifié* : sur une URL morte, `check_*` lèvent
   la cause nommée ; sur la base réelle, inchangés.

### Résultat mesuré (avant → après)

| | Avant M90 | Après M90 |
|---|---|---|
| Collecte pytest | **interrompue** (ImportError test_pdf_premium) | complète |
| Suite | 20 failed, 1528 passed | **13 failed, 1536 passed** |
| Rouges de classe ENV (parcel_anc/parkings_aper) | ~7 (ProgrammingError, lus régression) | **0** (dégradés en « Absent »/None) |
| golden 429 | FAIL (régression apparente) | INDÉTERMINÉ (code 2) |
| golden mauvais port | 33 faux FAIL possibles | défaut correct + préflight |
| bascule base down | OperationalError brut | BaseInjoignableError nommé |

Les **13 rouges restants sont TOUS non-env** et désormais HONNÊTEMENT attribuables à
leur vraie cause (ils étaient masqués derrière les ProgrammingError) : données seedées
manquantes (test_api ×2), doubles de test périmés (test_phase2_layers ×3, test_residuel
×4), drift M73-D `mode_b` (test_flash_report), findings réels (test_deps_declared imports,
test_faisabilite verdict, test_front_reliquats). **C'est la thèse du mandat réalisée : en
retirant la panne, la vraie nature de chaque échec redevient lisible.** Ces 13 relèvent de
la dette de test / des findings, hors classe « panne vs régression ».

### Phase 3 — vérification
- Chaque mode d'échec d'environnement provoqué dit la BONNE cause (429, port, table absente,
  base injoignable) — jamais un FAIL générique. ✓
- Golden **119/119** en conditions normales, code 0. ✓
- Aucun seuil métier desserré : seuls messages, statuts et gardes de table/connexion ont changé
  (TOLERANCES golden, `seuil_facteur` fraîcheur, `SEUIL_BLOCAGE_JOURS`, seuil APER 1 500 m² :
  inchangés). « Indéterminé » n'est jamais devenu « OK » (code 2 distinct, état « Absent » distinct). ✓
