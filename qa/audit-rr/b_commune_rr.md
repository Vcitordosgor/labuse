# ALGO-1 · RR par commune — fold 2025 (mesure, out-of-sample)

Protocole GELÉ : label L2-F 2025, scores du fold walk-forward (`scores-2025-fold-final.csv`), hors copro, ties seedés 974 (`p_model.evaluate`, rien de recodé).
**Contrôle île : RR@1158 = 6.73** (référence gelée 6 73 — OK) · n = 428 239 hors copro · taux de base île 1.51 %.

Deux lectures : **RR intra-commune** (top-k_c pris DANS la commune, k_c ∝ 1158 — le classement discrimine-t-il partout) et **présence dans le top-1158 île** (où va la réserve réellement servie).

| Commune | n hors copro | taux base | k_c | RR intra [conf.] | dans top-1158 île | RR dans le top île |
|---|---:|---:|---:|---:|---:|---:|
| Sainte-Suzanne (97420) | 12 490 | 0.90 % | 34 | **19.5** | 18 | 30.7 |
| L'Étang-Salé (97404) | 9 011 | 1.63 % | 24 | **17.9** | 40 | 13.8 |
| Le Port (97407) | 10 114 | 1.84 % | 27 | **16.1** | 25 | 17.4 |
| Sainte-Rose (97419) | 6 284 | 0.81 % | 17 | **14.5** ⚠ <5 positifs | 4 | 30.8 |
| Saint-Benoît (97410) | 21 622 | 1.48 % | 58 | **14.0** | 47 | 18.7 |
| Saint-Philippe (97417) | 4 155 | 1.52 % | 11 | **12.0** ⚠ <5 positifs | 3 | 44.0 |
| Petite-Île (97405) | 13 122 | 1.46 % | 35 | **9.8** | 31 | 6.6 |
| Saint-Pierre (97416) | 42 045 | 1.51 % | 114 | **9.3** | 96 | 9.0 |
| Les Avirons (97401) | 8 560 | 1.52 % | 23 | **8.6** ⚠ <5 positifs | 22 | 9.0 |
| Saint-André (97409) | 22 513 | 1.35 % | 61 | **8.5** | 53 | 9.8 |
| La Plaine-des-Palmistes (97406) | 6 446 | 1.60 % | 17 | **7.4** ⚠ <5 positifs | 19 | 6.6 |
| Sainte-Marie (97418) | 16 646 | 1.32 % | 45 | **6.7** ⚠ <5 positifs | 32 | 9.5 |
| Salazie (97421) | 7 034 | 0.87 % | 19 | **6.1** ⚠ <5 positifs | 11 | 10.5 |
| Saint-Leu (97413) | 22 763 | 1.32 % | 62 | **4.9** ⚠ <5 positifs | 67 | 4.5 |
| Saint-Paul (97415) | 50 593 | 1.74 % | 137 | **4.6** | 194 | 4.7 |
| Entre-Deux (97403) | 6 301 | 1.29 % | 17 | **4.6** ⚠ <5 positifs | 13 | 6.0 |
| La Possession (97408) | 13 148 | 2.19 % | 36 | **3.8** ⚠ <5 positifs | 97 | 4.2 |
| Saint-Denis (97411) | 36 981 | 1.60 % | 100 | **3.8** | 127 | 3.0 |
| Saint-Louis (97414) | 29 141 | 1.39 % | 79 | **3.7** ⚠ <5 positifs | 72 | 5.0 |
| Le Tampon (97422) | 42 523 | 1.71 % | 115 | **3.1** | 80 | 2.9 |
| Saint-Joseph (97412) | 28 875 | 1.55 % | 78 | **2.5** ⚠ <5 positifs | 43 | 1.5 |
| Bras-Panon (97402) | 6 016 | 0.96 % | 16 | **0.0** ⚠ <5 positifs | 11 | 0.0 |
| Les Trois-Bassins (97423) | 5 301 | 1.38 % | 14 | **0.0** ⚠ <5 positifs | 41 | 1.8 |
| Cilaos (97424) | 6 555 | 1.74 % | 18 | **0.0** ⚠ <5 positifs | 12 | 0.0 |

Médiane des RR intra-commune : **6.4** (île : 6.73).

Notes de lecture honnêtes :
- un RR intra très haut sur une PETITE commune (peu de positifs dans le top-k_c) est fragile — les lignes « ⚠ <5 positifs » ne supportent aucune conclusion ;
- « dans top-1158 île — » = la commune ne place AUCUNE parcelle dans la réserve servie : le classement île concentre la réserve sur les marchés actifs (c'est le comportement attendu d'un rang absolu, pas un bug — mais c'est un choix produit à connaître) ;
- mesure SEULE : aucun seuil, aucun tier, aucun modèle modifié (mandat ALGO-1 item 1).
