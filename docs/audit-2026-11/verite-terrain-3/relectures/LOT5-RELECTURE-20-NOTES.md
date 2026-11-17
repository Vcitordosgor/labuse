# VERITE-TERRAIN-3 — LOT 5, relecture des 20 ventes DVF « terrains à bâtir » servies fermées (lecture seule)

Date : 2026-11-15 · Base : labuse (SELECT seulement) · Moteur rejoué : `parcel_faisabilite` (code de la
branche) sur les 20 parcelles ; composition des mutations relue dans `dvf_mutations_parcelle` ; permis
dans `sitadel_permits` ; verbatims `plu_reglement_extrait`.

## Clé de lecture

La ligne DVF « terrains a bâtir » est attachée à UNE parcelle d'UNE mutation, mais `valeur_fonciere` est la
valeur de la MUTATION ENTIÈRE. 12 des 20 ventes sont des mutations multi-parcelles (jusqu'à 66 parcelles),
dont 5 contiennent une maison ou un local commercial sur une AUTRE parcelle : l'étiquette « terrain à bâtir »
sur un délaissé de 11 m² vendu avec une maison n'est pas un signal de constructibilité. Le test géométrique
indépendant (`ST_Buffer(geom, −3 m)`) confirme que 9 des 10 `terrain_exigu` se vident réellement aux reculs.

## Tableau — vente par vente

| idu | vente (val. mutation) | fermeture servie | relecture | verdict |
|---|---|---|---|---|
| 97416000HP0750 | 2021-11, 419 k€, mono-parcelle 464 m² | `zone_non_constructible:Us` | PC 2019 **achevé** (maison 134 m²) AVANT la vente ; zone Us créée par le PLU Saint-Pierre 2024-06 (Us1 : extensions seules) ; la vente précède ces règles (`post_regles=f`) | **vente hors règles actuelles** (fermeture défendable au PLU 2024) |
| 97407000AE0479 | 2025-06, 43 k€, mutation 6 parcelles | `terrain_exigu` (cache 21/10) | 246 m² en Ub, inset −3 m = **92 m² ≠ vide** ; le moteur actuel rend `assiette_a_verifier` (ignorance, pas un verdict) ; vente postérieure aux règles | **suspecte** — cause servie périmée : devrait être « à vérifier » (NC), jamais fermé `terrain_exigu` |
| 97410000BY0583 | 2021-03, 458 k€, mutation 3 parcelles | `zone_non_constructible:A` | 79 m² en zone A réelle ; valeur = mutation entière ; vente postérieure au PLU 2020 mais micro-parcelle | **défendable** (zone A vérifiée ; étiquette TAB d'une mutation groupée) |
| 97401000AR1652 | 2024-04, 105 k€, mutation 2 parcelles | `terrain_exigu` (cache) | zone N actuelle (PLU Avirons 2024-12, POSTÉRIEUR à la vente) ; moteur actuel : `zone_transition` N — la cause servie (`terrain_exigu`) est mal étiquetée mais la fermeture tient | **vente hors règles actuelles** (fermeture défendable au zonage actuel ; cause du cache périmée) |
| 97411000IL0610 | 2025-05, 1 350 €, mono-parcelle | `terrain_exigu` | parcelle de **1 m²** (largeur 0,2 m) | **défendable** (sliver ; l'étiquette DVF « TAB » est du bruit) |
| 97415000ET0602 | 2023-09, s. prix, mutation 20 parcelles | `zone_non_resolue:A` | moteur actuel : zone introuvable (`parcel_faisabilite` → None) ; `zone_non_resolue` est une IGNORANCE — le gate la compte « fermée » | **indéterminé** — ni la vente (lot de 20 parcelles, sans prix) ni le servi (zone non résolue) ne permettent de trancher |
| 97408000BK0288 | 2024-08, 357 k€, mutation 2 p. (maison 110 m²) | `terrain_exigu` | 16 m² (largeur 0,9 m), inset = 0 ; le PC 2026 trouvé « depuis » porte sur l'assiette **BK0245+BK0288** (2 parcelles) | **défendable** — l'exigu par parcelle est vrai ; permis et marché opèrent à l'échelle d'assiette regroupée |
| 97408000AB0414 | 2024-12, 270 k€, mutation 2 p. (maison 70 m²) | `terrain_exigu` | 73 m² (largeur 2,7 m), inset −3 m = 0 | **défendable** |
| 97422000BP1967 | 2025-04, 1,42 M€, mutation **66 parcelles** (local commercial) | `habitat_interdit:1AUe` | zone économique ; opération d'ensemble commerciale ; « TAB » cohérent pour de l'activité, pas du logement | **défendable** (la fermeture LABUSE vise l'habitat) |
| 97416000CS1523 | 2024-06, 185 k€ | `habitat_interdit:Uazi` | zone industrielle (ZI) ; le permis « depuis » (2024) est un PC **locaux** (SI LOGISTIQUE) | **défendable** |
| 97410000CD0898 | 2023-06, 50,6 k€ (153 €/m²), mono-parcelle 330 m² | gate fermé via `parcel_au_statut = 'générique'` | le résiduel servi donne pourtant **168 m² de SDP, sans cause** ; le moteur rejoué dit « R+2 · ~168 m² » constructible ; la fermeture vient du seul déclassement « AU non calibrée » (AUb19 Saint-Benoît) ; vente postérieure aux règles (PLU 2020) | **suspecte** — fermeture par non-calibrage de la zone, en contradiction avec le propre calcul de capacité ; règle AUb19 à ingérer |
| 97424000AI2333 | 2024-04, 245 k€, mutation 6 p. (maison 111 m²) | `terrain_exigu` | 60 m² (largeur 2,7 m), inset = 0 | **défendable** |
| 97404000AL1605 | 2022-03, 2,35 M€, mutation **27 parcelles** (maison 109 m²) | `terrain_exigu` | 11 m², inset = 0 — délaissé dans une grosse vente d'ensemble | **défendable** |
| 97417000AS0303 | 2022-01, 72 k€, mutation 2 parcelles | `hors_plu` | parcelle de **3,5 m²** (Saint-Philippe, RNU) ; `hors_plu` est une ignorance, mais le fond est un sliver | **défendable** (noter : `hors_plu` devrait être servi NC, pas « fermé ») |
| 97405000AW1613 | 2021-03, 15 k€, mutation 3 parcelles | `terrain_exigu` | 139 m² mais largeur ≈ 3,3 m : inset −3 m = 0, le contour se vide réellement | **défendable** |
| 97416000HP0813 | 2022-11, 152 k€, mutation 12 parcelles | `terrain_exigu` + `declasse_non_constructible` | 119 m² (largeur 4,7 m), inset −3 m = 3,6 m² < seuil 5 m² ; le PC 2022 **achevé** porte sur l'assiette **HP0805+HP0811+HP0813** (3 parcelles regroupées) | **défendable** à l'échelle parcelle — la construction réelle s'est faite sur assiette regroupée (limite du raisonnement par parcelle, pas une donnée fausse) |
| 97416000CS1561 | 2024-01, 381 k€, mutation 2 parcelles | `habitat_interdit:Uazi` | ZI ; permis « depuis » = PC **locaux** 2023 (SOS ALTERNATEURS) | **défendable** |
| 97416000EX1106 | 2023-02, 168 k€, mutation 4 parcelles | `terrain_exigu` | 61 m² (largeur 3,1 m), inset = 0 | **défendable** |
| 97416000CS1346 | 2022-10, 219 k€, mono-parcelle 73 m² | `terrain_exigu` | largeur 3,4 m, inset −3 m = 0 : géométriquement vrai ; le prix (≈3 000 €/m²) reste inexpliqué (valeur DVF possiblement portée à tort sur cette ligne) | **défendable** (réserve sur la valeur DVF) |
| 97412000BK1969 | 2025-05, 128 k€ (65 €/m²), mono-parcelle 1 961 m² | `habitat_interdit:1AU6` + AU conditionnelle | PC 2024 « depuis » = **locaux** (ZAC LES TERRASSES, destination 8) → vocation économique confirmée ; vente antérieure au PLU 2025-12 ; prix bas = anticipation | **défendable** (fermeture habitat cohérente avec la ZAC économique) |

## Répartition finale (20 ventes)

| catégorie | n | parcelles |
|---|---|---|
| **Fermeture défendable** (slivers vidés aux reculs — vérifié par inset géométrique —, zone A réelle, zones économiques à habitat interdit, assiettes regroupées) | 15 | BY0583, IL0610, BK0288, AB0414, BP1967, CS1523, AI2333, AL1605, AS0303, AW1613, HP0813, CS1561, EX1106, CS1346, BK1969 |
| **Fermeture suspecte** | 2 | **AE0479** (246 m² en Ub servis `terrain_exigu` alors que l'inset laisse 92 m² et que le moteur actuel dit « à vérifier » — cache périmé, ignorance servie en verdict) ; **CD0898** (résiduel servi 168 m² de SDP mais gate fermé par AU « générique » non calibrée — contradiction interne, règle AUb19 à ingérer) |
| **Vente hors règles actuelles** | 2 | HP0750 (vente 2021, Us créée 2024, maison déjà achevée), AR1652 (vente 2024-04, zone N au PLU 2024-12) |
| **Indéterminé** | 1 | ET0602 (`zone_non_resolue:A`, mutation de 20 parcelles sans prix) |

### Constats transverses
1. **Le signal DVF « terrain à bâtir » est très bruité ici** : 12/20 ventes sont multi-parcelles (valeur =
   mutation entière), 5 embarquent une maison/local sur une autre parcelle ; 10/20 parcelles font < 140 m²
   et 9 ont une largeur ≤ 3,4 m. Le marché n'y contredit presque jamais la fermeture.
2. **Les 2 cas suspects ne sont pas des erreurs de zonage mais des états internes** : un cache
   `terrain_exigu` périmé (AE0479) et un déclassement de prudence « AU non calibrée » qui l'emporte sur un
   résiduel calculé de 168 m² (CD0898).
3. **Trois causes d'ignorance sont comptées « fermées » par le gate** (`zone_non_resolue`, `hors_plu`,
   `terrain_exigu` périmé → `assiette_a_verifier` au rejeu) : pour un lecteur, « fermé » et « on ne sait
   pas » devraient rester distincts — même conclusion que LOT 4 sur le stock résiduel non rejoué.
