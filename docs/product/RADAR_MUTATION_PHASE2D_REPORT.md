# Radar Mutation — Phase 2D : optimisation, durcissement, polish & audit carte

> Mission nocturne **sans risque DB** (lecture seule métier). Base de départ `main = 7d04b57`.
> Rédigé le **2026-06-27**. Garde-fous respectés : aucune écriture DB, aucune table, aucune
> migration, aucun re-cascade, aucun import, scoring & verdicts intacts, pas de refonte.

## Synthèse

| Axe | Résultat |
|---|---|
| Latence liste `/mutation` | **cache TTL mémoire** : 4,7 s → **~0–9 ms** sur appel répété (×~1000), résultat **identique** |
| Durcissement API | `niveau` invalide → **422** ; `commune` inconnue → **404** ; `limit`/`min_score` déjà bornés |
| UI polish | **état de chargement** explicite + messages doux (additif, accent violet & wording conservés) |
| Mode carte | **fondation backend** `/map/mutation.geojson` (lecture seule, top caché) ; **UI reportée en 2E** |
| Optimisation SQL « pushdown » | **refusée** (gain 7 %, déstabilise le top-8) — documentée pour 2E |
| Tests | **50 passés** (+7) ; `node --check` OK |
| DB métier | **inchangée** (431 663 / 1 132 371 / 9 103 / 0 stale / cascade 8 997 413) |

---

## 1 · Baseline perf (avant 2D)

| Endpoint | Latence |
|---|---|
| `GET /mutation/{idu}` (fiche) | ~10–14 ms (excellent) |
| `GET /mutation` liste prioritaire `limit=8` | **~4,7–5,1 s** (10,8 s à froid) |
| `GET /shortlist` | ~4–4,7 s (pré-existant) |
| `GET /parcels/{idu}` (données fiche) | ~130–168 ms |

---

## 2 · Diagnostic perf de la liste `/mutation`

Profilage read-only de `top_for_commune("Saint-Paul", limit=8, pool=200)` :

| Étape | Coût | Part |
|---|---|---|
| **Étage 1 — prescore SQL** (CTE le/zon/pot/dvf/rsq/pm) | **4 761 ms** | **~90 %** |
| Étage 2 — `bati.stats_batch` (spatial, 200 candidats) | 550 ms | ~10 % |
| Étage 2 — 5× `latest_layer` | 14 ms | négligeable |
| base + morale + `layer_available` | 7 ms | négligeable |

**Cause racine** (`EXPLAIN ANALYZE`) : le prescore exécute **4 `Parallel Seq Scan` sur
`cascade_results`** (8,99 M lignes) — un par couche `zon/pot/dvf/rsq` en `DISTINCT ON` — suivis
de tris sur disque (`external merge`). Or **`cascade_results` n'a qu'un index `(parcel_id)`**, pas
d'index `layer_name` ⇒ chaque couche = un balayage complet. La CTE `le` (eval la plus récente par
parcelle de la commune) coûte à elle seule ~532 ms. Le `pool` vaut `min(2000, max(limit×5,200))` =
**200 quel que soit `limit`** ⇒ latence identique à `limit=8` et `limit=20` (confirmé : 4,73 s).

> Le coût est **dans la SÉLECTION des candidats**, pas dans le calcul du score (moteur pur, instantané).

---

## 3 · Optimisations testées (read-only)

### 3.1 Pushdown du prédicat commune dans les CTE de couches — **REFUSÉE**
Idée : restreindre `zon/pot/dvf/rsq/pm` aux parcelles de la commune (≈12 % des lignes) via l'index
`ix_cascade_parcel`. Mesure :
- gain **7 % seulement** (4 185 → 3 906 ms) : le planificateur préfère le `Seq Scan` complet à
  51 129 sondes d'index ;
