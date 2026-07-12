# AUDIT M5.1 — lots 4.1 & 4.4 : couches de la carte (lecture seule)

Date : 2026-07-13 · Branche : `feat/m51-unification` · App : `http://127.0.0.1:8010/socle/` (non redémarrée)
Script : `frontend/qa/audit_couches_m51.mjs` (Playwright) · Détail réseau brut : `reports/m51-unification/audit-couches-net.json`
Captures : `reports/m51-unification/captures/couche-*.png`

Méthode : pour chaque couche du panneau « COUCHES », activation par clic dans l'UI (mode commune
Saint-Paul `#f=1&v=1&c=Saint-Paul`, viewport 1440×900), écoute des réponses réseau
(`/map/layers.geojson`, `/map/parcels.geojson`, `/map/tiles/…`, `communes974.geojson`),
vérification du rendu par diff pixel du canvas carte avant/après toggle, capture d'écran.
Côté base : comptages en lecture sur `spatial_layers`, `parcels`, `parcel_vue_mer`, `mvt_parcels`,
`mvt_overlays`. Zéro erreur console sur les deux modes.

## 4.1 — Tableau couche × réseau × base (mode commune Saint-Paul)

| Couche | Activée UI | Requête réseau | HTTP | n objets réseau | n objets base (SP / île) | Table source | Rendu | Statut |
|---|---|---|---|---|---|---|---|---|
| Zonage PLU | OK | `/map/layers.geojson?kind=plu_gpu_zone&commune=Saint-Paul` | 200 | 1 097 | 1 097 / 6 306 | `spatial_layers` kind=`plu_gpu_zone` | change | **OK** |
| Parcelles | OK (défaut ON) | `/map/parcels.geojson?source=q_v3_datagap&commune=Saint-Paul&limit=60000` (au boot) | 200 | 51 005 | 51 129 / 431 663 | `parcels` + `dryrun_parcel_evaluations` + `parcel_p_score_v2` | change | **OK** — delta 124 = parcelles < 2 m² filtrées à l'affichage (`MIN_DISPLAY_SURFACE_M2`), vérifié SQL-exact |
| PPR multirisque | OK | `/map/layers.geojson?kind=ppr&commune=Saint-Paul` | 200 | 11 | 11 / 164 | `spatial_layers` kind=`ppr` | change | **OK** |
| Vue mer | OK | aucune requête propre — filtre maplibre sur la propriété `vue_mer='oui'` du GeoJSON parcelles | — | 11 359 features `vue_mer=oui` dans le payload | 11 384 (mvt SP) / 92 419 île — `parcel_vue_mer` : 150 641 lignes (oui 92 419, partielle 17 144, non 41 078) | `parcel_vue_mer` (recopiée dans les propriétés parcelles) | change | **OK** (delta = filtre < 2 m²) |
| Parc national | OK | `/map/layers.geojson?kind=parc_national&commune=Saint-Paul` | 200 | 3 | 3 / 72 | `spatial_layers` kind=`parc_national` | change | **OK** (voir anomalie A2 : 72 = 3 géométries × 24 communes) |
| Limites parcelles | OK (défaut ON) | même source que Parcelles (aucune requête propre) | — | 51 005 | 51 129 / 431 663 | `parcels` | change | **OK** |
| Limites communes | OK (défaut ON) | `/socle/communes974.geojson` (fichier statique, au boot) | 200 | 24 | 24 communes (fichier `frontend/public/communes974.geojson` — pas de table) | statique (geo.api.gouv) | change | **OK** |
| ANRU (NPNRU) | OK | `/map/layers.geojson?kind=anru&commune=Saint-Paul` | 200 | **0** | 0 / 8 | `spatial_layers` kind=`anru` | inchangé (rien à dessiner) | **OK-VIDE** — aucun périmètre NPNRU à Saint-Paul ; les 8 périmètres couvrent 6 communes (Saint-Denis ×3, Le Port, Saint-André, Saint-Benoît, Saint-Louis, Saint-Pierre). Vérifié servi et rendu en mode île (voir ci-dessous) |
| Équipements | OK | `/map/layers.geojson?kind=amenite&commune=Saint-Paul` | 200 | 1 437 | 1 437 / 14 933 | `spatial_layers` kind=`amenite` | change (après zoom ≥ z13, `minzoom: 13`) | **OK** (voir anomalie A4 : subtypes hors légende) |

