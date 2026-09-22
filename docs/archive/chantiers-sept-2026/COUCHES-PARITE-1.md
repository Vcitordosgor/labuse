# COUCHES-PARITE-1 — Parité avant tout retrait

Branche `feat/couches-tuyau`, départ `71461157`. **Lecture seule, aucune suppression, aucun nettoyage.** Le retrait sera un mandat séparé, écrit à partir de ce tableau.

## 35 anciennes couches d'overlay, **35/35 couvertes par le tuyau** ; **43 appelants front actifs** (MapView 39 + Legend 4) et **0 hors du V1 map** (exports/PDF, outils, copilote, scripts).

Le panneau « Cartes » compte **37 entrées** (35 couches d'overlay servies par l'ancien endpoint + 2 repères de fond). L'ancien endpoint `/map/layers.geojson` sert **40 kinds stockés** + **6 kinds virtuels**. Tout est couvert par les 56 couches du tuyau (qui en AJOUTE ~14). Aucun appelant runtime hors du V1 map (`MapView`/`Legend`) et de 12 tests → **le retrait ne casse rien d'externe**, mais il faut retirer l'endpoint, ses 43 hooks et le panneau V1 ENSEMBLE, et **préserver le basemap** (dont le tuyau dépend).

## Le double inventaire

**1. Ancien endpoint `/map/layers.geojson?kind=…`** (`src/labuse/api/app.py:5570`, `map_layers_geojson`). Sert `_MAP_LAYER_KINDS` (40 kinds stockés) : `amenite, amenite_bpe, anru, artificialisation, axe_structurant, bassin_versant, bruit_carte, bruit_route, cimetiere, cinquante_pas, construction_lineaire, construction_surfacique, dpf, dpu, endiguement, frr, georisque_alea, ligne_ht, ligne_mt, parc_national, peb, piscine_cosia, plu_gpu_zone, pole_echange, ppr, qpv, sup, tcsp_station, tcsp_troncon, tcsp_zone, telepherique, transport_arret, transport_ligne, tri_zone, tva_primo, vefa_neuf, zfang, znieff, zone_activite, zone_humide` — plus **6 kinds virtuels** (`_VIRTUAL_MAP_KINDS`) : `er→plu_gpu_prescription(05)`, `ebc→plu_gpu_prescription(01)`, `enp→ens`, `rpg→safer`, `sis→sol_pollue(sis)`, `casias→sol_pollue(casias,instruction)`. Un second endpoint V1 sert les gros aplats zonage/PPR en tuiles vectorielles : `/map/tiles/ov/{kind}/…` (`src/labuse/api/tiles.py:474`, `ovmvt-zonage`/`ovmvt-ppr`).

**2. Ancien panneau « Cartes »** (`frontend/src/components/panel/LeftPanel.tsx`, `LAYER_FAMILIES`, 37 clés `LayerToggles`) — chaque clé pilote une couche `ov-*` de MapView, alimentée par `getMapLayer(kind)` (`api.ts:656` → `/map/layers.geojson`). Le tuyau (`NouvellesCouches`) est monté DANS le même panneau, à côté. 3 clés de store (`parcelles`, `renouv`, `couleurs_verdict`) ne sont PAS des couches servies : ce sont des modes de rendu conservés hors menu.

## Le tableau — ancienne couche · équivalent tuyau · appelants restants · retirable

