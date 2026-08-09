# M13 — LOT D · Couches et carte

Worktree isolé, branche `fix/m13-d-couches`. **Aucun merge. Zéro touche scoring.**
App servie sur `http://127.0.0.1:8033/socle/` (build Vite → `frontend/dist`), captures Playwright
viewport 1440×900 sous `qa/m13/D/`.

Vérif globale :
- `npm run build` → **0 erreur TS**.
- Golden : **116/116 PASS, 0 FAIL** (PYTHONPATH worktree, LABUSE_API_BASE=:8033).

---

## D1 — Panneau Couches OUVERT PAR DÉFAUT (QA-47) — **FAIT / PROUVÉ**

Avant (M12) : tiroir **replié** par défaut + auto-fermeture ~10 s après une sélection de couche.

Après :
- `couchesOpen` initialisé à **`true`** (ouvert dès le chargement).
- Le tiroir se **referme automatiquement** quand `verdict` bascule `false → true`, c.-à-d. au clic
  sur « Afficher l'analyse LABUSE » (`[data-verdict-on]`), pour libérer la place. Un `useRef`
  (`prevVerdict`) ne déclenche la fermeture qu'à la **bascule** : l'utilisateur peut rouvrir
  manuellement ensuite sans être re-fermé.
- **Auto-fermeture 10 s SUPPRIMÉE** : `autoClose` / `onLayerSelected` / la prop `onSelected`
  retirés (`LayersSection`, les 2 usages desktop + mobile, et le `onClick` des cases). C'est la
  règle « analyse affichée → couches repliées » qui remplace la temporisation.

Fichier : `frontend/src/components/panel/LeftPanel.tsx`.

PREUVES :
- `qa/m13/D/d1_couches_ouvert.png` — au chargement, la liste des couches est dépliée
  (Parcelles, Limites, Zonage…, PPR, Équipements, etc. visibles).
