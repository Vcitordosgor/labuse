# VITESSE-FICHE-2 — fiche parcelle rapide (cold path)

**Branche** `fix/vitesse-fiche-2` (rebasée sur `origin/main` = `e60bf578`, VITESSE-PROD-1 + TUILES-TX-1), ports 8830/6030, **pas de merge**.
**Règle tenue** : mêmes chiffres, même affichage — **md5 du payload `/parcels/{idu}` identique sur 20 parcelles, avant/après** (`scripts/vfiche2_md5.py`).
**Base de mesure** : `labuse` locale (431 663 parcelles, run servi `q_v16`, cascade `q_v13_sources1`) — mêmes données qu'en prod.

> Depuis la rebase, la fiche a un **cache versionné par parcelle** (VITESSE-PROD-1, ~5 ms sur hit). La prod 1,35 s / 3-9 s est donc le **chemin cache-MISS (froid)** — exactement ce que ce lot optimise. Les 10 parcelles mesurées sont distinctes (toutes des miss).

---

## 1. L'écart « 1,3 s de SQL vs 3-9 s servis » : répartition par étape

Chronométrage de `/parcels/{idu}` par étape sur **10 parcelles froides** (`scripts/vfiche2_chrono.py` : events SQLAlchemy pour le SQL, `jsonable_encoder`+`json.dumps` pour la sérialisation, `gzip.compress` pour le transport, acquisition de connexion pour le pool). Médianes :

| étape | avant | après |
|---|--:|--:|
| **SQL** (somme des allers-retours) | **1 447 ms** | **522 ms** |
| Python (assemblage entre requêtes) | 113 ms | 95 ms |
| sérialisation JSON | 4,7 ms | 2,6 ms |
| gzip (middleware) | 3,7 ms | 2,3 ms |
| attente du pool | 0,4 ms | 0,2 ms |
| **build total** | **1 600 ms** | **587 ms** |
| nb de requêtes SQL / fiche | 233 | 216 |

