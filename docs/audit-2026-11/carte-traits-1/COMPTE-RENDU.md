# CARTE-TRAITS-1 — des bandes qui ne sont pas des parcelles

**Mandat.** Autour du 3 chemin de la Citerne, 97417 La Montagne (Saint-Denis), la carte
montre de fines bandes entre la parcelle sélectionnée et ses voisines, comme des
micro-parcelles ; en cliquant dessus, c'est la grande parcelle qui se sélectionne.
Dire ce que sont ces bandes, preuve à l'appui ; corriger ; recette.

**Périmètre.** Branche `fix/carte-traits-1`, worktree `~/Desktop/labuse-carte`, ports
9570 (API) / 6770 (front). Aucun accès prod, aucun merge. **Un seul fichier applicatif
touché** (`frontend/src/components/map/basemaps.ts`) + son test. Rien d'autre que la carte.

---

## 1. Réponse : ce sont un DOUBLE DESSIN (traits du fond ≠ nos traits)

Ni des parcelles cadastrales réelles, ni des interstices du cadastre : **un double tracé**.
Le fond de carte **Plan IGN v2** dessine SON PROPRE parcellaire (traits mauves + numéros de
parcelle) à son dernier niveau de zoom (z19) ; **nous** dessinons AUSSI le cadastre
par-dessus, en vecteur. Les deux tracés **ne coïncident pas** → entre une parcelle et sa
voisine, deux lignes parallèles décalées = la « fine bande » que voit Vic.

Parcelle de Vic : **`97411000BZ1065`** (3 chemin de la Citerne), 1 625 m² (surface
géométrique), centroïde 55,429478 / −20,885194.

### Preuve 1 — le fond IGN dessine ses propres parcelles, au SEUL z19

Tuiles `GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2` tirées en direct de la Géoplateforme, sur la
parcelle de Vic :

| Zoom | Contenu | Capture |
|------|---------|---------|
| z17  | bâti + voirie, **aucun trait de parcelle** | — |
| z18  | bâti + voirie + numéros de voie, **aucun trait de parcelle** | `captures/preuve_IGN_plan_z18_sans_parcellaire.png` |
| z19  | **parcellaire MAUVE + numéros de parcelle** (0391, 1124, 0577, 4bis… = les voisins de Vic) | `captures/preuve_IGN_plan_z19_avec_parcellaire_mauve.png` |

Vérifié aussi en centre dense (Saint-Denis / rue de Paris) : **z18 = pas de parcellaire**
(`captures/preuve_IGN_plan_z18_stdenis_centre_sans_parcellaire.png`). Le parcellaire du
Plan IGN n'apparaît **qu'au dernier niveau de la couche, z19.**

### Preuve 2 — notre tracé, à lui seul, est propre et unique

Fond IGN éteint, à z19 sur la parcelle de Vic : nos limites (`ile-limites`) forment **un
seul maillage net**, sans bande (`captures/preuve_labuse_seul_tracé_unique_crop.png`).
Les bandes n'existent que lorsque le Plan IGN est allumé **et** qu'on atteint z19 — c'est-à-dire
exactement quand les deux parcellaires se superposent.

### Preuve 3 — notre géométrie EST celle de cadastre.gouv (donc ce n'est pas nous qui dérivons)

Comparaison de `parcels.geom` (ce que sert LABUSE) à la géométrie DGFiP servie par
`apicarto.ign.fr/api/cadastre/parcelle` (= cadastre.gouv) pour `97411000BZ1065` :

| Mesure | Valeur |
|--------|--------|
| Aire LABUSE | 1 625,2 m² |
| Aire cadastre.gouv | 1 625,1 m² |
| **Distance de Hausdorff** | **0,007 m (7 mm)** |
| Différence symétrique | 0,38 m² |

Nos deux tracés sont, à 7 mm près, **identiques**. Le tracé qui « bouge » est celui du
**raster IGN** (autre produit cartographique, autre généralisation/calage), pas le nôtre.

### Preuve 4 — pas d'interstices réels : les parcelles se TOUCHENT

Dans `parcels.geom`, les 5 voisines immédiates de Vic la **touchent exactement**
(`ST_Touches = vrai`, distance 0,000 m) — aucun vide, aucune micro-bande dans la donnée.
Et aucun **chevauchement** réel autour d'elle (0 paire > 0,5 m²). La bande n'est donc PAS
une parcelle ni un interstice : c'est un **artefact d'affichage**.

### Preuve 5 — pourquoi le clic « tombe sur la grande parcelle »

Le clic appelle `/parcels/at` → `ST_Contains` sur la **vraie** géométrie (pleine résolution,
SRID 4326). Comme la bande n'est pas une parcelle, le point sous le curseur est à l'intérieur
de la grande parcelle réelle → c'est elle qui est sélectionnée. Le clic était **déjà correct** ;
seul l'affichage mentait.

---

## 2. Correctif (forme carte seule)

`frontend/src/components/map/basemaps.ts` — la source `bm-plan` est **bornée à `maxzoom: 18`** :

```ts
'bm-plan': { tiles: [WMTS('GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2', 'image/png')],
             attribution: '© IGN Géoplateforme — Plan IGN v2', maxzoom: 18 },
```

Le parcellaire IGN n'existant qu'à z19, borner la source à z18 fait que **MapLibre
sur-zoome la tuile z18 (sans parcellaire)** au-delà → le fond **n'affiche plus jamais ses
propres traits de parcelles, à aucun niveau de zoom**. Il ne reste que notre tracé vectoriel
(net). Le bâti / la voirie / les numéros de voie du z18 subsistent (léger sur-zoom ×2 au seul
z19, acceptable). **L'ortho est une photo** (aucun cadastre dans le raster) → non concernée :
c'est le seul fond à borner. `maxBounds` et `maxZoom` (19) de la carte sont inchangés.

