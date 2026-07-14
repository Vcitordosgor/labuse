# M6.1 — items 1+2 : couches carte « Zonage PLU (parcelles) » & « 50 pas géométriques »

Branche `feat/m61-couches` (rebased sur main) — run servi **q_v5_m6b** partout (vérifié).
Livré le 14/07/2026. E2E `frontend/qa/m61_couches.mjs` : **29/29 PASS**.

## Item 1 — Zonage PLU (parcelles)

### Données
- Table dérivée **`parcel_zone_plu`** (`idu` PK, `zone_lib`, `zone_fam`) : la zone PLU
  **dominante par surface d'intersection** (spatial_layers `kind='plu_gpu_zone'`, 5 848 zones
  dédoublonnées M6-2b, `ST_MakeValid`). **427 419 / 431 663 parcelles zonées** (99,0 %) —
  U 306 630 · A 73 946 · N 36 306 · AU 10 537. Build one-shot ~23 min, intégré à
  `labuse build-mvt` (construit si absente, réutilisée ensuite : le zonage ne bouge pas
  avec les runs de scoring).
- **`zone_lib` = code court** (« U1e », « 1AUc », « Ud », max 9 caractères) : le champ `name`
  du GPU est hétérogène selon les communes — code nu (Saint-Paul), « Ud : libellé long »
  (Saint-Denis), phrase entière sans code (Bras-Panon). Normalisation prudente : 1er token si
  reconnaissable comme code de la famille, **sinon la famille seule** — jamais une phrase en
  étiquette carte. `zone_fam` = famille dérivée du typezone (AU*→AU, U*→U, A, N, sinon autre).

### Surfaces servies
- **Commune (GeoJSON)** : jointure live `parcel_zone_plu` dans `_q_v2_geojson`
  (coût mesuré : 82 ms sur les 51 129 parcelles de Saint-Paul — noyé dans la sérialisation
  géométrie préexistante).
- **Île (tuiles MVT)** : `mvt_parcels` reconstruite (431 663 parcelles, label **q_v5_m6b**)
  avec `zone_fam` dès z9 (tuiles maigres — c'est la couleur) et `zone_lib` en tuiles pleines
  (z12+). Surcoût mesuré à Saint-Denis : z9 5 441 vs 5 104 Ko (**+6,6 %**),
  z13 1 257 vs 1 215 Ko (**+3,5 %**) — zéro dégradation perceptible en navigation
  (E2E : saut île + idle 2,7 s couche ON, même pipeline de tuiles).
- **`/map/tiles/meta`** (nouveau) : `{run_label, zonage_parcelle}` — le front vérifie que les
  tuiles servies portent le zonage avant d'appliquer le remplissage en mode île (repli toast
  honnête sinon ; jamais déclenché depuis le build, garde-fou conservé).

### Front
- Case « Zonage PLU (parcelles) » dans le panneau Couches.
- Remplissage par famille — palette **distincte du verdict v2** :
  U rose `#E8579B` · AU violet `#9F6BF0` · A jaune-vert `#C9D44B` · N vert forêt `#3E8E6E`
  · autre gris `#8A94A6` ; hors zonage GPU = trame quasi éteinte (opacité 0,06).
  La couche prime sur le verdict tant qu'elle est active ; toggle off = verdict restauré
  à l'identique (E2E).
- Étiquette de la zone **précise** (`zone_lib`) au **zoom ≥ 16**, commune ET île
  (160 étiquettes rendues à l'écran en commune, 635 en île — assertions E2E), + **popup au
  clic** (« Zone Ncor · zonage PLU (GPU) · famille N ») — la fiche s'ouvre normalement.
- **Légende dédiée** (« ZONAGE PLU (PARCELLES) », 5 familles) quand la couche est active —
  la vignette VERDICT reste intacte au-dessus.

## Item 2 — 50 pas géométriques
- `kind='cinquante_pas'` ajouté à la whitelist `/map/layers.geojson` — 163 polygones
  (`commune IS NULL` → servis île entière, mode commune inclus). NB : géométrie ingérée =
  corridor ±90 m autour de la limite haute DEAL (approximation documentée LOT 6).
- Case « 50 pas géométriques », tooltip métier exact :
  « Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer) ».
- Style distinct : remplissage cyan côtier `#4CC3E8` léger (0,16) + **contour tireté** —
  une bande littorale, pas une couche de zonage pleine. Rappel dans la légende quand active.
- **Toast état-vide** (pattern ANRU) : « Aucune bande des 50 pas géométriques sur Salazie —
  commune sans littoral. » (test sommet-dans-bbox de la commune, suffisant pour des bandes
  qui longent le rivage).

## Correctif au passage (préexistant, bloquant pour l'item 1)
- **Hôte glyphs Carto corrigé** dans le style MapLibre :
  `basemaps.cartocdn.com/gl/<style>/{fontstack}/{range}.pbf` répondait **404 sans CORS**
  → **aucun calque symbol ne rendait** (silencieux). Corrigé vers
  `tiles.basemaps.cartocdn.com/fonts/…` (vérifié 200 + Access-Control-Allow-Origin).
  Effet de bord positif : les pastilles « #rang » M5.1 rendent désormais réellement.

## Garde-fous (vérifiés après le build final)
- `mvt_meta.run_label` = **q_v5_m6b** ✓ (build-mvt lit la constante `Q_A_RUN_LABEL`).
- `tests/test_run_serving_coherence.py` : **3/3 PASS** (front SOURCE, bundle dist, tuiles).
- ⚠ Le cache LRU de tuiles vit dans le process API : **redémarrer l'app après un build-mvt**
  (vécu pendant la QA : tuiles pré-normalisation servies depuis le cache).

## Captures (`captures/`)
- `item1-zonage-commune-vue.png` — recoloration par famille, Saint-Paul z12.4, légende dédiée.
- `item1-zonage-commune-z16-etiquettes.png` — étiquettes de zone précises z16.6.
- `item1-zonage-commune-popup-clic.png` — popup zone au clic.
- `item1-zonage-ile-vue.png` / `item1-zonage-ile-z16-etiquettes.png` — mode île (tuiles).
- `item2-50pas-commune-littoral.png` — bande littorale Saint-Paul z14.2.
- `item2-50pas-salazie-toast.png` — toast état-vide commune sans littoral.
- `item2-50pas-ile.png` — 50 pas en mode île.
