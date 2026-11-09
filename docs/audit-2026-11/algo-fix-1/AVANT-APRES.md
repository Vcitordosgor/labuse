# ALGO-FIX-1 — AVANT / APRÈS sur toute l'île (run servi q_v20)

Lu de la table de run `parcel_scenario_v2_runs` (écrite par le calcul du run, pas par
l'endpoint). V1 = bande servie `score_labuse`. V2 = statut + bande du scénario.
Reconstruction : statut dérivé sur toute l'île ; bandes & quantités chiffrées (enrich)
sur Entre-Deux + Saint-Denis (échantillon).

## Île entière — 433229 parcelles

### Bandes V1 (servies)
| clé | n | part |
|---|---:|---:|
| A | 6166 | 1.4 % |
| B | 36254 | 8.4 % |
| C | 50913 | 11.8 % |
| D | 99011 | 22.9 % |
| 0 | 217954 | 50.3 % |
| NC | 16272 | 3.8 % |
| HC | 6659 | 1.5 % |

### Statuts V2 — conservation
| clé | n | part |
|---|---:|---:|
| ESTIMATED | 184432 | 42.6 % |
| TO_VERIFY | 30438 | 7.0 % |
| DEFERRED | 782 | 0.2 % |
| NO_MARGIN | 85480 | 19.7 % |
| OUTSIDE_OBJECTIVE | 132097 | 30.5 % |

### Statuts V2 — reconstruction
| clé | n | part |
|---|---:|---:|
| ESTIMATED | 269455 | 62.2 % |
| TO_VERIFY | 30895 | 7.1 % |
| DEFERRED | 782 | 0.2 % |
| OUTSIDE_OBJECTIVE | 132097 | 30.5 % |

### Bandes V2 — conservation (parcelles « Capacité estimée »)
| clé | n | part |
|---|---:|---:|
| A | 10197 | 5.5 % |
| B | 55920 | 30.3 % |
| C | 62894 | 34.1 % |
| D | 55421 | 30.0 % |

### Croisement bande V1 → statut V2 (conservation, île)
| V1 ↓ / V2 → | ESTIMATED | PRESTUDY | TO_VERIFY | DEFERRED | NO_MARGIN | OUTSIDE_OBJECTIVE |
|---|---|---|---|---|---|---|
| A | 5462 | 0 | 704 | 0 | 0 | 0 |
| B | 34031 | 0 | 2172 | 51 | 0 | 0 |
| C | 48569 | 0 | 1997 | 347 | 0 | 0 |
| D | 96370 | 0 | 2319 | 318 | 4 | 0 |
| 0 | 0 | 0 | 18230 | 66 | 85476 | 114182 |
| NC | 0 | 0 | 5016 | 0 | 0 | 11256 |
| HC | 0 | 0 | 0 | 0 | 0 | 6659 |

### Top 20 des changements de bande (conservation), avec la raison
Changement = la V1 sert une bande constructible (A/B/C/D) que la V2 refuse
(À vérifier / Hors projet / Aucun ajout), ou la V1 sert « 0/HC » que la V2 nomme
« Capacité estimée ». Classé par écart de rang de bande.

| IDU | commune | V1 | V2 statut | V2 bande | raison (cause V2) |
|---|---|---|---|---|---|
| 97401000AD1550 | Les Avirons | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97401000AH0371 | Les Avirons | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97401000AI0166 | Les Avirons | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97402000AD0980 | Bras-Panon | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97402000AH1989 | Bras-Panon | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97402000AH1990 | Bras-Panon | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97402000AI1211 | Bras-Panon | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97402000AI1212 | Bras-Panon | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97402000AK2254 | Bras-Panon | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97403000AN0258 | Entre-Deux | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97403000AR1522 | Entre-Deux | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97403000AR1524 | Entre-Deux | A | TO_VERIFY | — | BANDE_SENSIBLE_INCONNUE |
| 97404000AY0350 | L'Étang-Salé | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97404000AY0461 | L'Étang-Salé | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97404000BA0201 | L'Étang-Salé | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97405000AX0050 | Petite-Île | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97405000AX0161 | Petite-Île | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97406000AD0145 | La Plaine-des-Palmistes | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97406000AD0633 | La Plaine-des-Palmistes | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |
| 97406000AE0084 | La Plaine-des-Palmistes | A | TO_VERIFY | — | CALCUL_ASSIETTE_DOUTEUX |

## Par commune

| commune | n | V2 keep: EST / NO_MARGIN / TO_VERIFY / DEFERRED / OUTSIDE | V2 rebuild: EST / autres |
|---|---:|---|---|
| Bras-Panon | 6056 | 2493 / 1512 / 357 / 25 / 1669 | 4005 / 2051 |
| Cilaos | 6583 | 2241 / 985 / 394 / 0 / 2963 | 3226 / 3357 |
| Entre-Deux | 6341 | 2255 / 803 / 229 / 0 / 3054 | 2794 / 3547 |
| L'Étang-Salé | 9133 | 3790 / 1646 / 547 / 1 / 3149 | 5436 / 3697 |
| La Plaine-des-Palmistes | 6465 | 2804 / 1247 / 617 / 73 / 1724 | 4051 / 2414 |
| La Possession | 13407 | 7685 / 1881 / 1042 / 33 / 2766 | 9566 / 3841 |
| Le Port | 10242 | 3244 / 4075 / 597 / 1 / 2325 | 7319 / 2923 |
| Le Tampon | 42877 | 23338 / 4534 / 2213 / 76 / 12716 | 27872 / 15005 |
| Les Avirons | 8636 | 3725 / 1217 / 419 / 10 / 3265 | 4942 / 3694 |
| Les Trois-Bassins | 5341 | 1972 / 875 / 366 / 34 / 2094 | 2847 / 2494 |
| Petite-Île | 13196 | 3564 / 2324 / 616 / 20 / 6672 | 5888 / 7308 |
| Saint-André | 22695 | 13460 / 4555 / 1361 / 0 / 3319 | 18015 / 4680 |
| Saint-Benoît | 21748 | 11458 / 405 / 1681 / 11 / 8193 | 11863 / 9885 |
| Saint-Denis | 38295 | 12532 / 15722 / 4287 / 82 / 5672 | 28061 / 10234 |
| Saint-Joseph | 29027 | 10334 / 4620 / 1262 / 0 / 12811 | 14954 / 14073 |
| Saint-Leu | 23046 | 8004 / 6143 / 1573 / 91 / 7235 | 14147 / 8899 |
| Saint-Louis | 29304 | 12662 / 6181 / 1284 / 242 / 8935 | 18843 / 10461 |
| Saint-Paul | 51359 | 24227 / 8735 / 3305 / 0 / 15092 | 32962 / 18397 |
| Saint-Philippe | 4173 | 0 / 0 / 3331 / 0 / 842 | 0 / 4173 |
| Saint-Pierre | 42558 | 17124 / 12305 / 2212 / 0 / 10917 | 29429 / 13129 |
| Sainte-Marie | 16784 | 7883 / 2541 / 1153 / 8 / 5199 | 10424 / 6360 |
| Sainte-Rose | 6295 | 2147 / 705 / 452 / 51 / 2940 | 2852 / 3443 |
| Sainte-Suzanne | 12615 | 5659 / 2082 / 776 / 24 / 4074 | 7741 / 4874 |
| Salazie | 7053 | 1831 / 387 / 364 / 0 / 4471 | 2218 / 4835 |

