# CARTE-VITESSE-2 — remèdes à la lenteur d'ouverture de la carte

Suite d'exécution de l'audit **CARTE-VITESSE-1** (`docs/audit-2026-09/CARTE-VITESSE-1.md`).
Branche `perf/carte-vitesse-2`. Chaque lot = un remède chiffré de l'audit.

| Remède audit | Lot | État |
|---|---|---|
| R1 — pré-chauffe des tuiles z9-z11 (cache persistant) | **A** | ✅ commit `62cb6f57` |
| R2 — code-split du monolithe `index` (les 16 outils) | **B** | ✅ commit `faa0a3af` |
| R3 — ETag + revalidation 304 sur les tuiles parcelles | **C** | ✅ commit `76eeff9a` |
| R4 — mémoïser les API de boot (plan des couches) | **D** | ✅ ce lot |

Mesures : harnais `harnais/bench.mjs` + `harnais/run_bench.sh` (Playwright, redémarrage API
pour un vrai froid), résultats dans `MESURES/bench.csv`. Machine locale, base **au calme** (aucune
autre session — contrairement à l'audit qui subissait la contention S1/S2). Les valeurs absolues
sont donc basses ; ce qui compte est le **delta avant/après** à conditions identiques.

---

## Lot A — pré-chauffe des tuiles (rappel, déjà commité)

Les tuiles parcelles z9-z11 de l'île (26 : z9=4, z10=6, z11=16) faisaient un *Parallel Seq Scan* de
`mvt_parcels` (240 Mo, index GiST non sélectif à z9). Désormais pré-générées dans `mvt_tile_cache`
(clé versionnée = `mvt_meta.updated_at`, `etag`, `built_at`) et servies en ~7 ms, cache LRU vide
compris (traverse les 5 workers prod). `warm_parcel_tiles()` branché en fin de `rebuild_mvt_servies`
+ CLI `labuse tiles-warm`. z≥12 reste à la volée (l'index GiST porte, ~40 ms).

---

## Lot B — code-split du monolithe `index` (R2)

**Cause (audit).** Le chunk `index` pesait **1,04 Mo (gz 276 Ko)** = les 16 outils + la Fiche +
toutes les vues plein écran, importés **statiquement** par `App.tsx`. Résultat : un mur de long-tasks
de fil principal (~4 s dans l'audit) AVANT que les tuiles ne partent, alors que rien de tout cela
n'est sur le chemin du **premier écran** (shell + carte).

**Correction.** Tout ce qui est monté **sous condition** (view / module / état) passe en `import()`
lazy derrière un `<Suspense>` — rendu identique, seul le moment du téléchargement change :

- `ModulePanel` (tire l'arbre des 16 outils : `moteurs`, `EtudeZone`, `blocB`, `TaxeAmenagement`,
  `Gabarit`, `Communes`, `Successions`, `Blocs`, `Plu`, `ProspectionSolaire`…), `Fiche`
  (constructibilité / faisabilité), `AdminView`, `CopiloteView`, `Kanban`, `SourcesPage`,
  `ProjetsPanel`, `ParcoursTinder`, `SurveillancePanel`, `ComparePanel`, `ContextePanel`.
- Les 3 modales de **Communes** (table / Évolution / Radar) et `ContextePanel` : leur **montage** est
  gaté (`module==='communes'` / `contexteCommune`) pour que le chunk n'arrive qu'à l'ouverture (le
  composant garde son `return null` interne).
- Restent **eager** (shell du premier écran) : `Rail`, `Header`, `LeftPanel`, `MapView` (déjà lazy
  M-V), `SourceDrawer`, `Toast`, `IaRestitution`.

**Résultat build** (`vite build`, gzip) :

| chunk | avant | après |
|---|---|---|
| `index` (critique, premier écran) | **276 Ko** | **48 Ko** (−83 %) |
| `Fiche` (au clic parcelle) | dans `index` | 104 Ko (différé) |
| `AdminView` (admin only) | dans `index` | 50 Ko (différé) |
| `Communes` (outil) | dans `index` | 12,5 Ko (différé) |

**Résultat runtime** (médiane de 3 froids ; `avantB` = post-merge + lot A, `apresB` = + lot B) :

| métrique | avantB | apresB | delta |
|---|---|---|---|
| FCP (froid) | 424 ms | 200 ms | **−53 %** |
| 1ʳᵉ tuile peinte (froid) | 1428 ms | 879 ms | **−38 %** |
| dernière tuile (froid) | 1543 ms | 1126 ms | −27 % |
| FCP (chaud) | 144 ms | 112 ms | −22 % |

Sur cette machine rapide + tuiles déjà chaudes (lot A), les gains en absolu sont modestes ; le levier
réel — retirer **228 Ko gz du chemin critique** — se paie surtout sur matériel lent / réseau contraint
(là où l'audit mesurait 3,95 s de long-tasks du monolithe). Le FCP divisé par deux corrobore.

---

## Lot C — ETag + revalidation 304 sur les tuiles parcelles (R3)

**Cause (audit).** Aucun ETag sur `/map/tiles/{z}/{x}/{y}.pbf` : une fois `max-age` écoulé (ou en
revalidation `stale-while-revalidate`), le navigateur re-téléchargeait la tuile **entière** (z9 ≈
570 Ko) même inchangée.

**Correction.** `_tile_response()` = point unique de fabrication de la réponse tuile — **ETag fort**
(hash md5 du CONTENU, déjà stocké par lot A dans `mvt_tile_cache`) + `Cache-Control`. Un
`If-None-Match` correspondant → **304** sans corps (~0 octet réseau) ; tolère listes, tags faibles
`W/"…"` et joker `*`. L'ETag change au rebuild-mvt (le contenu change) → invalidation propre côté
client, et un proxy / CDN amont peut revalider sur cette clé forte. Le LRU mémorise désormais
`(octets, ETag)` pour ne pas recalculer le md5 à chaque tuile chaude ; les 3 chemins (LRU / cache
persistant / à la volée) portent tous l'ETag.

**Preuve (live).**

```
GET /map/tiles/9/334/286.pbf        → 200  ETag "9025…c40"  Content-Length 571970
GET … If-None-Match: "9025…c40"     → 304  (0 octet)
GET … If-None-Match: "deadbeef"     → 200  (mismatch → renvoie la tuile)
```

Vérifié aussi z12 (à la volée, 863 Ko → 304) et z14 (tuile vide → 304). Test de contrat
`_tile_response` (200/304/faible/joker/mismatch) dans `tests/test_carte_tuiles.py`.

**Note infra.** Le multi-worker prod (LRU perdu ×5) est déjà couvert par la table persistante du
lot A (traverse les workers). Caddy reverse-proxie et transmet l'ETag tel quel — la revalidation
fonctionne sans toucher au `Caddyfile`. Un **vrai cache Caddy** des tuiles exigerait un plugin
(Souin `cache`) : hors périmètre « risque nul », laissé en option de suivi.

---

## Lot D — mémoïser le plan des couches (R4)

**Cause (audit).** `/map/tuyau/couches` (chemin des overlays de la carte) appelait `couches_carte()`
→ `declarations.charger()` à **chaque requête**, ce qui **relisait + parsait tout l'arbre YAML**
(`declarations/**/*.yaml`). L'audit y mesurait ~3,4 s de Python **sous contention**.

**Correction.** Mémoïsation `functools.lru_cache` (même idiome que `labuse.plu.destinations._load_yaml`,
avec `cache_clear()` pour les tests) sur les lecteurs de déclarations statiques :
`declarations.charger`, `declarations.couches_carte`, `couches_tuyau._charger_hors_registre`. Les
déclarations ne changent qu'au déploiement ; tous les appelants itèrent le résultat **en lecture
seule** (aucune mutation de la liste cachée).

**Résultat (live, `/map/tuyau/couches`).**

| appel | avant | après |
|---|---|---|
| 1ᵉʳ (parse, une fois par process) | 0,47 s | 0,26 s |
| suivants (chaque chargement de carte) | ~0,18 s | **~0,004 s** (≈ ×45) |

Sous la contention prod de l'audit (×3,4 s), la même mémoïsation retire ce coût de **chaque** ouverture
de carte après le premier appel.

*Non traité : `/moi/prefs-carte` 401 en local — comportement de dev seul (prod a une session), repli
fond sombre déjà gracieux, aucun coût perf.*

---

## Tests

- Front : `tsc -b` OK, `vitest` **188/188**, `vite build` sans erreur.
- Back : `pytest` tuiles 22 passed (dont le nouveau contrat ETag). Suite complète : voir décompte
  final — 1 échec **pré-existant** confirmé (`test_plu_destinations.py::test_module_unique_aucune_autre_lecture`,
  échoue à l'identique sans les modifs de ces lots : la garde grep « plu_destinations » attrape des
  fichiers ajoutés par les merges de `main`, sans rapport avec la carte).

## Cible de l'audit vs atteint

Cible réaliste de l'audit : **froid ~2,5-3 s, chaud <1 s**. Au calme + lot A, le froid mesuré est déjà
~1,1 s (dernière tuile) et le chaud ~0,3 s. Les lots B/C/D consolident : moins de JS critique (B),
plus de re-téléchargement de tuiles inchangées (C), plan des couches instantané (D) — les gains
tiennent d'autant mieux quand le matériel / le réseau / la contention DB se dégradent.