| # | ancienne couche (clé panneau) | kind endpoint | équivalent tuyau | appelants restants | retirable |
|---|-------------------------------|---------------|------------------|--------------------|:---------:|
| 1 | limites (contour cadastral) | — (base cadastre, pas l'endpoint) | limites_parcelles | MapView base + applyClairMode | à voir (repère/basemap) |
| 2 | communes | — (communes974.geojson IGN) | limites_communes | MapView base + applyClairMode | à voir (repère/basemap) |
| 3 | zonage_parcelle | plu_gpu_zone | zonage_parcelle | MapView | oui |
| 4 | zonage | plu_gpu_zone | plu_gpu_zone | MapView (ov + ovmvt `/map/tiles/ov`) | oui |
| 5 | ebc | plu_gpu_prescription(01) | ebc | MapView | oui |
| 6 | er | plu_gpu_prescription(05) | er | MapView | oui |
| 7 | dpu | dpu | dpu | MapView | oui |
| 8 | sup | sup | sup | MapView | oui |
| 9 | ppr | ppr | ppr | MapView (ov + ovmvt) | oui |
| 10 | alea_inondation | georisque_alea | alea_inondation | MapView + Legend | oui |
| 11 | alea_mvt | georisque_alea | alea_mvt | MapView + Legend | oui |
| 12 | endiguement | endiguement | endiguement | MapView | oui |
| 13 | peb | peb | peb | MapView | oui |
| 14 | bruit_route | bruit_route | bruit_route | MapView | oui |
| 15 | bruit_carte | bruit_carte | bruit_carte | MapView | oui |
| 16 | sis | sol_pollue(sis) | sis | MapView | oui |
| 17 | casias | sol_pollue(casias) | casias | MapView | oui |
| 18 | parc | parc_national | parc_national | MapView | oui |
| 19 | znieff | znieff | znieff | MapView | oui |
| 20 | enp | ens | enp | MapView | oui |
| 21 | zone_humide | zone_humide | zone_humide | MapView | oui |
| 22 | artificialisation | artificialisation (OCS GE) | artificialisation | MapView | oui |
| 23 | dpf | dpf | dpf | MapView | oui |
| 24 | cinquante_pas | cinquante_pas | cinquante_pas | MapView | oui |
| 25 | rpg | safer | safer (RPG/SAFER) | MapView | oui |
| 26 | transport (lignes+arrêts) | transport_ligne · transport_arret · telepherique | transport_ligne + transport_arret + telepherique | MapView + Legend | oui |
| 27 | tcsp | tcsp_troncon · tcsp_station · tcsp_zone | tcsp | MapView | oui |
| 28 | axes | axe_structurant · pole_echange | axe_structurant + pole_echange | MapView + Legend | oui |
| 29 | lignes_ht (HTA+HTB) | ligne_ht · ligne_mt | ligne_ht + ligne_mt | MapView + Legend | oui |
| 30 | equipements_bpe | amenite_bpe | amenite_bpe | MapView | oui |
| 31 | equipements | amenite | amenite | MapView | oui |
| 32 | qpv | qpv | qpv | MapView | oui |
| 33 | tva_primo | tva_primo | tva_primo | MapView | oui |
| 34 | anru | anru | anru | MapView | oui |
| 35 | zfang | zfang | zfang | MapView | oui |
| 36 | frr | frr | frr | MapView | oui |
| 37 | vefa_neuf | vefa_neuf | vefa_neuf | MapView | oui |

**Parité : 37/37 ont leur équivalent tuyau** (les 35 couches d'overlay + les 2 repères). Aucune ancienne couche sans équivalent. Plusieurs anciennes clés fusionnées ont été ÉCLATÉES par le tuyau (transport → 3 couches, axes → 2, lignes_ht → 2) — le tuyau est plus fin, pas plus pauvre.

## Ce que le tuyau AJOUTE (superset — sans équivalent V1)

`bassin_versant, foret_publique, sar, zone_activite, friche, piscine_cosia, cimetiere, abf, tri_zone, trait_de_cote, icpe, cavite` (12 couches thématiques neuves), + `batiment, construction_surfacique, construction_lineaire` (fonds/repères). Le tuyau sert **56 couches** contre 35 overlays V1 → aucune perte au retrait.

## Appelants encore actifs (récap — qui casse au retrait)

- **Runtime, front (V1 map) :** `getMapLayer()` (`api.ts:656`) appelé par **39 hooks `useQuery` dans MapView.tsx** (l.838-904) + **4 dans Legend.tsx** (aléa, transport, pôles, ligne HT). = **43 hooks vivants**. Plus les couches `ovmvt-zonage`/`ovmvt-ppr` (endpoint `/map/tiles/ov`).
- **Tests :** 12 appels directs / HTTP (`test_api_q_v2`, `test_amenites`, `test_retours12_c2_tcsp`, `test_retours13_lot1`, `test_retours14_carte`, `test_sources_connexions`).
- **AUCUN appelant runtime hors du V1 map :** exports/PDF = 0, outils = 0, copilote = 0, scripts = 0. Les autres références sont des DÉCLARATIONS/MÉTADONNÉES statiques (pas des fetch) : `route:` des YAML couches (56), `registre/robinets.py` (31, télémétrie dashboard), `registre/donnees.py` (47, fonction servante), fixtures QA, docstrings d'ingestion, `protection.py` (préfixe rate-limit). Elles ne cassent pas au runtime mais devront être migrées/nettoyées avec le retrait.

## Mécanismes V1 dont le tuyau DÉPEND encore (à NE PAS retirer)

Le tuyau rend ses couches AU-DESSUS du basemap V1 ; il ne dépend d'AUCUNE couche d'overlay `ov-*` (elles sont retirables), mais il dépend du **fond** :

1. **`applyClairMode`** (`MapView.tsx:358`) — thème du basemap par fond (mer/terre `bg`, `ile-mass`, `ortho-veil`, rasters ortho). ET : `paintParcellesParFond` (`CouchesTuyau.tsx`, STYLE-5) **copie VERBATIM** les valeurs `parcels-limites` d'`applyClairMode` (couleur/largeur/opacité par fond) — dépendance de VALEUR (si applyClairMode change ces valeurs, le tuyau dérive).
2. **Les calques de basemap** : `bg` (canvas mer), `bm-ortho-*` (rasters), `ile-mass`, `ortho-veil`, `ile-cote`, et le **cadastre de fond** `parcels-base`/`ile-base`/`zone-fill` (le maillage visible sous le contour tuyau).
3. **L'état `basemap` du store + `MapToolbar`** (sélecteur de fond, conservé en STYLE-6).

Ces trois blocs restent nécessaires ; seul l'ensemble {endpoint `/map/layers.geojson` + `/map/tiles/ov` + les 43 hooks + `LAYER_FAMILIES`/`ov-*`/`ovmvt-*` + `LayerToggles` + 12 tests} est retirable, EN BLOC, une fois le mandat de retrait écrit.

## Verdict

Parité prouvée : **rien n'est perdu**. Les 35 couches d'overlay V1 sont couvertes 1:1 par le tuyau (qui en ajoute 14+) et ne sont appelées que par le V1 map lui-même — zéro appelant externe (exports/PDF, outils, copilote, scripts). Retrait = opération INTERNE au front carto + endpoint, à faire d'un bloc, en gardant le basemap (applyClairMode + rasters + cadastre de fond + MapToolbar) et en tranchant le sort des 2 repères (limites/communes). `tsc -b` vert, lecture seule.
