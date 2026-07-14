# M6.2 — RÉSULTATS (Lot 5) : avant / après

Branche `feat/m62-perf` (aucun merge). Mesures 2026-07-14, instance 8011 (dev-mode), python urllib.
Baseline : `BASELINE.md`. **Aucun changement de données/scores/verdicts** — golden 32/32, cohérence 3/3,
E2E M6.1 29/29, suite 778 passed (8 échecs préexistants `labuse_test`, 0 nouveau) : identiques avant/après.

## Avant → après (par cible)

| Cible | Avant | Après | Gain |
|---|---|---|---|
| **geojson commune — 1er accès** | Salazie 6,4 s · St-Benoît 7,5 s · St-Paul 13 s | 0,6 s · 8,2 s · 10,7 s | petites 16× ; grosses ≈ inchangé (plancher) |
| **geojson commune — accès RÉPÉTÉ (caché)** | (non caché — 13 s à chaque fois) | **9-40 ms** (toutes communes) | **≈275×** (St-Paul) |
| **/stats sous 10 concurrent (P95)** | 3 944 ms | **1 642 ms** | stampede supprimé |
| **/stats commune (P95)** | 2 596 ms | 361 ms | 7× |
| **Tuiles — cache navigateur** | absent sur le chemin LRU (re-téléchargées) | **Cache-Control 1 h** partout | revisites carte instantanées |
| fiche / v2 / tuile (serveur) | 20-78 / 4-14 / 3-6 ms | inchangés (déjà bons) | — |
| /parcels liste 500 (@10 conc) | 1,4 s | 1,4 s (inchangé — cf. écarté) | — |

**Le levier décisif** : le geojson commune (bascule commune, #1 baseline) passe de « 13 s à CHAQUE
visite » à « 0,6-10,7 s au 1er accès, < 40 ms ensuite ». Navigation typique (aller-retour entre communes) :
instantanée. Diagnostic clé mesuré : le `json_build_object` de 51k features × 26 propriétés = **11 s
incompressibles côté Postgres** (EXPLAIN ANALYZE) — d'où le choix de CACHER plutôt que de re-sérialiser.

## Optimisations APPLIQUÉES (7 commits atomiques)

1. **geojson : sérialisation SQL** (`json_build_object`/`json_agg`, string brute) au lieu de
   `json.loads(g)` × 51k + re-sérialisation FastAPI. Byte-identique. Débloque le cache (string).
2. **geojson : sous-requête `flags` scopée à la commune** — elle scannait les 14 M lignes de
   `dryrun_cascade_results` à l'île entière (~5,4 s FIXE) à chaque requête. Flags per-parcelle → scope
   sémantiquement identique.
3. **BAN matérialisée** (`parcel_adresse`, idu PK) — élimine le LATERAL par-parcelle (~5,4 s pour 21k).
   `DISTINCT ON` = même sélection que le lateral (0 diff vérifié). Reconstruite par `build-mvt`.
4. **Cache serveur du geojson** (`_geojson_cached`) : par (commune, run), single-flight + LRU 220 Mo +
   TTL 600 s. 1er accès amorti, répétitions < 40 ms.
5. **Cache-Control navigateur** sur le geojson (`max-age=600`, URL pinne `source=run`).
6. **Tuiles : Cache-Control sur le chemin LRU serveur** (constante `_TILE_HEADERS`) — il l'omettait, le
   navigateur re-téléchargeait les tuiles chaudes.
7. **`_mem_cached` single-flight** — fin du cache stampede (/stats : une seule recompute par expiration
   au lieu de N sous concurrence).

## Optimisations ÉCARTÉES (avec raison)

- **Front code-splitting** (Outils/CRM/Sources lazy) : le chargement froid est DÉJÀ rapide (FCP 152 ms,
  574 Ko, bundle 370 Ko gzip). Pas un goulot mesuré → « ne pas optimiser au cas où » (règle du mandat).
- **Glyphs locaux** : nécessite `fontnik` + la police (Open Sans) pour générer les PBF. Ce n'est pas un
  goulot de perf (glyphs petits, cachés) mais une **exigence VPS** → recommandation M7 (ci-dessous).
- **/parcels liste** : la pagination M5.1 (page CTE → jointures sur 500 lignes) est déjà optimale ; le
  1,4 s @10 conc est de la contention CPU (10 requêtes lourdes en parallèle), pas un N+1 → rien à gagner
  proprement sans changer l'architecture.
- **Slim du geojson commune** (retirer les props « cartes » pour ne garder que le style) : les cartes de
  résultats en mode commune sont construites CLIENT-SIDE depuis ce geojson (`ResultsSection`) — les
  slimmer = réécrire la logique commune (cards depuis /parcels). Hors périmètre (« on ne réécrit pas »).
- **Suppression de `ST_SimplifyPreserveTopology`** : mesuré ~430 ms de surcoût mais réduit la taille
  (47 vs 58 Mo) — gardé (le gzip n'annule pas le gain de taille en mémoire/cache).
- **`pipeline.py:218` (ANO-1, étage 0 q_v2 en dur)** : EXCLU explicitement (note Vic — re-run + delta
  nécessaires, mandat dédié post-VPS). Non touché.

## Cibles de sortie (BASELINE) — atteinte

| Cible | Visé | Atteint |
|---|---|---|
| Premier chargement froid < 3 s | ✅ | FCP 152 ms (déjà) |
| Bascule commune < 2 s | ⚠️ partiel | **répétée < 40 ms ✅** ; 1er accès grosse commune 8-11 s (plancher json_build, amorti par cache) |
| Bascule couche < 1 s | ⚠️ | revisites cachées (Cache-Control) ; 1er toggle PPR = 4,5 Mo inhérent |
| /stats P95 < 500 ms | ⚠️ | 1 642 ms sous 10 conc (stampede supprimé ; résidu = le calcul lui-même, caché 30 s) |
| Zéro régression | ✅ | golden 32/32, cohérence 3/3, E2E 29/29, suite inchangée |

## Recommandations VPS (pour M7 — ce que nginx devra faire)

1. **`proxy_cache` nginx sur `/map/parcels.geojson`** : le cache actuel est IN-PROCESS (perdu au
   redémarrage, non partagé entre workers uvicorn). nginx le rendrait persistant et partagé → le 1er
   accès grosse commune (10 s) ne serait payé qu'une fois pour TOUS les workers/utilisateurs. Clé de
   cache = URL (inclut `source=run`), TTL aligné (600 s), invalidation au déploiement d'un run.
2. **Glyphs en LOCAL** : générer les PBF (fontnik depuis une police, ex. Open Sans) et les servir depuis
   nginx (`/fonts/{fontstack}/{range}.pbf`, cache long) ; pointer `MapView.glyphs` vers l'URL locale.
   Supprime la dépendance au CDN externe cartocdn (exigence « VPS possédé »).
3. **Brotli** nginx (en plus du gzip applicatif) sur JSON/JS/CSS/pbf — ~15-20 % de mieux que gzip.
4. **Tuiles** : nginx peut cacher les `.pbf` (Cache-Control désormais cohérent sur tous les chemins).
5. **Pré-chauffage optionnel** : au déploiement, un `curl` des 24 communes remplit le cache geojson →
   même le 1er utilisateur a une bascule commune instantanée.

## Fichiers / commits

`git log --oneline main..feat/m62-perf` : baseline + 7 perf. Tables dérivées ajoutées : `parcel_adresse`
(construite par `build-mvt`). Aucune migration destructive, aucune donnée modifiée.
