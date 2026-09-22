# RAPPORT — 3.D Volume constructible 3D (rapport de faisabilité + livraison)

> Brief 3.D : **rapport de faisabilité d'abord** (techno de rendu), **effort plafonné**
> (v1 = simple extrusion de l'emprise à la hauteur PLU, pas de modélisation fine). 284 tests verts.

## 1. Rapport de faisabilité — quelle techno de rendu ?

| Option | Verdict |
|---|---|
| **Three.js** | Scène 3D complète. **Surdimensionné** pour une simple extrusion ; ~600 ko à vendoriser. |
| **deck.gl** (PolygonLayer extrudé) | Excellent pour l'extrusion, mais lourd (+ fond de carte WebGL) ; gros vendor. |
| **MapLibre GL JS** (`fill-extrusion`) | Vrai 3D navigable, mais **remplacer Leaflet** (le fond carto) = chantier disproportionné pour une v1. |
| **Axonométrie SVG (maison)** ✅ | **Zéro dépendance**, offline-safe, ~50 lignes. Cohérent avec la contrainte du projet (*« Leaflet VENDORISÉ… un CDN bloqué rendait l'app noire »*). Suffit pour « emprise × hauteur posée sur la parcelle ». |

**Décision : axonométrie SVG, v1.** On extrude l'emprise constructible à la hauteur PLU dans une
projection isométrique calculée côté client — aucune librairie 3D, aucun appel réseau, rien à
vendoriser. **Chemin d'évolution** documenté : si Vic veut un 3D navigable (rotation, ombres
réelles), bascule vers MapLibre `fill-extrusion` (le payload `volume3d` fournit déjà l'empreinte +
la hauteur — la donnée ne changera pas, seul le moteur de rendu).

## 2. Livraison
- **Capacité** : le moteur expose désormais `hauteur_m` (= niveaux × hauteur d'étage) et
  `hauteur_etage_m` dans la fourchette — la hauteur devient une **sortie de capacité** de plein droit.
- **`volume3d_payload`** (faisabilité) : empreinte **parcelle** + **emprise constructible insetée
  du recul**, renvoyées en **mètres locaux** (EPSG:2975 recentré sur le centroïde → prêtes pour
  l'axonométrie, sans reprojection front) ; + `volume_m3 = emprise × hauteur`. Isolé/défensif :
  ne casse jamais la fiche ; non constructible → pas de gabarit (jamais de volume inventé).
- **Fiche** : bloc 3D dans la section capacité — gabarit doré extrudé sur la parcelle (sol +
  murs ombrés triés en profondeur + toiture), avec **volume (m³)**, **R+x · hauteur (m)** et
  **emprise au sol (m²)**. Mention « indicatif : ni architecture ni implantation réelle ».

## 3. Recette (brief : « le volume affiché = emprise × hauteur de la capacité déjà calculée »)
`pytest tests/test_volume3d.py` (**3 verts**) :
- `volume_m3 == round(emprise_constructible_m2 × hauteur_m)` sur une parcelle U constructible ;
- géométrie bien en **mètres locaux** (|coord| < 1 km, centroïde ≈ origine) ;
- la hauteur exposée = `niveaux × hauteur d'étage` (cohérence moteur) ;
- zone agricole → **aucun gabarit** (pas de volume fabriqué).
