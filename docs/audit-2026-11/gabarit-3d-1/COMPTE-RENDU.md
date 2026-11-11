# GABARIT-3D-1 — pilote (étape 1 : serveur) — compte-rendu

Branche `feat/gabarit-3d-1`. Pilote : le terrain réel, le bâti, deux coupes. Aucun merge, aucun accès
prod. **Aucun chiffre servi ne change** (bancs Gabarit verts, chiffres du Gabarit identiques — prouvé).
La vue 3D actuelle reste la vue par défaut ; le pilote vit derrière un **interrupteur réservé aux admins**.
**Aucun plafond de hauteur n'est dessiné** (les hauteurs en pente sont le mandat suivant).

> Les §1–§9 décrivent l'étape 1. Le **§10** consigne la **revue d'Astra (étape 1 bis)** et FAIT FOI
> pour la scène et les coupes (surface de référence, trois contours, indicateurs, thèmes, contrôle C).

---

## 1. L'existant, en une page

Le Gabarit est un volume **à plat**, sans relief. Six fichiers le portent.

- **`frontend/.../outils/Gabarit.tsx`** — l'outil. Appelle `GET /outils/gabarit/{idu}`, affiche ce que le
  moteur sert (zéro recalcul). `useMapLayers` pose sur MapLibre : zone (vert), reculs (ambre), exclusions
  (rouge), contour, bâti existant (gris). En 3D : `fill-extrusion` de la zone à `hauteurReglementaireM`
  et du bâti à sa hauteur mesurée — **extrusion posée à plat** (`terrainNote` le dit). Bascule 2D/3D,
  export PDF.
- **`frontend/.../map/MapView.tsx`** — la carte. Une source DEM existe (`raster-dem` terrarium AWS,
  exagération 1,35×) MAIS **le relief est explicitement désactivé en mode Gabarit** (`setTerrain(null)`,
  `gabaritFlat`). Motif documenté (R13) : une parcelle en altitude/pente **flottait hors champ** une
  fois le relief posé à pitch 45 (cas cité : « 36 Rue des Jacarandas », Saint-Paul, « ~760 m »). Le
  Gabarit est donc seul propriétaire de la caméra et pose un terrain plat. Cadrage `fitBounds` (3D :
  pitch 45, bearing 0, padding 70).
- **`gabarit/plan_svg.py`** — deux SVG serveur **miroir de l'écran** : `gabarit_svg` (plan 2D) et
  `gabarit_svg_3d` (**axonométrie** isométrique, sol **plat**, légende « Volume indicatif — terrain
  supposé plat »). L'enveloppe y est réduite à l'aire du **plafond d'emprise** (`_emprise_env`, érosion
  métrique).
