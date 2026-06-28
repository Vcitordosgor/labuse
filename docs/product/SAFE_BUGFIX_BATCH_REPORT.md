# Lot « safe bugfix » LABUSE — rapport (#2, #4, #6, #7, #8, #10, #11, #13)

> Correction du lot de bugs **sûrs** identifiés par l'audit, **sans toucher** à la DB, au scoring
> effectif, aux verdicts, ni aux valeurs du Radar Mutation. Rédigé le 2026-06-28 sur `main = d786532`.
> DB métier vérifiée inchangée (`431663 / 9103 / parcel_enrichment 27`).

## Synthèse — 8/8 corrigés, 486 tests verts, DB intacte

| # | Bug | Correctif | Risque |
|---|---|---|---|
| **2** | `/parcels` timeout >45 s (no-limit + N+1) | `limit`/`offset` bornés + requête LATERAL unique | nul (endpoint non-UI) |
| **4** | docstring `/enrichment` « lecture seule » mensonger | docstring corrigée (dit qu'il écrit un cache) | nul (doc) |
| **6** | `/demo-status` lent (~6,4 s) | cache mémoire TTL 30 s | nul (résultat identique) |
| **7** | `/stats` lent (~2 s) | cache mémoire TTL 30 s, clé par commune | nul (résultat identique) |
| **8** | export HTML f-strings (XSS théorique) | **déjà échappé** ; ajout d'un test anti-injection | nul |
| **10** | poids Radar Mutation codés en dur | externalisés dans `config/mutation_weights.yaml` (valeurs **identiques**, fallback) | nul (test de non-régression) |
| **11** | `_clamp()` dupliqué | factorisé dans `labuse.numeric.clamp` | nul (impl. identique) |
| **13** | malus −15 non affiché dans la fiche Radar | ligne malus explicite (« … −15 pts ») | nul (calcul inchangé) |

## Détail par bug

**#2 `/parcels`** (`api/app.py`) — ajout de `limit` (défaut 100, max 1000) + `offset` bornés (FastAPI
`Query`), et remplacement du **N+1** (`_latest_eval` par parcelle) par une **requête LATERAL unique**
(comme `/stats`). Avant : timeout > 45 s. Après : **6–190 ms**. Bornes : `limit=9999`/`0` → **422**.
Endpoint **toujours non utilisé par l'UI** (qui passe par `/map/parcels.geojson` + `/parcels/{idu}`).

**#4 `/enrichment`** (`api/enrichment.py`) — docstring module corrigée : ne dit plus « n'écrit rien » ;
précise que `enrichment_cached()` **écrit un cache** (`parcel_enrichment`, cache-on-read) sans toucher
les données métier. **Logique cache inchangée** (pas de risque).

**#6 `/demo-status`** & **#7 `/stats`** (`api/app.py`) — helper `_mem_cached()` (cache mémoire process,
lock, TTL, borné 256, `clear_mem_cache()`). `/demo-status` : ~6,4 s → **3 ms** en répété ; `/stats`
(clé par commune) : ~2 s → **3 ms** en répété. **Résultat strictement identique** (vérifié). Rien en
DB. Un fixture autouse vide le cache **avant chaque test** (pas de fuite inter-tests).

**#8 export HTML** (`api/export.py`) — `fiche_html` **utilisait déjà `html.escape`** sur **toutes** les
valeurs injectées (idu, commune, section, numéro, statut, disclaimer, détails, sources, notes,
synthèse IA). Le risque d'audit était théorique → **aucune correction de format nécessaire** ; ajout
d'un **test anti-injection** (`<script>`/`<img onerror>` échappés) pour verrouiller le comportement.

**#10 poids Radar Mutation** (`mutation.py` + `config/mutation_weights.yaml`) — les 7 poids, le malus,
les seuils, le plancher de confiance et les paramètres surface/bâti sont **externalisés en YAML**. Le
code conserve **exactement** ces valeurs en défaut : un YAML absent/incomplet ne change **rien**.
Test de non-régression : valeurs identiques **+** cas connu (type DM0031) toujours **100/prioritaire**.
**Aucune valeur changée** (vérifié : `VALEURS IDENTIQUES = True`).

**#11 `_clamp`** (`numeric.py` + `mutation.py` + `scoring/opportunity.py`) — fonction dupliquée
factorisée dans `labuse.numeric.clamp` (impl. **strictement identique** `max(lo, min(hi, x))`), importée
des deux côtés. Scoring effectif **inchangé** (suite `test_scoring` verte).

**#13 malus fiche Radar** (`web/app.js` + `web/styles.css`) — `renderMutation()` affiche désormais
**explicitement** les raisons à points **négatifs** (ex. « PPR fort / pente forte — vigilance, à
confirmer **−15 pts** ») en couleur d'alerte, en plus du badge « Vigilance contrainte forte ». **Calcul
inchangé** (la donnée `raisons` existait déjà ; on cesse juste de la masquer).

## Fichiers modifiés

- `src/labuse/api/app.py` — #2, #6, #7 (+ helper cache + `clear_mem_cache`).
- `src/labuse/api/enrichment.py` — #4 (docstring).
- `src/labuse/mutation.py` — #10 (chargement YAML), #11 (import `clamp`).
- `src/labuse/scoring/opportunity.py` — #11 (import `clamp`).
- `src/labuse/numeric.py` — **nouveau**, #11 (`clamp` partagé).
- `config/mutation_weights.yaml` — **nouveau**, #10 (poids externalisés, valeurs V1).
- `src/labuse/api/web/app.js` + `styles.css` — #13 (affichage malus).
- `tests/` — `test_mutation` (#10), `test_export_comparables` (#8), `test_api` (#2), `conftest`
  (fixture autouse vidage cache).

## Ce qui n'a PAS été touché (volontairement)

- Bugs **1, 3, 5, 9, 12, 14, 15** : hors lot (non corrigés).
- DB, scoring **effectif**, verdicts, **valeurs** du Radar Mutation : strictement inchangés.
- Logique du cache `/enrichment`, multi-commune (sauf rien — non modifié), carte, `/map/*`.
- Aucune migration, aucun index, aucun re-cascade, aucun import.

## Tests

- **486 passés** (full suite ; +3 : non-régression poids #10, pagination `/parcels` #2, anti-injection
  HTML #8). `node --check app.js` OK.
- Fixture `conftest` autouse vide les caches mémoire avant chaque test.

## Performance avant / après

| Endpoint | Avant | Après (chaud) |
|---|---|---|
| `/parcels` (liste) | **timeout > 45 s** | **6–190 ms** (borné) |
| `/demo-status` | ~6,4 s | **3 ms** (cache) |
| `/stats` | ~2 s | **3 ms** (cache) |

## DB inchangée

`parcels=431 663` · `opportunités=9 103` · `parcel_enrichment=27`. Aucune écriture
(`/enrichment` aborté en QA UI). Tests sur base dédiée `labuse_test`.

## Limites restantes

- Bugs **1** (déjà livré séparément en fait : multi-commune), **3** (auth de déploiement), **5**
  (`/map/bati` 11 s), **9** (`app.py` monolithe), **12** (perf froide Radar liste), **14** (niveau
  « surveiller » sidebar), **15** (Saint-Philippe non évalué + classification Saint-Leu) — **non
  traités** (hors lot).
- Caches `/stats` & `/demo-status` : péremption ≤ 30 s (acceptable, données stables hors
  re-évaluation). Le **cold start** subsiste (1ᵉʳ appel non mémorisé).