Aucune modification du moteur de tuiles, du calcul, du clic, ni de la géométrie servie.

---

## 3. Recette

### Parcelle de Vic — avant / après (z19, fond Plan IGN)

- `captures/vic_AVANT_z19.png` (+ `_crop`) : traits mauves IGN + numéros, **doublés** de nos
  lignes → bandes.
- `captures/vic_APRES_z19.png` (+ `_crop`) : **un seul tracé** (le nôtre), plus aucun trait
  mauve ni numéro de parcelle IGN.

### Trois niveaux de zoom — `captures/vic_APRES_3zooms.png`

z17 / z18 / z19 après correctif, fond Plan IGN : tracé de cadastre **unique** aux trois
zooms. (z17/z18 n'étaient de toute façon jamais affectés — le parcellaire IGN est z19.)

### 10 parcelles témoins, 5 communes — avant / après (`captures/cmp_t*.png`)

| # | IDU | Commune | avant | après |
|---|-----|---------|:---:|:---:|
| 1 | 97422000AD0505 | Le Tampon | bandes | **tracé unique** |
| 2 | 97422000AD0761 | Le Tampon | bandes | **tracé unique** |
| 3 | 97409000AB0243 | Saint-André | bandes | **tracé unique** |
| 4 | 97409000AB0424 | Saint-André | bandes | **tracé unique** |
| 5 | 97411000AB0310 | Saint-Denis | bandes | **tracé unique** |
| 6 | 97411000AD0004 | Saint-Denis | bandes | **tracé unique** |
| 7 | 97415000AC0145 | Saint-Paul | bandes | **tracé unique** |
| 8 | 97415000AD0422 | Saint-Paul | bandes | **tracé unique** |
| 9 | 97416000CO0382 | Saint-Pierre | bandes | **tracé unique** |
| 10 | 97416000CO0935 | Saint-Pierre | bandes | **tracé unique** |

Chaque `cmp_t*.png` juxtapose avant (traits mauves IGN + numéros, doublés) et après (tracé
unique, le parcellaire IGN a disparu). Même résultat dans les 5 communes.

### Preuve réseau — universelle (toute l'île, pas seulement 10 parcelles)

À z19, en relevant les requêtes de tuiles `PLANIGNV2` effectivement émises par le navigateur :

| État | TILEMATRIX demandés |
|------|---------------------|
| **avant** (source non bornée) | **19** et 20 (→ le parcellaire mauve) |
| **après** (`maxzoom: 18`) | **18 seulement** (0 requête à 19) |

Le fond ne **télécharge plus jamais** la tuile z19 qui porte le parcellaire — donc il ne peut
plus l'afficher, nulle part.

### Aucun écart entre le contour affiché et la géométrie API

`captures/api_overlap_vic_crop.png` : la géométrie servie par `/parcels/{idu}/geojson`
(pointillés **rouges**) se superpose **exactement** au contour affiché par la carte (tuiles
MVT) — aucun décalage (< 1 px). Cohérent : à z15 (maxzoom de la source MVT) la géométrie est
servie **sans simplification**, puis sur-zoomée en vecteur → le contour affiché EST la
géométrie API.

### Le clic : une parcelle sous le curseur, une seule ; rien hors parcelle

Sondes sur `/parcels/at` :

| Point | Résultat |
|-------|----------|
| intérieur de Vic | `97411000BZ1065` (la bonne, une seule) |
| intérieur de la voisine BZ0389 | `97411000BZ0389` |
| au large (océan) | `null` (rien) |
| exactement sur la limite partagée | `null` (pas de micro-parcelle fantôme) |

Aucun chevauchement de parcelles autour de Vic → un clic ne peut jamais toucher deux
parcelles. Comportement conforme : un clic sélectionne la parcelle sous le curseur, une
seule ; une zone sans parcelle ne sélectionne rien.

---

## 4. Hook / tests

| Vérif | Résultat |
|-------|----------|
| Scan de secrets | ✓ rien trouvé |
| Front `tsc -b` | ✓ 0 erreur |
| Front `vitest run` | ✓ **304 tests** (303 + 1 verrou ajouté), 64 fichiers |
| Verrou ajouté `basemaps.test.ts` | ✓ `bm-plan.maxzoom === 18` |
| Python unitaires (sans base) | **2882 passés**, 49 ignorés ; 1 échec isolé-vert
  (`test_disque_externe_1::test_vigie_copie_externe…`) = **pollution d'ordre pré-existante**
  (passe seul), hors périmètre (changement 100 % front) |

---

## 5. Fichiers, décisions, dette

**Touchés :**
- `frontend/src/components/map/basemaps.ts` — `bm-plan` → `maxzoom: 18` (+ commentaire).
- `frontend/src/components/map/basemaps.test.ts` — verrou de régression.
- `docs/audit-2026-11/carte-traits-1/` — ce rapport + `captures/`.

**Décision :** on NE remplace pas le Plan IGN par une autre couche (il n'existe pas de « Plan
sans cadastre » chez IGN) et on NE retire pas notre tracé (il est juste, ≡ cadastre.gouv) :
on empêche simplement le fond de servir le niveau qui porte SON cadastre. Le nôtre reste la
seule vérité à l'écran.

**Dette :** merge de `fix/carte-traits-1` par PR (aucun accès prod dans ce mandat).