- **déstabilise le top-8** : `Δ=28` candidats changent. Cause = de **nombreuses parcelles à
  prescore égal** (ex. beaucoup à 100) sans **départage déterministe** ; `LIMIT 200` tranche
  arbitrairement parmi les ex-æquo. (Le prescore reste identique sur les candidats communs :
  `Δscore=0` — la formule est bonne, c'est l'ordre du `LIMIT` qui bouge.)

Règle de la mission : « si l'optimisation change trop le classement → documenter seulement ».
→ **Non implémentée.** Reportée en 2E avec un **départage déterministe** (cf. §9).

### 3.2 Index `layer_name` sur `cascade_results` — **HORS PÉRIMÈTRE**
Un index `(parcel_id, layer_name, evaluated_at DESC)` rendrait le froid rapide **et** stable, mais
c'est une **modification de schéma DB (DDL/migration)** explicitement interdite cette nuit. À
proposer comme GO séparé (cf. §9).

### 3.3 Cache mémoire TTL — **IMPLÉMENTÉE** ✅
Le top d'une commune ne dépend que de la DB (stable hors re-cascade). On **mémorise le résultat
EXACT du moteur** quelques minutes : 1ᵉʳ appel inchangé, suivants quasi-instantanés.

---

## 4 · Optimisation implémentée : cache TTL (`src/labuse/mutation.py`)

- Dictionnaire mémoire `_TOP_CACHE`, clé `(commune, niveau, min_score, limit)`, `threading.Lock`,
  **TTL 300 s**, plafond **256 entrées** (éviction des plus anciennes / périmées).
- **100 % lecture seule** : aucune écriture DB ; mémoire process uniquement ; vidé au redémarrage.
- `clear_top_cache()` pour invalidation manuelle / tests.

**Validation** (identité stricte du résultat) :

| Mesure | Avant cache | Avec cache |
|---|---|---|
| 1ᵉʳ appel (froid) | 4 717 ms | 4 717 ms (inchangé) |
| appels suivants | 4 717 ms | **~0–9 ms** (×~1000) |
| top-8 livré | référence | **identique** (`chaud == froid` et `recalcul == froid`) |
| filtres `niveau`/`min_score`/`limit` | — | **préservés** (clés distinctes, jamais mélangées) |
| écriture DB | 0 | **0** |

Le top-8 servi reste exactement celui validé en QA V1 (`AT0737, AY0395, HK0539, CZ1202, HK0566, …`).

---

## 5 · Durcissement API (`src/labuse/api/app.py`)

| Cas | Avant 2D | Après 2D |
|---|---|---|
| `niveau` hors nomenclature (`bidon`) | 200 + liste vide silencieuse | **422** + message clair |
| `commune` inconnue (`Atlantis`) | 200 + liste vide silencieuse | **404** + message clair |
| `limit` hors borne (`0`, `999`) | déjà 422 (FastAPI) | 422 (inchangé) |
| `min_score` hors borne (`250`) | déjà 422 (FastAPI) | 422 (inchangé) |

Source unique des niveaux : `mutation.NIVEAUX`. Messages : `niveau invalide : 'bidon' (attendu :
prioritaire, forte, surveiller, faible)` / `Commune inconnue : 'Atlantis'`. Appliqué aux **deux**
endpoints (`/mutation` et `/map/mutation.geojson`).

---

## 6 · UI polish (`app.js` + `styles.css`)

Strictement **additif, sans refonte**, accent violet et wording prudent **conservés** :
- **État de chargement** explicite de la sidebar (« Analyse des parcelles à fort potentiel… » +
  pastille pulsée) — plus jamais un « — » muet pendant le calcul à froid.
