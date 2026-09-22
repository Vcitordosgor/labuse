# RAPPORT DE FAISABILITÉ — 2.B Vue mer (viewshed)

> §7 / brief 2.B (« rapport de faisabilité d'abord, effort plafonné »). Sondé le 2026-06-14.

## Options évaluées
| Option | Verdict |
|---|---|
| **GRASS `r.viewshed`** | ❌ GRASS non installé dans le conteneur |
| **PostGIS raster** (MNT chargé en raster) | ❌ extension `postgis_raster` absente, aucun MNT raster |
| **Profil d'élévation 1D vers l'océan** (RGE ALTI + trait de côte) | ✅ retenu — léger, sources déjà branchées |

## v1 retenue (line-of-sight 1D)
- **Direction mer** : point le plus proche du **trait de côte (DEAL)** depuis le centroïde → azimut + distance.
- **Profil** : 40 échantillons d'altitude **RGE ALTI** du centroïde jusqu'à 200 m au-delà de la côte
  (1 appel batch/parcelle). La vue est dégagée si le terrain DESCEND vers la mer sans relief au-dessus
  de la ligne observateur→mer ; **front de mer (< 120 m)** → vue acquise (cas dégénéré du profil).
- **Indicateur** : `oui` / `partielle` / `non` + distance côte, altitude observateur, % d'obstruction.
- **Coût** : ~1 appel RGE/parcelle, **lazy** (fiche) + **mémoïsé** (cache `parcel_vue_mer`) → le bilan
  lit le cache sans appel live.

## Limites documentées (assumées)
- Profil sur **un seul azimut** (pas un viewshed 360°) → un panorama latéral peut être sous-estimé.
- **Sans le bâti** (RGE ALTI = sol) → un immeuble masquant n'est pas vu. INDICATIF.
- Couverture complète des 3 000 parcelles = batch RGE (borné mais lent, ~quota 5 req/s) → fait à la
  volée à l'ouverture de fiche (mémoïsé) ; un `compute-vue-mer` batch reste possible côté ops.

## Recette
- **BV1120** (alt 317 m, côte à 2,3 km, descente dégagée) → **« oui »** (hauteur à vue panoramique).
- **BT0124** (côte à 606 m, relief intermédiaire) → **« non »** (masquée).
- **Bonus prix** : param `bonus_vue_mer_pct` (PLACEHOLDER) ; le bilan applique +X % au prix si la
  parcelle est `vue=oui` (testé : CA × 1,12 à 12 %). Vic calibre le %.

## Verdict : **GO v1** livrée (indicateur fiche + bonus bilan), limites documentées.