### Mode île (complément — aucune couche n'est commune-scopée, R6)

| Couche | Requête réseau | HTTP | n réseau | n base | Statut |
|---|---|---|---|---|---|
| Zonage PLU (île) | `/map/tiles/ov/plu_gpu_zone/{z}/{x}/{y}.pbf` (tuiles MVT) | 200 | 4 tuiles au cadrage île | `mvt_overlays` kind=`plu_gpu_zone` : 6 306 | **OK** |
| PPR (île) | `/map/tiles/ov/ppr/{z}/{x}/{y}.pbf` | 200 | 4 tuiles | `mvt_overlays` kind=`ppr` : 164 | **OK** |
| Parcelles (île) | `/map/tiles/{z}/{x}/{y}.pbf` (au boot) | 200 | 4 tuiles | `mvt_parcels` : 431 663 | **OK** |
| ANRU (île) | `/map/layers.geojson?kind=anru` (sans commune) | 200 | 8 | 8 | **OK** — rendu visible |

`mvt_overlays` total = 6 470 = 6 306 (plu_gpu_zone) + 164 (ppr) : raccord exact avec `spatial_layers`.

## 4.4 — Cohérence inter-couches : 5 parcelles témoins

Comparaison (a) fiche API `GET /parcels/{idu}?source=q_v3_datagap`, (b) MVT en base
(`mvt_parcels.status/tier_v2/rang_v2/etage0`), (c) zonage PLU par intersection
`spatial_layers` kind=`plu_gpu_zone` ∩ `parcels.geom` vs la ligne `zonage_plu_gpu` de la fiche.

| IDU | Commune | Fiche API (statut · tier · rang · etage0) | MVT base | Zonage fiche vs zonage base | Verdict |
|---|---|---|---|---|---|
| 97410000AS1425 | Saint-Benoît | ecartee · brulante · 16 · false | ecartee · brulante · 16 · 0 | fiche « AUc — constructible » ↔ base AUc (AUa5) 100 % | **RACCORD** |
| 97410000CD0905 | Saint-Benoît | ecartee · brulante · 8 · false | ecartee · brulante · 8 · 0 | fiche « AUc » ↔ base AUc (AUb19) 100 % | **RACCORD** |
| 97423000AB1908 | Les Trois-Bassins | ecartee · brulante · 1 · false | ecartee · brulante · 1 · 0 | fiche « AUc » ↔ base AUc (1AUb) 100 % | **RACCORD** |
| 97423000AB1341 (choisie : écartée étage 0, motif risques) | Les Trois-Bassins | ecartee · ecartee · 19 · **true** — HARD_EXCLUDE « PPR zone rouge (inconstructible) » (zones R1 + R2 distinctes, 2 lignes légitimes) | ecartee · ecartee · 19 · 1 | fiche « Zone N PLU — inconstructible (recouvrement **95 %**) » vs base : N (Nco) **47,5 %** + AUc (1AUb) **52,5 %** → **divergence** (voir anomalie A1 : polygone N dupliqué compté deux fois, 47,5 × 2 = 95) | **RACCORD** sur statut/tier/rang/etage0 ; **DIVERGENCE zonage** (le % de recouvrement N est gonflé par un doublon ; la zone majoritaire réelle est AUc). L'exclusion de la parcelle reste fondée (PPR rouge R1/R2 recoupent bien la parcelle en base) |
| 97415000EY1509 (choisie : réserve foncière, Saint-Paul) | Saint-Paul | chaude · reserve_fonciere · 231 138 · false | chaude · reserve_fonciere · 231 138 · 0 | fiche « U — constructible » ↔ base U (U3a) 100 % (N tangent 0,0 %) | **RACCORD** |