- **`exports/blocs/gabarit.py`** — le bloc PDF (Dossier / Pré-dossier PC) : plan 2D, chiffres, règles
  appliquées / non intégrées, puis une page « Vue 3D » (l'axonométrie ci-dessus). 2D seulement.
- **`implantation/contexte.py`** — le voisinage de la planche plan-masse : parcelles/bâti/voies voisins,
  TN **au LiDAR RGE ALTI 5 m** aux 4 angles, et surtout **l'axe de coupe perpendiculaire à la voie**
  (`_axe_coupe`, origine côté voie → intérieur) + un profil TN **à 16 points**. C'est la graine de la
  coupe « accès » du pilote (réutilisée).
- **`faisabilite/profil_altimetrique.py`** — la coupe altimétrique live : lit le raster RGE ALTI 5 m
  **en base** (`rgealti_mnt_5m`) puis **complète au service IGN** ; `stats_profil` (dénivelé ±, pente
  moyenne/max). Pas 5 m.

**L'écart écran / PDF.** À l'écran, la **zone entière** est extrudée (fill-extrusion de
`zoneImplantationGeoJSON`). Au PDF, l'axonométrie extrude un **socle réduit au plafond d'emprise**
(`_emprise_env`). Les deux sont à plat, mais ne montrent pas le même volume : l'écran = la zone ;
le PDF = l'emprise constructible. Le pilote réunit les deux sources de vérité sous **une scène unique**.

**Constat données.** Le MNT 5 m local (`rgealti_mnt_5m`) ne contient que **2 tuiles** : les altitudes
viennent en réalité du **service IGN en ligne**. Aucun fond 1 m n'existait.

---

## 2. Ce qui a été construit (serveur)

| Pièce | Fichier | Rôle |
|---|---|---|
| Fond 1 m | `scripts/gabarit_3d_fond.py` → `data/mnt1m/fond_1m.tif` (+`.meta.json`) | COG LiDAR HD MNT 1 m, EPSG:2975, REUN89 |
| Scène | `src/labuse/gabarit/scene.py` | terrain, limite, zone, bâtiments, règles, 2 coupes, métadonnées, id |
| Coupes SVG | `src/labuse/gabarit/coupe_svg.py` | 2 coupes vectorielles + plan-clé (axes reportés) |
| Endpoints | `src/labuse/api/gabarit.py` | `GET …/scene/{idu}`, `…/coupe/{A\|B}.svg`, `…/plan.svg` (**admin**) |
| PDF | `src/labuse/exports/blocs/gabarit.py` | section pilote **gated** `ctx['scene3d']` (défaut inchangé) |
| Config | `src/labuse/config.py` | `mnt1m_cog_path` / `LABUSE_MNT1M_COG_PATH` |
| Témoins + contrôles | `scripts/gabarit_3d_temoins.py` | coupes SVG(clair+sombre)+PNG, plan, recette D, contrôles a/b/c/C |
| Tests | `tests/test_gabarit_scene.py` | 13 tests (surface bilinéaire, trous, indicateurs, cadre, thèmes, gating, invariant) |

La **scène** lit le `GabaritResult` SERVI par `gabarit_detail` (chiffres repris tels quels) + le fond 1 m.
Écran (étape 2) et PDF lisent la même scène. Tout est **offline** (COG local + base ; aucun appel réseau,
aucun GPU) — prouvé en coupant le réseau pendant le rendu PDF (`docs/.../pdf/bz1065_pilote.pdf`, 27,5 Ko).

---

## 3. Le fond d'altitudes 1 m

**Disque libre mesuré : 13 GiB (partagé avec d'autres sessions).** L'île entière à 1 m (~2 500 dalles
LiDAR HD) ne tient pas raisonnablement. **Décision (validée) : fond sur les voisinages des parcelles
témoins + extrapolation.**

### Source retenue — LiDAR HD MNT 1 m

Couche `IGNF_LIDAR-HD_MNT_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S` (mission `23LHDREUNION`, acquise
**août 2023**), tirée par WMS en GeoTIFF Float32. Comparaison mesurée sur BZ1065 (talus) :

| Comparaison | écart moyen | écart-type | |·|max |
|---|---|---|---|
| RGE ALTI **HIGHRES** − LiDAR HD MNT | −0,09 m | 0,74 m | 6,8 m |
| RGE ALTI **standard 5 m** − LiDAR HD MNT | +2,76 m | 5,01 m | 26,5 m |
| 1 m IGN − (0,50 m natif moyenné 2×2) | 0,000 m | 0,000 m | 0,000 m |

→ **Le RGE ALTI « HIGHRES » DÉRIVE du LiDAR HD** (même produit à 1 m) ; le RGE ALTI standard est le vieux
5 m rééchantillonné (σ≈5 m) ; le 1 m IGN est **exactement** la moyenne 2×2 du 0,50 m natif. On retient le
LiDAR HD MNT (produit natif de La Réunion, RGR92/UTM40S + REUN89). Le WMS tague EPSG:32740 alors que la
grille est en coordonnées 2975 au pixel près → **ré-étiquetée 2975** (écart RGR92↔WGS84 < 1 m).

### Taille réelle + extrapolation

- **Fond construit : 2,93 Mo** (COG unique, sparse, 0,79 Mpx de données) — **3,74 octets/m² compressé**.
- Extrapolation (couverture 1 m pleine) : **3 communes (508 km²) ≈ 1,9 Go** ; **île (2 512 km²) ≈ 9,4 Go**.
- Référentiel : **RGR92 / UTM 40 Sud (EPSG:2975)** en planimétrie, **REUN89 (IGN 1989)** en altitude.
- Lacunes : nodata −9999 (hors emprise mission). Ocean ≈ 0 (retour d'eau), **pas** une lacune.

### La scène

Endpoint `GET /outils/gabarit/scene/{idu}` (admin). En mètres autour d'une origine locale (coin SW de la
bbox parcelle, 2975) : **terrain** (grille 1 m sur parcelle+accès, grille 2 m sur ~150 m de voisinage),
**limite**, **zone d'implantation**, **reculs**, **exclusions**, **bâtiments** (empreinte + hauteur +
provenance `mesurée`/`estimée` + altitude de base), **règles en données** (reprises telles quelles),
**métadonnées** (produit, pas, référentiel, acquisition, lacunes) et un **identifiant de scène** stable
(hash parcelle + chiffres servis + signature du fond).

---

## 4. Les deux coupes

SVG **vectoriel serveur** (`coupe_svg`). Pas de 1 m. **Échelle horizontale = verticale (1:1, aucune
exagération)** ; graduations + barre visibles ; altitude REUN89. Tracées : profil, **limites**
parcellaires, **étendue de la zone d'implantation**, **bâtiments coupés** (hauteur + provenance),
**cotes** (altitudes, dénivelé, pente moyenne/max). Une coupe **s'interrompt au droit d'une lacune**
(profil par morceaux ; pente/dénivelé calculés **par morceau**, jamais à travers le trou). **Aucun
plafond de hauteur dessiné.** L'**axe est reporté sur le plan-clé** (`plan.svg` : parcelle + zone + A-A'/B-B').

- **Coupe A-A'** : sens de la **plus grande pente** (plan ajusté aux pixels du fond sous la parcelle).
- **Coupe B-B'** : **de la voie vers la parcelle**, par l'accès identifié (axe `implantation.contexte`,
  étendu de 25 m côté voie pour partir de la chaussée).

---

## 5. Contrôles — trois conclusions séparées

### (a) Exactitude sur plan incliné synthétique — `controles/a_plan_synthetique.*`
Plan `z = 100 + 0,10·x − 0,04·y` (pente 10,77 %), échantillonné 1 m **au centre des pixels**, avec une
bande nodata :
- **altitudes : erreur max 0,000 m**, moyenne 0,000 m (échantillon au centre = valeur exacte du plan) ;
- **pente le long de x : 10,0 % mesurée = 10,0 % attendue** ; raccords continus (pas constant 1 m) ;
- **lacune** : la bande coupe le profil en **2 morceaux** ; la pente est calculée **par morceau**.
- **50 cm → 1 m sur le talus BZ1065** : le 1 m = moyenne 2×2 du 0,50 m. ⚠ **Lecture corrigée en
  étape 1 bis (§10, contrôle C)** : le « 0,92 m » annoncé ici était l'étendue pic-à-pic des sous-pixels
  (dispersion interne), PAS l'écart de cote introduit par le 1 m. Mesuré le long des MÊMES axes, l'écart
  réel 1 m↔0,50 m est **décimétrique** (BZ1065 médiane 0,107 m, p95 0,50 m).

### (b) Cohérence LiDAR HD ↔ RGE ALTI — `controles/b_coherence_lidar_rgealti.json`
Aux centroïdes témoins, par type de terrain : COG LiDAR HD vs service RGE ALTI IGN.

| type | COG LiDAR | RGE ALTI service | écart |
|---|---|---|---|
| plate (≈plat) | 5,58 | 5,19 | +0,39 |
| alt760 (pente douce) | 594,92 | 594,85 | +0,07 |
| bz1065 (talus) | 400,97 | 401,09 | −0,12 |
| cotier (falaise) | 42,23 | 41,87 | +0,36 |

**Écart absolu max 0,39 m, moyen 0,23 m.** Le service RGE ALTI de La Réunion **dérive du LiDAR HD**
(écarts décimétriques, toutes pentes) ; la couche RGE ALTI historique 5 m, elle, s'écarte de plusieurs
mètres (cf. §3). Les deux produits « 1 m » sont donc cohérents car c'est **le même**.

### (c) Contrôle indépendant — `controles/c_controle_independant.json`
**Aucun.** Aucune cote publique INDÉPENDANTE ne coïncide avec un point témoin au même endroit ET au même
référentiel (REUN89) : service RGE ALTI et WMS LiDAR HD sont la même source (donc pas indépendants) ; les
repères de nivellement IGN existent mais aucun ne tombe au pixel d'un témoin. Conformément au mandat :
il n'y en a pas, et on le dit.

---

## 6. Témoins — `coupes/` `plan/`

| Témoin | Parcelle | Terrain (mesuré) |
|---|---|---|
| plate | `97415000CY0196` (Saint-Paul) | plaine littorale, ~5 m, faible relief |
| cotier | `97413000CA0057` (Saint-Leu) | **falaise** 47 m → niveau mer (coupe B : pente 409 %) |
| alt760 | `97415000CM1658` (Saint-Paul) | « 36 Rue des Jacarandas » — **~595 m mesurés** (le « ~760 m » du commentaire MapView était approximatif) |
| talus | `97411000BZ1065` (Saint-Denis) | talus, dénivelé ~12 m, pente moyenne 27 % (témoin CDC) |
| pente synthétique | — | contrôle (a) : plan 10 %, lacune, exactitude 0,000 m |

Pour chaque témoin réel : coupe A + coupe B (SVG + PNG) et plan-clé (axes reportés). `synthese.json`
regroupe tout. Pas de vraie lacune dans les fenêtres téléchargées (le fond couvre tout) ; la branche
lacune est prouvée rigoureusement par le contrôle (a) et par la falaise côtière.

---

## 7. Reproduire

```bash
# venv partagé : ../labuse/.venv ; base : postgresql+psycopg://openclaw@localhost:5432/labuse
../labuse/.venv/bin/python scripts/gabarit_3d_fond.py            # construit data/mnt1m/fond_1m.tif (~1 min, WMS)
PYTHONPATH=/tmp/gab3d_libs:src ../labuse/.venv/bin/python scripts/gabarit_3d_temoins.py   # coupes + contrôles
PYTHONPATH=src ../labuse/.venv/bin/python -m pytest tests/test_gabarit_scene.py -q        # 9 tests
```
`cairosvg` (SVG→PNG) est installé **isolément** dans `/tmp/gab3d_libs` (le venv partagé n'est pas modifié).
Le COG est **hors-git** (`data/*`) ; sa taille réelle est reportée ci-dessus et dans `fond_1m.meta.json`.

## 8. Vérifications

- **Chiffres identiques** : test `test_scene_ne_change_aucun_chiffre_servi` (base réelle) — `scene.regles`
  == `gabarit_detail` (zone, plafond, hauteur, surface). ✅
- **Bancs Gabarit** : 288 tests unitaires + 2 db verts, inchangés. ✅
- **Pilote gated** : le PDF par défaut ne contient pas la section 3D (test). ✅ Endpoints **admin**. ✅
- **Offline** : PDF rendu réseau coupé. ✅ **Aucun plafond de hauteur dessiné** (test). ✅

## 9. Réserves / points ouverts

- Étendue du fond = voisinages témoins (pas les 3 communes) — décision disque ; extrapolation donnée.
- CRS WMS tagué 32740 → ré-étiqueté 2975 (écart RGR92↔WGS84 < 1 m, acceptable pilote ; à affiner si besoin).
- Altitude de base des bâtiments = altitude au centroïde (suffisant pour la coupe ; min d'empreinte possible).
- **Étape 2 (visionneuse Three.js, interrupteur front, mesures Safari) non faite** — sur feu vert de Vic.
- Les PNG/PDF des coupes sont normalement exclus par `.gitignore` (`docs/audit-*/**/*.png|pdf`,
  anti-bloat) ; comme le mandat les demande explicitement « en SVG **et** PNG », ils sont ajoutés en
  `git add -f` (chacun < 45 Ko). Le COG, lui, reste hors-git.

---

## 10. Étape 1 bis — revue d'Astra appliquée

Même branche, avant la visionneuse. La maquette « 13-coupe-cible » n'est qu'une direction graphique
(ses longueurs étaient fausses) ; seules les règles ci-dessous font foi.

### A. La scène
- **Trois contours distincts**, trous et parties multiples conservés : `contour_cadastral` (parcels),
  `contour_gabarit` (contour étudié), `zone_implantation` (`_polys_local` → `{ext, trous}`).
- **Une seule surface de référence** `SurfaceReference` : patchs **bilinéaires** sur le MNT 1 m
  (= triangulation par maille ; raccords 1 m/2 m et lacunes définis). Les profils sont calculés **par
  intersection** avec elle. ✅ Test : une **coupe oblique** (37°) décalée des centres de pixels rend la
  **pente constante** d'un plan (écart 0,0).
- **Axe B** : porte l'identité de la voie, son **point d'intersection vérifié** (`intersection_d`) et le
  **statut d'accès** ; sans intersection établie → « coupe orientée vers la voie », **sans voie dessinée**.
  **Axe A renommé « pente dominante »**.
- **État et identifiant exposés séparément** : `etat = {gabarit, terrain_couverture, fond_disponible,
  coupes[]}` ; **jamais « disponible » avec des grilles vides** (`disponible = fond ∧ couverture>0`).
  `scene_id` = hash du **contenu** + des **sources versionnées**. Scène **déterministe** : ✅ l'export se
  reproduit **après purge du cache** (SVG et `scene_id` identiques — recette D2).
- **Bâtiments** (règle précisée) : la hauteur LiDAR est un **faîtage PAR PARCELLE**, donc attribuable à
  l'emprise dessinée **seulement si la parcelle ne porte qu'UN SEUL bâtiment** → cotée « mesurée
  (LiDAR) ». Si elle en porte **plusieurs**, **aucun n'est coté** : volume schématique (contour tireté)
  + mention « **hauteur non attribuée** ». Même règle pour les bâtiments voisins (le pilote n'en rend pas
  encore ; la règle s'applique au nombre de bâtiments de LEUR parcelle). BD TOPO → « estimée », schématique
  non coté. **Pied aux DEUX rencontres** (amont/aval). Témoins : **alt760 (1 bâti) coté « mesurée (LiDAR) »**,
  **bz1065 / plate (plusieurs) → « hauteur non attribuée »**. Test `test_bati_cote_seulement_si_un_seul_batiment`.

### B. Les coupes (SVG serveur, `coupe_svg`)
- **Cadre** : l'extent vertical inclut terrain, pieds **et sommets de bâti** + marges ; **rien ne
  déborde** (test automatique, 0 faute sur tous les témoins) ; **flèches dessinées en tracés**.
- **Échelle** : « H = V · sans exagération verticale » + **barre graphique** ; échelle **chiffrée dans
  le PDF seulement** (`largeur_mm=170`).
- **Intervalles** : traversées parcelle et zone en **bandes cotées sous le profil, par tronçon**.
- **Traits N&B** : terrain plein (mesuré), **reconstitué en tirets** si trou ≤ 3 m bordé d'appuis,
  **lacune ouverte** sinon, limites en trait fin, **aplat léger** pour le bâti coupé.
- **Cotes au décimètre**, « Altitudes en m, IGN 1989 » **une fois**, **aux points vérifiés seulement**
  (voie si établie, limites, haut/bas, pieds amont/aval) ; cote au support incertain **omise**.
- **Indicateurs par traversée** : pente entre limites (signée, avec sens) **et** amplitude **séparément** ;
  **pente max sur 5 m** (fenêtre entièrement valable, dans la parcelle, hors bâti, **emplacement reporté**
  sur le dessin) ; **pente d'accès** seulement si la voie est établie.
- **Thèmes** : **clair** (PDF) / **sombre** (écran), même contenu.

### C. Résolution — `controles/C_resolution_georef.json`
- **1 m vs 0,50 m sur les témoins en pente, mêmes axes** : écart de cote **décimétrique** — BZ1065
  médiane **0,107 m** / p95 0,50 m / max 0,56 m ; cotier (falaise) médiane 0,11 m / p95 1,09 m (le 0,50 m
  résout mieux la crête de falaise). Le 1 m conserve la forme et les cotes utiles.
- **Géoréférencement** : l'altitude en un point est **invariante** par le cadrage de la fenêtre WMS
  (écart **0,06 m** entre deux fenêtres décalées) → fenêtres bien calées sur la grille native.
- **Correction du 0,92 m** : voir §5(a) — le 0,92 m était une dispersion intra-pixel, pas l'écart réel.

### D. Recette — `recette/`
- Bâtiment sur **coupe plate**, toit **cadré** ✅ (test). Parcelle **multi-tronçons** (BZ1065 coupe B :
  traversées 31,9–50,8 m et 61,7–94,6 m) ✅. **Lacune sous bâti** : bâti dessiné, lacune **ouverte**
  dessous, cotes omises ✅. **Reproductibilité après purge du cache** ✅.
- **Test automatique** : aucun élément hors cadre ; chaque repère vérifié a son libellé.
- Coupes témoins en **SVG (clair + sombre) et PNG** dans `coupes/`, plan-clé dans `plan/`.

Vérifs étape 1 bis : 13 tests `test_gabarit_scene.py` ✅ ; 292 unit + 2 db gabarit inchangés ✅ ;
invariant « chiffres identiques » + déterminisme (base réelle) ✅ ; PDF pilote (clair) rendu offline ✅.