**Verdict sur l'écart.** La fiche est **à ~90 % du SQL** ; Python, sérialisation, gzip et pool sont négligeables (≤ 120 ms cumulés). Les ~1,3 s de SQL mesurés par `pg_stat_statements` en prod sont le **temps d'exécution PostgreSQL** ; le reste de l'écart jusqu'à 3-9 s servis n'est **ni du Python ni de la sérialisation** — c'est le coût des **~230 allers-retours** par fiche sous charge (latence réseau par requête + contention) **et la pression sur le pool** (sous concurrence, `pool wait` monte alors qu'en mono-requête il est à 0). Le levier est donc double : **réduire le temps SQL ET le nombre de requêtes**. Les deux baissent (−64 % de temps, −17 requêtes).

---

## 2. Corrections (chacune prouvée identique à l'octet)

### 2.1 Constantes recalculées à chaque fiche → mémorisées une fois par run/jeu de données

Mémo process TTL 60 s (même cadence que le cache de fiche VITESSE-PROD-1 ; `_mem_cached`, vidé par `clear_mem_cache()` en test) — valeur **identique**, calculée une fois au lieu d'à chaque fiche.

| constante | avant | après |
|---|--:|--:|
| `_cascade_run` (résolution cascade du run : `params` + 2 sondes `dryrun_parcel_evaluations` à plan générique) | **183 ms / 4 req** | **0 ms / 0 req** |
| couverture ANC (`count(DISTINCT commune) FROM parcels` 215 ms¹ + `count(DISTINCT left(idu,5)) FROM parcel_anc`) | bloc ANC 56 ms / 8 req | 26 ms / 5 req |
| clé de fraîcheur `serv_version` (`max(created_at)‖count(*)` sur `spatial_layers` + parcels) du bloc Dispositifs | ~35-80 ms¹ / fiche | 0 ms sur hit |

¹ valeurs prod `pg_stat_statements` (215/81 ms) ; en local 21/35 ms — même nature, même économie.

### 2.2 Propriétaires voisins (`fiche_blocs3.pm_voisines`) — réécriture

`EXPLAIN ANALYZE` : **186 ms**, dont la quasi-totalité à matérialiser la vue `v_parcel_dvf_last` EN ENTIER (CTE multi-agrégats, seq scan ~100 k lignes de `dvf_mutations_parcelle` + ~56 ms de planification) alors que seuls ~16 voisins sont retenus. Or la requête ne lit de cette vue **que `max(date_mutation)`**.

**Réécriture** : `JOIN v_parcel_dvf_last` → `JOIN LATERAL (SELECT max(date_mutation) … WHERE id_parcelle = p2.idu)`. C'est la **même grandeur** (la vue est `DISTINCT ON (id_parcelle) … ORDER BY date_mutation DESC`, donc sa `date_mutation` = `max(date_mutation)` par parcelle), lue par l'index `ix_dvfp_parcelle` pour les seuls voisins.

- **Identité prouvée** : 0 écart sur **300 parcelles** (94 non vides), lignes et ordre compris.
- **Temps** : 137 → **8,5 ms** / parcelle sur ces 300 (×16). Bloc fiche : 153 → **4 ms**. → **sous 50 ms**. ✔

### 2.3 Distances — 7 KNN → 1 requête (`_proximites_block`)

Le bloc proximités lançait **9 requêtes** dont 7 `plus_proche` (un KNN `ORDER BY geom_2975 <-> g LIMIT 1` par `kind` : arrêt, pôle, téléphérique, ligne HT, ligne MT, tracé transport, poste). Regroupées en **1 requête** `UNION ALL` (`_plus_proche_multi`).

- **Pourquoi `UNION ALL` et pas un `LATERAL` sur `VALUES`** : première tentative (LATERAL/VALUES) → **5 des 20 parcelles md5-divergentes**. Cause isolée : des couches **équidistantes** (ex. deux lignes de bus à 6 m, HTA aérien/souterrain à 0 m) ; le départage sur égalité est implicite (ordre de parcours de l'index GiST) et un plan différent choisit un autre objet « le plus proche » (aussi juste, mais octet différent). La forme `UNION ALL` où **chaque branche est la requête `plus_proche` à l'identique** garde le **même plan par kind → même ligne sur égalité**.
- **Identité prouvée** : 0 écart sur **250 parcelles** vs 7 appels `plus_proche` (dont les 5 cas d'égalité).
- Bloc : 92 ms / 9 req → **62 ms / 3 req** (les 7 KNN en une passe ; `tcsp` et `axe_structurant` gardent leur requête propre — `axe` pour conserver sa dégradation partielle sur erreur, `tcsp` car distance en `geography` + logique de seuil distincte).

> Les **12** distances annoncées se répartissent : 7 ici (→ 1), + `tcsp`, + `axe`, + le bloc `proximites_equipements` (maille domaine BPE, autre mécanisme). On ramène les 7 combinables à 1 ; les autres sont de familles/types différents (pas regroupables sans changer la sortie) — **« sinon dis pourquoi »**.

### 2.4 Le plus gros poste SQL : `score_labuse` (bloc `analyse_labuse`) — index

`EXPLAIN ANALYZE` : **162 ms, Parallel Seq Scan** de ~1 M lignes. La requête filtre `WHERE run_label = :r AND idu = :idu`, or la PK est `(run_label, parcel_id)` et il n'existait **aucun index sur `idu`**.

**Index ajouté** `score_labuse (run_label, idu)` (dans `ensure_schema`, idempotent). Plan → **Index Scan, 0,04 ms**. Bloc : 123 → **0,8 ms**. Valeurs servies identiques (même ligne).

> **Geste de déploiement prod** (base existante, hors rebuild) : `CREATE INDEX CONCURRENTLY IF NOT EXISTS score_labuse_run_idu ON score_labuse (run_label, idu);` — `ensure_schema` le posera au prochain rebuild du Score, mais l'index immédiat donne le gain sans attendre.

---

## 3. Preuve d'invariance (md5)

`scripts/vfiche2_md5.py capture|compare` — payload complet `/parcels/{idu}`, `jsonable_encoder` + `json.dumps(sort_keys)`.

**20/20 parcelles `=== IDENTIQUE ===`** après l'ensemble des corrections (y compris les 5 qui avaient divergé avec la variante LATERAL de 2.3, re-vérifiées OK avec `UNION ALL`).

Tests ciblés : `test_fiche_blocs3 · test_servitudes · test_voisinage · test_anc(_service) · test_fiche1_aleas/tcsp · test_coherence_run_fiche · test_algofix1_point2_score_labuse` → **40 passed, 2 skipped** (skips = base de test sans parcelle à aléa / proche TCSP, pré-existants).

---

## 4. Bilan

| | avant | après | gain |
|---|--:|--:|--:|
| build fiche (froid, médiane) | 1 600 ms | **587 ms** | **−63 %** |
| dont SQL | 1 447 ms | 522 ms | −64 % |
| requêtes / fiche | 233 | 216 | −17 |
| max observé | 2 228 ms | 1 043 ms | −53 % |

Le reste du SQL (~520 ms) est dominé par `_data_sources_fiche` (**55 requêtes** de remplissage/existence par fiche, ~90 ms) et par les blocs d'intersection géométrique live — **non traités ici** (hors périmètre : refonte du remplisseur de sources, risque sur la sortie) ; signalés comme prochain gisement. `aleas_parcelle` (ex-plus gros poste, 1,75 s ×2) est **déjà corrigé par VITESSE-PROD-1** (mémo par session + `tuyau_subdivise`), confirmé à 15-26 ms ici.

### Fichiers touchés (commit 1)
- `src/labuse/api/app.py` — mémo `_cascade_run`, mémo couverture ANC, mémo clé de fraîcheur, `_plus_proche_multi` + `_proximites_block`.
- `src/labuse/api/fiche_blocs3.py` — `pm_voisines` (LATERAL).
- `src/labuse/scoring/score_labuse_combine.py` — index `score_labuse (run_label, idu)`.
- `scripts/vfiche2_{chrono,blocks,md5}.py` — harnais de mesure et de preuve (rejouables).

Aucun calcul, aucun libellé, aucun seuil modifié. Aucune donnée écrite (index mis à part).

---

## 5. `_data_sources_fiche` — 55 → 14 requêtes (commit séparé)

« Les données » liste les sources réellement utilisées sur la fiche, puis **filtre** celles sans valeur pour la parcelle via `remplissage.remplissage_source(slug, témoin)` — appelé une fois par source (~40). Chaque appel **réintrospectait le catalogue** (`to_regclass` + `information_schema.columns` par table de réservoir) → **~55 requêtes/fiche**, dont ~40 de pur catalogue.

`remplissage_source` accepte déjà un paramètre `schema` (table→colonnes, cf. `schema_public`, ajouté pour `/admin/circuit`) qui supprime ces lectures catalogue ; la fiche ne le passait pas. Correctif :

- on calcule le catalogue **une fois**, partagé par tous les appels de la boucle ;
- **mémorisé** (TTL 60 s) car `schema_public` scanne TOUT `information_schema.columns` (coûteux) et le catalogue est une constante du jeu de données — sans le mémo, la fiche troquait 40 petites lectures catalogue contre un gros scan **par fiche** (mesuré : +40 ms, régression). Avec le mémo : le scan tourne une fois par 60 s.

**Identité** : `schema_public` renvoie la même existence/colonnes (schéma public) que `to_regclass`/`information_schema` ; les `count(...)` réels sont inchangés → mêmes verdicts garder/écarter. **md5 20/20 IDENTIQUE.**

| mesure (bout en bout, même machine) | avant | après |
|---|--:|--:|
| build froid médiane | 539 ms | **441 ms** (−18 %) |
| dont SQL | 458 ms | 369 ms |
| requêtes / fiche | 216 | **174** (−42) |
| bloc `_data_sources_fiche` | 55 req | **14 req** |

Tests : `test_fiche1_sources_attendues · test_circuit_provenance · test_circuit_p4_*` → **13 passed**.

**Cumul des deux commits** : fiche froide **1 600 → 441 ms** (−72 %), **233 → 174 requêtes** (−59). Reste comme gisement les ~14 `count(...)` de remplissage (un par table-réservoir jointe) et les intersections géométriques live — batchables mais au prix d'une refonte de `remplissage_source` (partagé avec `/admin/circuit`), hors de la règle « md5 strict / risque minimal » de ce lot.

### Fichiers touchés (commit 2)
- `src/labuse/api/app.py` — `_data_sources_fiche` passe `schema_public` mémorisé à `remplissage_source`.