Bilan : 5/5 raccord sur statut · tier v2 · rang · étage 0 (API fiche ↔ MVT base, au champ près).
1/5 divergence sur la LIGNE zonage (AB1341) — cause données, pas code de la fiche.

## Anomalies constatées (CONSIGNÉES, non corrigées)

- **A1 — Doublons `plu_gpu_zone` inter-communes (impact scoring)** : 441 géométries présentes
  en double dans `spatial_layers` kind=`plu_gpu_zone` (458 lignes excédentaires sur 6 306) —
  polygones chevauchant une limite communale ingérés une fois PAR commune (ex. zone N « Nco » :
  id 37999 rattachée Saint-Paul et id 1281239 rattachée Les Trois-Bassins, géométries
  strictement identiques, md5 égal). Conséquence observée sur le témoin 97423000AB1341 : la
  cascade somme les deux intersections → fiche « Zone N — recouvrement 95 % » +
  HARD_EXCLUDE zonage, alors que le recouvrement N réel est 47,5 % et que la zone majoritaire
  est AUc 52,5 %. Des HARD_EXCLUDE zonage peuvent donc reposer sur un recouvrement gonflé le
  long des limites communales (l'exclusion d'AB1341 reste fondée par ailleurs : PPR rouge).
  Réparation = dédoublonnage à l'ingestion + re-run cascade → NON TRIVIALE, consignée.
- **A2 — `parc_national` dupliqué ×24** : 72 lignes = les 3 mêmes géométries île entière
  (cœur, aire d'adhésion, aire ouverte à l'adhésion) recopiées pour chacune des 24 communes.
  En mode île, `kind=parc_national` sans commune renvoie les 72 features → chaque polygone est
  dessiné 24 fois (fill-opacity 0.22 empilée ≈ opaque, et payload ×24). En mode commune (3
  features) le rendu est correct. Consignée (dédoublonnage données ou `DISTINCT ON` côté API).
- **A3 — ANRU muet hors des 6 communes NPNRU** : en mode commune Saint-Paul la couche
  s'active, la requête répond 200 avec 0 feature, et rien ne change à l'écran sans aucun
  message. Comportement données-exact mais UX muette (l'utilisateur ne sait pas si la couche
  est vide ou cassée). Mineur, consigné.
- **A4 — `amenite` : 2 subtypes servis hors légende** : le payload Équipements contient 7
  subtypes ; `tcsp` (6 464 à l'île, 43 % du volume) et `commerce` (946) ne figurent ni dans le
  hint du panneau (« mairie · écoles · santé · police/gendarmerie · sport ») ni dans
  `EQUIP_COLOR` (rendus en gris par défaut). Payload plus lourd qu'annoncé, points gris non
  documentés. Mineur, consigné.
- **Note (pas une anomalie)** : Équipements a `minzoom: 13` — au cadrage commune (z < 13)
  l'activation ne dessine rien tant qu'on ne zoome pas (voulu : pas de milliers d'icônes) ;
  le rendu a été vérifié après zoom. De même, « Vue mer » et « Limites parcelles » n'émettent
  aucune requête propre : elles rhabillent la source parcelles déjà à bord (voulu).

## Fichiers produits

- `frontend/qa/audit_couches_m51.mjs` (script d'audit rejouable)
- `reports/m51-unification/audit-couches.csv`
- `reports/m51-unification/audit-couches-net.json` (log réseau brut)
- `reports/m51-unification/captures/couche-{zonage,parcelles,ppr,vue-mer,parc,limites,communes,anru,equipements}.png` + variantes `-ile`
