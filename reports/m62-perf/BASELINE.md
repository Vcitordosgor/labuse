# M6.2 — BASELINE de référence (Lot 1) — dicte les priorités

Mesuré le 2026-07-14, run servi q_v5_m6b, instance 8011 (dev-mode, sans rate-limit).
Détail : `baseline-api-bundle.md` (API/bundle/infra + diagnostics) · `baseline-navigateur.md` (Playwright/CDP).

## Chargement initial (navigateur, CDP) — 🟢 déjà bon

| Métrique | Froid | Chaud |
|---|---|---|
| FCP | 152 ms | — |
| Poids transféré | 574 Ko (346 Ko JS) | 21 Ko (24/39 req. du cache) |
| Bundle (gzip) | maplibre 217 Ko + app ~80 Ko + vendor ~57 Ko + css ~15 Ko | — |

Le premier chargement est **léger et rapide** (gzip complet déjà actif). Pas une cible.

## Interactions — LES CIBLES (par impact × fréquence)

| Rang | Interaction | Mesure | Cause racine (diagnostiquée) | Lot |
|---|---|---|---|---|
| 🔴 1 | **Bascule de commune** | **10,3 s** (nav) / **13 s** (endpoint) | `_q_v2_geojson` fait `json.loads(r["g"])` **× 51k** puis FastAPI re-sérialise ; la SQL ne fait que ~1 s | 2 |
| 🔴 2 | **/stats sous concurrence** | P50 8 ms / **P95 3,9 s** | `_mem_cached` relâche le verrou avant `compute()` → stampede (N recalculs simultanés) | 2 |
| 🟠 3 | **Bascule couche PPR** | 6,4 s / **4,5 Mo pbf** | tuiles MVT PPR île re-téléchargées à chaque toggle (pas de cache navigateur) | 3 |
| 🟠 4 | **Bascule Équipements / 50 pas** | 5,2 / 5,0 s | GeoJSON couche + rendu plein viewport ; pas de cache | 3 |
| 🟠 5 | **/parcels liste 500** | 1,4 s @10 conc | requête lourde (EXPLAIN lot 2) | 2 |
| 🟠 6 | **Filtre tier** | 2,4 s | à confirmer (re-render panneau + refetch) | 4 |
| 🟠 7 | **1re tuile affichée** | 2,1 s | boot carte | 3 |

### Cibles infra (mesurées, transverses)

- 🟠 **Tuiles servies depuis le cache LRU (tiles.py:160/240) n'émettent PAS `Cache-Control`** (le chemin
  frais 206/256 l'a) → le navigateur re-télécharge les tuiles CHAUDES. Fix trivial (lot 3).
- 🟠 **Glyphs sur CDN EXTERNE** `tiles.basemaps.cartocdn.com/fonts/` (MapView.tsx:37) — à rapatrier en
  local (VPS possédé, pas de CDN externe). Lot 3.
- 🟠 **Front non code-splitté** : index 277 Ko charge Outils/CRM/Sources au boot. Lot 4.

## Ce qui est DÉJÀ bon — NE PAS toucher (respect « optimiser ce qui pèse »)

- ✅ gzip complet (assets statiques + JSON API : /parcels 224→17 Ko).
- ✅ Tuiles en cache LRU serveur (5 ms P50), fiche API 24-78 ms, /v2/score 4-14 ms.
- ✅ Chargement froid léger (FCP 152 ms), deps front saines (pas de lib lourde superflue).

## Écarté (NON une cible — pour ne pas optimiser un fantôme)

- **Fiche open « 3,35 s »** rapporté par l'agent = artefact d'attente `networkidle`. Mesure propre :
  clic→verdict **0,6-3,1 s VARIABLE** ; l'API fiche fait **24 ms**, la recherche 54 ms, `select()` ne
  change pas de commune. Le délai = **animation carte flyTo** (MapLibre ease ~1-2 s), pas un coût
  backend. → pas de fix serveur ; éventuel skeleton/perçu en lot 4 SI profilage headed le confirme.
- **ST_SimplifyPreserveTopology** : coûte ~430 ms de PLUS qu'il ne fait gagner (gzip absorbe la taille) —
  à réévaluer dans le fix #1.

## Cibles de sortie (lot 5)

Premier chargement interactif < 3 s froid / < 1,5 s chaud (déjà ~OK) ; **bascule commune < 2 s**
(depuis 10 s) ; **bascule couche < 1 s** (depuis 5-6 s) ; /stats P95 < 500 ms ; zéro régression
(golden 32/32 + cohérence 3/3 + E2E 29/29 identiques).
