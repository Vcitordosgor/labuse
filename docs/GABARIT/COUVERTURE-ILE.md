# Couverture du Gabarit — échantillon zone U

Audit lecture seule (aucune écriture en base). Branche `audit/gabarit-couverture` (depuis main `297b2dbd`).

## Méthode

`build_gabarit_input` + `compute_gabarit` rejoués sur **3 000 parcelles tirées au hasard en zone U**
(`parcel_zone_plu.zone_fam = 'U'`, la zone dominante par surface, celle que lit l'écran — population
306 630 parcelles). Zone U = les seules parcelles qui intéressent un client. Sur 3 000, la marge
d'erreur est < 1 %. Exécution parallèle (7 process, `statement_timeout = 20 s`, aucune écriture).
**Durée : 2,2 min.** Script : `scripts/gabcouv_ile.py` (`… gabcouv_ile.py 7 3000 U`).

## Résultat

| | Parcelles | % |
|---|---|---|
| **Servies** | **2 367** | **78,9 %** |
| Bloquées | 633 | 21,1 % |
| Erreurs / timeout | 0 | 0 % |

(La famille du builder confirme « U » sur les 3 000 : `parcel_zone_plu` et le builder concordent.)

## Bloquées par cause (du plus gros au plus petit)

| Cause | Nb | % des bloquées |
|---|---|---|
| limite non qualifiée | 300 | 47,4 % |
| PLU : zone non calibrée | 201 | 31,8 % |
| PLU : hauteur non validée | 41 | 6,5 % |
| enclave (sans façade sur voie) | 35 | 5,5 % |
| recul non validé | 16 | 2,5 % |
| PLU : CES (emprise) non validée | 13 | 2,1 % |
| multi-zone (≥ 2 zones constructibles) | 11 | 1,7 % |
| PLU : zone sans règles d'implantation | 8 | 1,3 % |
| compute incomplet | 8 | 1,3 % |

Deux causes = **79 %** des blocages : la **limite non qualifiée** (géométrie : voie/séparative non
tranchée — dont les micro-arêtes traitées par GABARIT-6, non mergé ici) et la **zone non calibrée**
(complétude du PLU).

## Par commune (servie / total, %)

| Commune | Servie/Total | % servie | Bloquées |
|---|---|---|---|
| Saint-André | 196/206 | 95,1 % | 10 |
| Les Trois-Bassins | 27/29 | 93,1 % | 2 |
| Saint-Paul | 342/370 | 92,4 % | 28 |
| Sainte-Suzanne | 75/82 | 91,5 % | 7 |
| Entre-Deux | 21/23 | 91,3 % | 2 |
| Saint-Louis | 161/180 | 89,4 % | 19 |
| Saint-Pierre | 281/320 | 87,8 % | 39 |
| Saint-Leu | 141/161 | 87,6 % | 20 |
| Le Tampon | 278/323 | 86,1 % | 45 |
| Saint-Joseph | 126/148 | 85,1 % | 22 |
| Petite-Île | 51/60 | 85,0 % | 9 |
| Sainte-Marie | 113/138 | 81,9 % | 25 |
| Bras-Panon | 33/41 | 80,5 % | 8 |
| Les Avirons | 40/52 | 76,9 % | 12 |
| L'Étang-Salé | 44/58 | 75,9 % | 14 |
| Saint-Denis | 240/334 | 71,9 % | 94 |
| Le Port | 68/96 | 70,8 % | 28 |
| Cilaos | 26/37 | 70,3 % | 11 |
| La Possession | 65/93 | 69,9 % | 28 |
| La Plaine-des-Palmistes | 32/47 | 68,1 % | 15 |
| **Sainte-Rose** | **7/33** | **21,2 %** | 26 |
| **Saint-Benoît** | **0/133** | **0,0 %** | 133 |
| **Salazie** | **0/36** | **0,0 %** | 36 |

23 communes (Saint-Philippe absente : RNU, aucune zone U). **Trois communes structurellement mal
couvertes** : **Saint-Benoît (0 %)**, **Salazie (0 %)** et **Sainte-Rose (21 %)** — PLU non calibré
sur leurs zones U (cause « zone non calibrée »). Elles tirent la moyenne île vers le bas ; hors ces
trois, le reste de l'île dépasse largement 80 %.

## Top 5 causes — 3 exemples d'IDU

- **limite non qualifiée** : `97414000DM0096`, `97413000CD0041`, `97411000BC0035`
- **PLU : zone non calibrée** : `97411000AB0041`, `97410000BX1270`, `97410000AS1339`
- **PLU : hauteur non validée** : `97421000BC0234`, `97421000BO0672`, `97408000BR0188`
- **enclave (sans façade sur voie)** : `97422000ED0098`, `97411000EH0185`, `97411000DW0198`
- **recul non validé** : `97411000AP0181`, `97411000AO0062`, `97416000EV1186`