- `qa/m13/D/d1_couches_referme.png` — après clic « Afficher l'analyse LABUSE », le tiroir est
  replié (seul l'en-tête « Couches » + chevron subsistent) et les résultats de l'analyse s'affichent.
- Assertions Playwright : liste visible au load = `true` ; après verdict = `false` ; bandeau
  « Analyse LABUSE affichée » = `true`.

## D2 — Bulles « i » au premier plan et ENTIÈRES (QA-48) — **FAIT / PROUVÉ**

Avant : la bulle, `position:absolute` DANS le panneau, était **rognée** par le bord du panneau et
par le conteneur `overflow-y-auto` de la liste (« sans découp… »).

Après : `Tip` (composant unique de toute l'app) réécrit —
- la bulle est rendue dans un **PORTAL** sur `<body>`, en `position:fixed`, `z-[9999]` :
  **au-dessus de tout**, jamais rognée par un ancêtre `overflow`/le bord du panneau ;
- **repositionnement automatique** : ancrage calculé sur le rect du déclencheur, recentrage
  horizontal borné à l'écran (marge 8 px), bascule haut↔bas si le côté demandé déborde ;
  recalcul au scroll/resize ;
- comportements de déclenchement conservés : survol souris (apparition/disparition), focus
  clavier, tap mobile (toggle), fermeture au tap extérieur + minuterie 4 s, largeur max 260 px,
  style `.floating` inchangé.

Fichier : `frontend/src/components/Tip.tsx`. Impacte **tous** les tooltips de l'app (uniformément
au premier plan) — aucun autre appelant modifié.

PREUVES :
- `qa/m13/D/d2_bulle_entiere.png` — bulle « i » de « Zonage PLU (zones officielles) » affichée
  complète, débordant sur la carte à droite (donc non contrainte par le panneau).
- `qa/m13/D/d2_bulle_entiere_crop.png` — recadrage serré : texte **entier**, se termine bien par
  « … non rattaché aux parcelles. » (plus de troncature).
- Playwright : `boundingBox` de la bulle = `{x:205, w:260, h:210}`, entièrement dans le viewport
  (bord droit 465 < 1440, x ≥ 0).

## D3 — Icônes équipements ×1,5 (QA-49) — **FAIT / PROUVÉ**

Rampe `icon-size` de la couche `ov-equip` multipliée par 1,5, comportement au zoom (M12 C3)
conservé (rampe croissante continue jusqu'à z20) :

| zoom | M12 (avant) | M13-D (×1,5) |
|------|-------------|--------------|
| 12   | 0,30        | **0,45**     |
| 15   | 0,55        | **0,825**    |
| 17   | 0,85        | **1,275**    |
| 20   | 1,30        | **1,95**     |

Fichier : `frontend/src/components/map/MapView.tsx` (couche `ov-equip`).

PREUVES :
- `qa/m13/D/d3_equipements.png` + `d3_equipements_zoom.png` — carte avec couche « Équipements »
  active (Saint-Denis), pastilles/pictogrammes visibles.
- Avant/après à vue **identique** (même commune, même zoom) :
  `qa/m13/D/d3_equipements_avant.png` (rampe M12) vs `qa/m13/D/d3_equipements_apres.png` (×1,5) —
  les pastilles sont nettement plus grandes après.

## D4 — « Zonage PLU (zones officielles) » : à quoi sert-elle ? (QA-50 — AUDIT, PAS de suppression)

**Rien supprimé.** Audit + réécriture du texte « i ».

### Ce que fait exactement la couche
Toggle `zonage`. Elle demande `GET /map/layers.geojson?kind=plu_gpu_zone[&commune=…]`
(`getMapLayer('plu_gpu_zone')`, actif uniquement hors mode île) et rend les **polygones de zones
PLU bruts** en fond translucide (calque `ov-zonage`, fill-opacity 0,10 ; U en vert `#5CE6A1`,
autres en brun `#8a6b3f`). En mode île, le même contenu passe par des tuiles vectorielles
(`ovmvt-zonage`, source-layer `plu_gpu_zone`).

### Source
Table `spatial_layers` **`kind='plu_gpu_zone'`** = les zones telles que **déposées par la commune
sur le Géoportail de l'urbanisme (GPU)**. Ce sont les géométries d'origine du document opposable :
leurs contours **ne suivent pas** le découpage cadastral.

### Différence avec les deux autres couches de zonage (PAS un doublon)
- **`zonage` — « Zonage PLU (zones officielles) »** : polygones GPU **bruts**, non rattachés aux
  parcelles. Montre le zonage tel que publié (contours d'origine).
- **`zonage_parcelle` — « Zonage PLU (par parcelle) »** : **chaque parcelle** est recolorée selon
  sa zone **dominante** (table dérivée `parcel_zone_plu`, calculée par intersection de surface),
  avec le **code exact** de la zone (« U1a », « 1AUc ») en étiquette au zoom et au clic.
- **`zonage_colorise` — « Colorisation par type de zonage »** : teinte **toutes les parcelles d'un
  coup** par famille de zone (U/AU/A/N), sans clic — lecture d'ensemble.

Les trois partagent la **même donnée source** (`plu_gpu_zone`) mais **trois représentations
distinctes et complémentaires** : polygone officiel brut / parcelle + code précis / aplat par
famille. **Pas un doublon** → conservée.

### Texte « i » appliqué (`LAYER_INFO.zonage`, `frontend/src/lib/layers.ts`)
> Les zones du PLU telles que déposées officiellement par la commune sur le Géoportail de
> l'urbanisme (source GPU) : les grands aplats de couleur, avec leurs contours d'origine — qui ne
> suivent pas forcément le découpage cadastral. C'est le document opposable de référence. À la
> différence de « Zonage PLU (par parcelle) » (qui colore chaque parcelle et affiche son code de
> zone au clic) et de « Colorisation par type de zonage » (qui teinte toutes les parcelles d'un
> coup), cette couche montre le zonage brut, non rattaché aux parcelles.

---

## Récap preuves
| Point | Statut | Captures |
|-------|--------|----------|
| D1 | FAIT / PROUVÉ | d1_couches_ouvert.png, d1_couches_referme.png |
| D2 | FAIT / PROUVÉ | d2_bulle_entiere.png, d2_bulle_entiere_crop.png |
| D3 | FAIT / PROUVÉ | d3_equipements.png, d3_equipements_zoom.png, d3_equipements_avant.png, d3_equipements_apres.png |
| D4 | FAIT (audit + texte i, aucune suppression) | (réponse ci-dessus) |
