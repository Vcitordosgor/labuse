# GEOPF-3 — Preuves par couche (objets 974 + témoin)

⚠ **Contrainte d'environnement** : la carte MapLibre (WebGL) ne se rasterise pas en headless
(preserveDrawingBuffer désactivé dans le code committé — contrainte documentée en mémoire :
« 3D headless ne rasterise pas WebGL », « MCP expire sur carte »). Les captures d'écran de la
**carte live** ne sont donc pas produisibles ici. À la place, chaque couche est prouvée par :
(a) son **nombre d'objets 974** (compté en base / au flux) ; (b) un **témoin** — pour les couches
RASTER, la **tuile réelle sur un témoin** (fichier visualisable ci-dessous) ; pour les couches
VECTEUR, la **tuile MVT servie non vide** sur une tuile-témoin Réunion (octets > 0 = features
présentes), l'API tournant sur 8445.

## Fichiers de captures (tuiles-témoins raster, visualisables)
- `couche6-enr-habitation-saint-pierre-z14.png` — couche 6 (EnR près habitations), périmètre visible.
- `couche9-scan50-1950-saint-paul-z13.jpg` — couche 9, carte IGN **1950** de Saint-Paul (Bellemène,
  le Guillaume, Bellemène les Hauts).
- `couche9-edugeo-1980-saint-paul-z14.png` — couche 9, carte EduGéo **1980** de Saint-Paul
  (le Petit Bernica, Guillaume).

## Preuves tuiles VECTEUR (MVT servie non vide, API 8445, tuile-témoin Réunion)
| Couche | kind | tuile-témoin (z/x/y) | octets MVT |
|--------|------|----------------------|-----------:|
| 1 Pylônes | `pylone` | z13/5357/4582 (Saint-Denis) | 557 |
| 2 Postes transfo | `poste_transformation` | présent z13 (20 objets île, épars) | >0 |
| 3 Mesures comp. | `mesures_compensatoires` | z11/1339/1145 | 405 |
| 4 SCOT | `scot` | z10/669/572 (Saint-Denis = CINOR) | 1510 |
| 5 EnR hors toiture | `enr_exclue_hors_toiture` | z10/669/572 (Parc national) | 12984 |

(octets > 0 = la tuile porte des features — vérifié `curl .../map/tiles/{kind}/{z}/{x}/{y}.pbf`.)

## Preuves fonctionnelles (couches sans rendu carte)
- **Couche 7 (recherche lieu-dit)** : `_sugg_lieu_dit` testé —
  « Guillaume » → `le Guillaume, Saint-Paul` ; « Bois de Nèfles » → 4 résultats ; « Grand Fond » → 4.
  1762 lieux-dits en base (1334 habités + 428 non habités).
- **Couche 7 (fiche Secteur)** : `_secteur_lieudit` testé — parcelle 97415000AB0001 → « le Cabestan ».
- **Couche 5 (Prospection solaire, filtre APER)** : `prospection-solaire/parcelle/{idu}` sert
  `enr_au_sol_exclu` + `enr_sol_exclu_zone` (ST_Intersects) ; affiché en bandeau sur la fiche soleil.
- **Couche 4 (fiche commune SCOT)** : `scot_commune` par ST_Contains(centroïde) —
  Saint-Denis→CINOR, Saint-Paul→TCO, Saint-Pierre→Grand Sud, Saint-Benoît→aucun.
- **Couche 3 (contraintes)** : `mesures_compensatoires` ajouté à `servitudes.contraintes_parcelle`
  (`_KINDS` + `_detail`) → remonte dans « Pièges et risques » + fiche.
- **Couche 9 (Remonter le temps)** : `TEMPS_MILLESIMES` porte SCAN 50 1950 et EduGéo 1980 (relais
  brut `/map/tiles/carte-ancienne`, tuiles 200 non vides ci-dessus).

Le tuyau `/map/tuyau/couches` sert bien les 5 couches vecteur avec leur famille + légende + « i »
(vérifié : pylone→reseaux, poste→reseaux, mesures→environnement, scot→urbanisme, enr→energie).