- **Messages doux** : « Aucune parcelle à fort potentiel pour l'instant — rien à signaler ici. » /
  « Radar momentanément indisponible. » (au lieu d'un tiret).
- **Bloc fiche** : inchangé (chargé en ~10 ms, ne « saute » pas ; se masque proprement en 404).

---

## 7 · Audit mode carte Radar (Phase F)

**Faisable sans calcul massif ?** Oui, **à condition de ne montrer que le TOP** (prioritaire), pas
toutes les parcelles (colorer 51 129 parcelles imposerait d'évaluer toute la commune → trop lourd).

**Fondation backend implémentée** : `GET /map/mutation.geojson?commune&niveau&limit` (lecture
seule) — réutilise le **top mémorisé** puis ne fait qu'un `ST_AsGeoJSON` sur ce petit lot.

| Mesure | Valeur |
|---|---|
| froid (1ᵉʳ remplissage cache) | 4,79 s |
| **chaud (cache)** | **~8,6 ms** |
| payload (50 polygones) | ~91 Ko (3 Ko en centroïdes) |
| structure | `FeatureCollection` → `Polygon` + `{idu, score_mutation, niveau}` |
| durcissement | `niveau`→422, `commune`→404, `limit` borné `1..500` |

**UI carte NON câblée cette nuit** (calque/toggle/légende toucheraient la carte = risque
« casser la map » + frôle la refonte). → Reportée en **Phase 2E** (cf. §9), l'endpoint est prêt et
testé.

**Risques UX/perf** : 1ᵉʳ affichage à froid (4,8 s, atténué par le cache et un chargement async) ;
veiller à un calque **clairement distinct** des couches verdict (couleur violette dédiée) pour ne
pas confondre potentiel de mutation et opportunité.

---

## 8 · Tests, screenshots, DB

- **pytest : 50 passés** (`test_mutation` 9 + `test_mutation_api` 12 (+7) + `test_api` 29), 1 warning
  Starlette pré-existant. `node --check app.js` : OK.
- Nouveaux tests : `niveau` 422, niveaux valides, `commune` 404, bornes `limit`/`min_score`,
  cohérence du cache + `clear_top_cache`, structure & durcissement de `/map/mutation.geojson`.
- **Screenshots** (livrés, non versionnés) : `qa2d_sidebar_loading.png` (état de chargement),
  `qa2d_sidebar_loaded.png` (liste résolue), `qa2d_fiche.png` (bloc fiche, accent violet).
- **DB métier inchangée** avant/après : `parcels=431 663`, `parcel_evaluations=1 132 371`,
  `opportunités=9 103`, `stale=0`, `cascade_results=8 997 413`.

---

## 9 · Recommandations Phase 2E

1. **Cold path stable & rapide** — réécrire le prescore en **une passe** sur `cascade_results`
   (pivot par `FILTER`) **+ départage déterministe** `ORDER BY prescore DESC, p.id`. Rend le top
   **reproductible** ET réduit le froid (objectif < 1 s). ⚠️ change le top-8 actuel (ex-æquo) →
   **décision produit assumée** requise.
2. **Index `cascade_results(parcel_id, layer_name, evaluated_at DESC)`** (GO DB séparé) : supprime
   les 4 `Seq Scan` → froid quasi-instantané, sans toucher la formule. Le plus gros levier, mais
   c'est une **migration** (hors mission nocturne).
3. **Câbler le calque carte Radar** sur `/map/mutation.geojson` : toggle dédié, couleur violette,
   légende « potentiel de mutation à étudier », n'afficher que prioritaire/forte.
4. **Pré-calcul / matérialisation** des scores mutation (table dédiée) pour un vrai filtrage
   multi-niveaux et des listes instantanées même à froid (GO DB séparé).

---

## 10 · Conclusion

> Phase 2D livrée **sans risque** : latence répétée divisée par ~1000 (cache), API durcie (422/404),
> UI plus lisible (chargement/vide), fondation carte prête et testée. **Scoring, verdicts et DB
> métier intacts**, V1 non cassée, 50 tests verts. Les optimisations à fort levier mais
> potentiellement déstabilisantes (réécriture SQL + départage, index, matérialisation, câblage
> carte) sont **documentées pour la Phase 2E** plutôt que forcées cette nuit.
>
> **→ Validation humaine requise.**
