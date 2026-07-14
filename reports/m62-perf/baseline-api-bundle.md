# M6.2 Lot 1 — Baseline API + bundle + infra (mesuré, instance 8011 dev-mode)

Mesures : 2026-07-14, run servi q_v5_m6b. Instance de mesure 8011 (dev-mode, sans rate-limit).

## API sous 10 requêtes concurrentes (P50 / P95, 3 rounds)

| Endpoint | P50 | P95 | Taille (transfert) | Verdict |
|---|---|---|---|---|
| `/stats` île | 8 ms | **3 944 ms** | 253 o | 🔴 **cache stampede** (P50 caché, P95 = 10 requêtes ratent le TTL ensemble et recalculent) |
| `/stats?commune=SP` | 7 ms | **2 596 ms** | ~0,3 Ko | 🔴 même stampede |
| `/parcels?limit=500` | **1 409 ms** | **1 584 ms** | 224 Ko brut → **16,7 Ko gzip** | 🟠 requête lourde, endpoint fréquent |
| `/parcels/{idu}` fiche | 78 ms | 93 ms | 13 Ko | 🟢 |
| `/v2/score/{idu}` | 14 ms | 16 ms | 1 Ko | 🟢 |
| tuile z12 (LRU) | 5 ms | 26 ms | qq Ko | 🟢 rapide, MAIS cache navigateur manquant (voir infra) |
| tuile z9 île | 5 ms | 24 ms | qq Ko | 🟢 |
| **`/map/parcels.geojson` commune SP** | **15 383 ms** | 15 397 ms (@4 conc) | 41 Mo brut → ~5 Mo gzip | 🔴 **#1 — génération serveur** |
| `/segments` (vues) | 17 ms | 684 ms | 19 Ko | 🟢 (P95 = 1er calcul) |

## Bundle front (dist/assets, déjà buildé)

| Chunk | Brut | gzip transféré | Note |
|---|---|---|---|
| maplibre-*.js | 783 Ko | **217 Ko** | plancher (lib carte, requise d'emblée) |
| index-*.js (app) | 277 Ko | ~80 Ko | 🟠 **non code-splitté** : Outils/CRM/Sources/fiche tout chargé au boot |
| vendor-*.js (react/query/zustand) | 180 Ko | ~57 Ko | sain |
| index-*.css | 95 Ko | ~15 Ko | à vérifier (purge Tailwind) |
| **Total initial** | **~1,3 Mo** | **~370 Ko gzip** | 3 chunks seulement |

Deps : maplibre-gl, react, react-query, zustand — **aucune lib lourde superflue** (pas de lodash/moment/chart/pdf-front).

## Infrastructure / ce qui est DÉJÀ bon (ne pas re-faire)

- ✅ **Compression gzip complète** : `GZipMiddleware` (minimum_size=1024) sur les assets statiques ET les
  JSON API (/parcels 224 Ko → 16,7 Ko). Rien à ajouter côté app (brotli = M7/nginx).
- ✅ Tuiles : cache LRU serveur en mémoire (5 ms), `Cache-Control: public, max-age=3600` sur le chemin FRAIS.

## Cibles infra identifiées (mesurées)

1. 🔴 **geojson commune (#1)** : mode commune charge le geojson complet (`MapView.tsx:190`,
   `enabled: !ile`) → 9-15 s de génération serveur par commune. En mode île = tuiles (rapide).
   → cache applicatif par commune (invalidé au run) et/ou allègement requête (lot 2/3).
2. 🔴 **cache stampede /stats** : `_mem_cached` (app.py:290) relâche `_MEM_LOCK` AVANT `compute()`
   → sous concurrence, N requêtes recalculent en même temps (P95 ~4 s). → single-flight (lot 2).
3. 🟠 **/parcels liste 1,4 s** @10 conc : requête lourde à profiler (EXPLAIN, lot 2).
4. 🟠 **tuiles LRU sans Cache-Control** : le chemin LRU (tiles.py:160/240) renvoie la tuile SANS le
   header `Cache-Control` que le chemin frais (206/256) porte → le navigateur re-télécharge les tuiles
   CHAUDES à chaque navigation. Incohérence, fix trivial (lot 3).
5. 🟠 **glyphs sur CDN EXTERNE** : `MapView.tsx:37` → `tiles.basemaps.cartocdn.com/fonts/` (le fix M6.1
   a changé l'hôte mais PAS rapatrié en local). Contraire à « VPS possédé, pas de CDN externe » (lot 3).
6. 🟠 **front non code-splitté** : 277 Ko d'app au boot inclut Outils/CRM/Sources (lot 4).

## Diagnostic cible #1 (geojson commune) — décomposition mesurée

Endpoint : **12,97 s** (chaud, Saint-Paul, 3,56 Mo gzip). Décomposition SQL (psql `\timing`) :

| Étape | Temps |
|---|---|
| jointure de base (parcels ⨝ eval commune) | 103 ms |
| toutes les jointures d'affichage (score/résiduel/vue-mer/zone) | 103 ms |
| `ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, 2e-5))` × 51k | 526 ms |
| `ST_AsGeoJSON(geom)` SANS simplify × 51k | 93 ms |

→ **La SQL totale est ~1 s. Les ~12 s restants sont côté PYTHON** : `_q_v2_geojson` (app.py:1051) fait
`"geometry": json.loads(r["g"])` **pour chacune des 51 129 lignes** — Postgres produit le geojson en
string, Python le RE-PARSE (json.loads × 51k), reconstruit un dict par feature, puis FastAPI RE-SÉRIALISE
tout en JSON. Triple travail de sérialisation.
**Fix (lot 2)** : construire la FeatureCollection entière en SQL (`json_build_object` + `json_agg`) et la
renvoyer en string brute via `Response(media_type="application/json")` — une seule sérialisation, côté
Postgres. Attendu : 13 s → ~1-2 s. Même anti-pattern à app.py:948 (couches). Donnée INCHANGÉE.
Bonus mesuré : `ST_SimplifyPreserveTopology` COÛTE ~430 ms de plus qu'il ne fait gagner (gzip absorbe la
taille) — à réévaluer.

FCP / TTI / carte / fiche navigateur : voir `baseline-navigateur.md` (agent Playwright).
