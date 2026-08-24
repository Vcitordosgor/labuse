# AUDIT — Moteur carte MapLibre (fond)

**Date** : 2026-08-24 · **Branche** : `audit/carte-fond` · **Type** : audit seul (aucune modification de code ; Postgres en lecture — `SELECT`/`ST_IsValid` ; endpoint tuiles sondé en `GET`).
**Périmètre** : le **moteur carte lui-même** — parcelles (MVT + GeoJSON), tuiles, rendu, interactions, cycle de vie. **Hors périmètre** : couches d'overlay (AUDIT-COUCHES) et 5 fonds commutables (bloc à part) — cités seulement pour l'empilement z.
**Méthode** : lecture du code (`MapView.tsx`, `tiles.py`) + base locale (`mvt_parcels`/`mvt_meta`, run servi `q_v10_m129`) + mesures réelles de tuiles servies par l'app en marche.

> App laissée intacte (uvicorn:8000 + vite) : uniquement des `GET /map/tiles/*` et des `SELECT`, aucune écriture, aucun redémarrage.

---

## 1. Tableau de synthèse

| # | Élément | Verdict | Constat |
|---|---------|---------|---------|
| Sources | `parcels` (GeoJSON, mode commune) + `parcels-ile` (vector MVT, minzoom 9 / **maxzoom 15**) | ✓ | Deux voies propres (commune=GeoJSON, île=MVT). Au-delà de z15 le client sur-zoome (n'interroge pas z16+). |
| Layers parcelles | base/fill/limites/line/sel/brulantes/zone-label + jumeaux `ile-*` + `ile-pick` + `*-ping` | ✓ | Empilement z cohérent (fond→overlays→parcelles→sélection/ping au-dessus). Aucun `beforeId` (ordre d'ajout). |
| Empilement clair | `applyClairMode` déplace `parcels-fill`/`ile-fill` sous `ov-zonage` en mode clair | ⚠(bas) | Mutation d'ordre z dynamique à chaque bascule de fond — fonctionne, mais fragile (dépend de l'existence des couches). |
| Layers outils | measure-*, zone-*, module-hl/ile-hl/module-*, permit-hover-ring ; Temps = carte séparée | ✓ | Nettoyés au `setData(EMPTY)` / `setFilter` vide à la sortie (masqués, pas `removeLayer` — motif standard). |
| Génération tuiles | `mvt_parcels` matérialisée (`build-mvt`), lue par `ST_AsMVT` + cache LRU | ✓ | 431 663 lignes, SRID 3857, **0 géométrie invalide**, index GiST. Run épinglé `q_v10_m129` (`mvt_meta`). |
| **Fraîcheur tuiles** | `mvt_parcels` bâtie 2026-08-19 vs `parcel_residuel` recalculé 2026-08-23 | ⚠ | **TUILES PÉRIMÉES** : SDP/sous_densité de la carte 4 j en retard sur la fiche. Garde existe mais non bloquante + au build seulement (§2.2). |
| **Poids tuiles z12-13** | z12 St-Denis = 2,15 Mo brut / **874 Ko gzip** ; bloc 3×3 = 5,6 Mo gzip | ⚠ | Saut à z12 (extent 1024→4096 + jeu de propriétés COMPLET, dont `flags`/`zone_lib` texte). Gzip par middleware (mitigé). §2.3. |
| Cache LRU serveur | `OrderedDict` 4096 tuiles, clé `(z,x,y)` | ⚠(bas) | `_CACHE.clear()` vit dans le process CLI du build → **le serveur en marche ne vide PAS son cache** au rebuild (§2.4). |
| Cache navigateur | `public, max-age=3600, stale-while-revalidate=86400` + GZip (min 1024 o) | ✓ | Bon (tuiles ne changent qu'au build). Compression 40 % effective quand le client l'annonce. |
| Zoom / bornes | endpoint z9-22 (204 hors) ; carte SANS `maxBounds`/`minZoom`/`maxZoom` | ⚠(bas) | Cadrage initial `ILE_BOUNDS` OK, mais rien ne borne la navigation → on peut dériver hors 974 (océan vide, sans plantage). §4. |
| Événements | click/mouseenter/mouseleave sur layers ; `dataloading`/`idle` | ✓ | Pas de `mousemove` lourd → pas de throttle nécessaire (survol = curseur seul). |
| Écouteurs / nettoyage | `map.on` de `load` posés une fois ; effets dynamiques avec `map.off` | ✓ | Tous les écouteurs d'`useEffect` ont leur cleanup (`off`/`removeEventListener`). Aucun doublon au fil des navigations. |
| Pulse (sélection) | `requestAnimationFrame` 3 s + `cancelAnimationFrame` au changement | ✓ | **Nettoyage correct** (`return () => cancelAnimationFrame(raf)`, dep `[selectedIdu]`) — pas de fuite d'animation (contredit une crainte initiale). |
| ResizeObserver | `new ResizeObserver(() => m.resize())` + `ro.disconnect()` | ✓ | Recale la carte quand les panneaux s'ouvrent ; nettoyé au démontage. |
| Init carte | `new maplibregl.Map` gardé par `if (map.current) return`, dep `[select]` | ⚠(cosmétique) | `select` = action zustand STABLE → effet exécuté une fois, carte jamais recréée. La dep devrait être `[]` (trompeuse mais inoffensive). |
| Sélection résiduelle | `parcels-sel`/`ile-sel` filtrés sur `selectedIdu` | ✓ | Désélection → filtre vide → couche muette, aucun résidu. `module-hl` piloté par `moduleMap.idus` (vide → rien). |
| feature-state | aucun `setFeatureState` | ✓(note) | Le survol/sélection passent par des expressions `setFilter` (pas de feature-state) — un poil plus coûteux à muter, mais correct et sans état oublié. |

**Santé données** : `mvt_parcels` 431 663 / SRID 3857 / **0 invalide** / GiST ; `mvt_overlays` (hors périmètre) plu_gpu_zone 5 845 + ppr 164, SRID 3857, GiST+kind. Le cœur géométrique est sain.

---

## 2. Détail (là où il y a quelque chose à dire)

### 2.1 — Chaîne de génération & zooms (contexte)
`mvt_parcels` = `CREATE TABLE AS SELECT` (parcels ⟕ dryrun_parcel_evaluations[run] ⟕ parcel_p_score_v2[v2run] ⟕ parcel_zone_plu ⟕ parcel_residuel ⟕ événements/flags), géométrie `ST_Transform(geom,3857)`, index GiST (`tiles.py:128-186`). L'endpoint (`tiles.py:306`) lit cette table via `ST_AsMVTGeom`/`ST_AsMVT`, avec :
- **simplification par zoom** : z9=60 m, z10=30 m, z11=15 m, z12+=brut ;
- **extent** : 1024 (z≤11) / 4096 (z≥12) ; **buffer** 16/64 ;
- **propriétés** : z≤11 maigres (`tier_v2, etage0, zone_fam, commune`) ; z≥12 complètes (`idu, surface_m2, rang_v2, mult_v2, zone_lib, completeness_score, sdp_residuelle_m2, sous_densite, evenement, flags`).
Zoom servi z9-22 (204 hors) ; mais la **source front cape à maxzoom 15** → le client ne demande jamais z16-22 (sur-zoom de z15). La capacité z16-22 de l'endpoint est donc inexploitée (bénin).

### 2.2 — Fraîcheur : tuiles actuellement PÉRIMÉES ⚠ (le point principal)
Mesuré en base :
- `mvt_meta.updated_at` (build tuiles) = **2026-08-19 22:02**
- `max(parcel_p_score_v2.computed_at)` du run servi = 2026-08-19 18:38 (avant le build ✓)
- `max(parcel_residuel.computed_at)` = **2026-08-23 01:44** (APRÈS le build ✗)

Donc `parcel_residuel` a été recalculé le 23/08, **après** la dernière matérialisation des tuiles (19/08). Les tuiles embarquent `sdp_residuelle_m2` et `sous_densite` de l'ANCIEN résiduel → **la carte contredit la fiche** (qui lit le résiduel vivant) sur ces deux champs, tant qu'un `labuse build-mvt` n'a pas été rejoué. La garde `check_peremption_tuiles` (`bascule_gardes.py:482`) détecte exactement ce cas (`mvt_at ≥ max(score, resid)`) — mais elle est **non bloquante** et ne s'exécute **qu'au moment du build** : entre deux builds, rien ne le signale au runtime ni à l'utilisateur. C'est un état réel aujourd'hui, pas une hypothèse.

### 2.3 — Poids des tuiles z12-13 ⚠
Tuiles réelles mesurées (Saint-Denis, dense) :

| z | brut | gzip | z | brut | gzip |
|---|------|------|---|------|------|
| 9 | 573 Ko | ~230 Ko | 13 | 1,40 Mo | ~560 Ko |
| 10 | 347 Ko | — | 14 | 661 Ko | — |
| 11 | 894 Ko | ~360 Ko | 16 | 48 Ko | — |
| **12** | **2,15 Mo** | **874 Ko** | 18 | 5,5 Ko | — |

Le saut à **z12** vient de deux causes cumulées : extent 1024→**4096** ET passage aux **propriétés complètes** (dont `flags` et `zone_lib`, des chaînes de texte, par feature). Un viewport dense à z12 (bloc 3×3) = **12,8 Mo brut / 5,6 Mo gzip**. Le `GZipMiddleware` (min 1024 o) compresse à ~40 % dès que le client envoie `Accept-Encoding` (ce que fait MapLibre) → le poids réseau réel est le « gzip ». Reste lourd sur zone urbaine dense à z12 ; pas un plantage, un point de vigilance perf.

### 2.4 — Cache LRU non invalidé au rebuild (cross-process) ⚠(bas)
Le cache serveur (`_CACHE`, OrderedDict 4096) mémorise les octets pbf par `(z,x,y)`. `_CACHE.clear()` est appelé dans `build_mvt_table`/`build_overlay_mvt` (`tiles.py:185,387`) — mais ces fonctions tournent dans le **process CLI** `labuse build-mvt`, PAS dans l'uvicorn en service. Le cache mémoire du serveur en marche n'est donc **pas vidé** par un rebuild : après un `build-mvt`, le serveur continue de servir les tuiles déjà en cache (jusqu'à 4096) issues de l'ANCIENNE table, jusqu'à éviction ou **redémarrage**. Compounde §2.2 (une reconstruction ne se reflète pas tant que le serveur n'est pas relancé et le `max-age=3600` navigateur écoulé).

### 2.5 — Empilement z & bascule clair (RAS, note)
Ordre d'ajout cohérent : `bg`/rasters → overlays `ov-*` → `communes-bounds` → parcelles (`parcels-*`) → overlays MVT île → parcelles île (`ile-*`) → mesure/module → `permit-hover-ring`. En **mode clair**, `applyClairMode` (`mv(...)`) descend `parcels-fill`/`ile-fill` sous `ov-zonage` pour lisibilité — mutation d'ordre dynamique à chaque changement de fond ; fonctionne, mais couplée à l'existence des couches (fragile si un id change).

### 2.6 — Interactions & cycle de vie (RAS vérifié)
- **Écouteurs** : ceux de `m.on('load')` posés une seule fois (le montage est gardé) ; les `m.on('zoom'|'click'|...)` d'`useEffect` ont tous leur `m.off` (deps propres) → aucun doublon au fil des bascules d'outil. `window.addEventListener('keydown')` retiré au cleanup.
- **Pulse** : `requestAnimationFrame` avec `cancelAnimationFrame(raf)` + drapeau `cancelled` au changement de `selectedIdu` (`MapView.tsx:1360`) → une sélection rapide annule l'animation précédente, pas de rAF orphelin.
- **ResizeObserver** : `disconnect()` au cleanup.
- **Sélection** : `parcels-sel`/`ile-sel` filtrés sur `selectedIdu` ; désélection → filtre vide → rien de peint. `module-hl`/`ile-hl` pilotés par `moduleMap.idus` (vide → rien) → pas de résidu après fermeture d'outil.
- **Init carte** : `new maplibregl.Map` créé une fois (`if (map.current) return`) ; la dep `[select]` est une action zustand stable donc effet mono-exécution — carte jamais recréée. (Dep à mettre à `[]` par clarté.)

---

## 3. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Moyenne** | T1 | Tuiles PÉRIMÉES : `parcel_residuel` (23/08) > build `mvt_parcels` (19/08) ; garde non bloquante + au build seulement (§2.2) | La carte affiche SDP/sous-densité périmés vs la fiche, sans le signaler au runtime. |
| **Moyenne** | T2 | Tuiles z12-13 lourdes (874 Ko gzip/tuile ; 5,6 Mo gzip par viewport dense) (§2.3) | Charge réseau élevée sur zone urbaine dense à z12 (mobile). |
| **Faible** | T3 | Cache LRU serveur non vidé au rebuild (cross-process) (§2.4) | Après `build-mvt`, tuiles cachées périmées servies jusqu'à redémarrage/éviction. |
| **Faible** | B1 | Pas de `maxBounds`/`minZoom`/`maxZoom` (§4) | On peut dériver hors La Réunion (océan vide) — sans plantage. |
| **Cosmétique** | C1 | Dep `[select]` sur l'effet d'init (devrait être `[]`) (§2.6) | Trompeur à la lecture ; sans effet (carte jamais recréée). |
| **Bénin** | C2 | Endpoint sert z16-22 mais la source cape à z15 (§2.1) | Capacité serveur inexploitée ; aucun impact. |

Aucun plantage, aucune fuite d'écouteur/animation, aucune géométrie invalide, aucun résidu de sélection, aucun re-render en boucle détecté. L'empilement z est cohérent et le run est épinglé/tracé (`mvt_meta` + gardes).

---

## 4. Comportements — bounds & zoom

La carte est initialisée avec `bounds: ILE_BOUNDS` (`[55.20,-21.42,55.87,-20.85]`, La Réunion) ou `SP_BOUNDS` si commune restaurée ; `fitBounds` se rejoue à chaque changement de commune (900 ms), padding borné 8-40 px. **Mais aucun `maxBounds`, `minZoom` ni `maxZoom`** n'est posé sur le constructeur : la navigation n'est pas contrainte à l'île (on peut paner vers l'océan/le monde — les parcelles renvoient 204, le fond carto sombre est mondial). Comportement sans risque, mais non borné à La Réunion.

---

## 5. Correctifs candidats à mandater (non faits)

1. **T1 (fraîcheur)** — Rejouer `labuse build-mvt` après le recompute de `parcel_residuel` (process attendu), ET rendre la péremption visible au RUNTIME : par ex. `/map/tiles/meta` expose déjà `run_label` — y ajouter un `perime: bool` (comparaison `mvt_meta.updated_at` vs `max(resid, score)`) que le front peut signaler ; ou un check au boot du serveur ; ou un cron qui rebuild dès qu'un amont bouge.
2. **T2 (poids z12)** — Alléger z12-13 : soit garder extent 1024 à z12, soit **différer les propriétés texte lourdes** (`flags`, `zone_lib`) à z14+ (moins de parcelles/tuile), soit retirer `flags` des tuiles (déjà servi par la fiche/liste). Mesurer le gain.
3. **T3 (cache)** — Invalider le cache LRU du serveur en marche au rebuild : clé de cache incluant `mvt_meta.updated_at` (un rebuild change la clé → auto-invalidation), OU endpoint admin de purge, OU relance serveur documentée dans la procédure de déploiement post-`build-mvt`.
4. **B1 (bounds)** — Poser `maxBounds` = `ILE_BOUNDS` élargi + `minZoom` ~8 pour garder l'utilisateur au-dessus de La Réunion.
5. **C1** — Dep `[select]` → `[]` (clarté).

---

## 6. Synthèse

Le moteur carte est **sainement construit** : deux voies parcelles (GeoJSON commune / MVT île), empilement z cohérent, run épinglé et tracé (`mvt_meta` + gardes de péremption/cohérence), géométries 100 % valides, écouteurs et animations **tous nettoyés** (rAF, ResizeObserver, `map.off`), sélection sans résidu, cache navigateur + gzip corrects. **Deux écarts de gravité moyenne** : les tuiles sont **actuellement périmées** (résiduel recalculé après le dernier build, non signalé au runtime), et les **tuiles z12-13 sont lourdes** sur zone dense (874 Ko gzip). Trois points faibles/cosmétiques (invalidation cache cross-process, absence de `maxBounds`, dep d'effet trompeuse). Rien ne rame en boucle, rien ne fuit, rien ne survit à tort côté rendu — le principal risque est de **fraîcheur** (tuiles matérialisées vs amont), pas de moteur.
