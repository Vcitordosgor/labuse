# SYNTHÈSE M3.6 — Verdict foncier (L2-F) + walk-forward long

## ⚑ LOT 0 — LE VERDICT PRODUIT (test 2025, univers HORS COPRO, modèle M3 gelé)

Effectifs : 3424 parcelles copro sur 431663
(RNIC 2465, détection DVF 2072) ;
taux de mutation de base : 29,0 % en copro vs 1,52 % hors copro.

| score | rr | ic95_bas | ic95_haut | taux_topk | positifs_topk |
|---|---|---|---|---|---|
| P (Z+D, calibré) | 2.847 | 2.046 | 3.671 | 0.043 | 50 |
| ablation Z seul | 5.067 | 4.154 | 6.121 | 0.077 | 89 |
| baseline rotation DVF secteur | 1.082 | 0.625 | 1.545 | 0.016 | 19 |
| baseline V v1.3 (ties à 0/NULL seedés 974) | 0.512 | 0.225 | 0.864 | 0.008 | 9 |

**Le modèle M3 complet retombe à RR@1158 = 2,85 hors copro, SOUS sa propre
ablation Z-seul (5,07)** : le bloc D de M3 (tenure et ses croisements) ne tirait
sa force que des copropriétés. La rotation de secteur seule ne vaut plus que 1,08
(les « secteurs chauds » L2 étaient les copros). **V v1.3 re-jugé hors copro :
0,51 — le verdict M3 est confirmé, il ne tenait pas aux copros.**

Décomposition du signe « permis <2 ans » (2023-24) : hors copro 5,4 % vs 1,5 %
(jamais) — **le signe positif est un vrai signal foncier**, pas un artefact copro
(en copro tout est à 21-31 %). Détail : permis-signe-copro.csv.

## Lot 1 — Label L2-F

L2-F = L2 moins les mutations « unité de copro » : tous locaux non nuls ∈
{Appartement, Dépendance}, ≥1 Appartement et ≤3 appartements (une vente en bloc
de ≥4 appartements = immeuble entier, CONSERVÉE ; maison, terrain nu, local
mixte, dépendance seule : conservés). Part exclue : 23 % (2014) → ~30 % (2022+).

| annee | l2 | l2f | part_exclue |
|---|---|---|---|
| 2014 | 5127 | 3937 | 0.232 |
| 2015 | 5452 | 4148 | 0.239 |
| 2016 | 6265 | 4595 | 0.267 |
| 2017 | 6891 | 5174 | 0.249 |
| 2018 | 6656 | 4854 | 0.271 |
| 2019 | 7393 | 5331 | 0.279 |
| 2020 | 7196 | 5098 | 0.292 |
| 2021 | 9266 | 6538 | 0.294 |
| 2022 | 9401 | 6561 | 0.302 |
| 2023 | 8091 | 5650 | 0.302 |
| 2024 | 6848 | 4799 | 0.299 |
| 2025 | 6951 | 4909 | 0.294 |

## Lot 2 — B0 censure (avenant) : forte, mais neutre pour le classement

| millesime | age_mois_precoce | parcelles_l2f_precoce | parcelles_l2f_complete | completude_l2f |
|---|---|---|---|---|
| 2018 | 4 | 2057 | 7027 | 0.293 |
| 2019 | 4 | 2006 | 7417 | 0.270 |
| 2020 | 4 | 3279 | 7280 | 0.450 |

Concordance de classement (même score, labels précoces vs complets) :

| millesime | vue | n_pos | taux | rr@1158 |
|---|---|---|---|---|
| 2019 | early | 1952 | 0.005 | 3.246 |
| 2019 | late | 7213 | 0.017 | 3.928 |
| 2020 | early | 3175 | 0.007 | 3.287 |
| 2020 | late | 7078 | 0.016 | 3.423 |

Un millésime 974 vu à ~16 mois ne contient que 27-45 % des parcelles L2-F
finales, mais le RR@1158 concorde (3,2→3,9 ; 3,3→3,4) : **la censure enlève du
niveau, pas de l'ordre**. Annotation prod au 07/2026 : [{'millesime': 2023, 'age_mois_en_072026': 42, 'completude_attendue': '≈ complète'}, {'millesime': 2024, 'age_mois_en_072026': 30, 'completude_attendue': '~80% (interpolation témoins)'}, {'millesime': 2025, 'age_mois_en_072026': 18, 'completude_attendue': '~40% (interpolation témoins)'}].
Amendement forward 2026 : verdicts de NIVEAU sur édition N+2 minimum (ou
correction par facteur de complétude) ; le suivi de CLASSEMENT peut être continu.

## Lot 2 — Walk-forward L2-F, 6 folds (train ≤N-2, calibration N-1, test N)

| fold | rr@1158 | ic_bas | ic_haut | rr@1158_hors_copro | ece |
|---|---|---|---|---|---|
| 2020 | 10.9591 | 9.6055 | 12.2502 | 9.4116 | 0.0013 |
| 2021 | 9.7389 | 8.3831 | 10.9147 | 8.6076 | 0.0033 |
| 2022 | 9.1412 | 8.0938 | 10.2901 | 8.6286 | 0.0024 |
| 2023 | 7.3651 | 6.4365 | 8.7415 | 7.2995 | 0.0032 |
| 2024 | 8.1160 | 6.8512 | 9.4230 | 7.0757 | 0.0029 |
| 2025 | 6.8855 | 5.9471 | 8.1958 | 6.7269 | 0.0014 |

Contrôle L2 (mêmes folds) — RR élevé en univers complet (~20, porté par les
copros) mais 4,2-6,5 seulement hors copro, TOUJOURS sous le modèle L2-F :

| fold | rr@1158 | rr@1158_hors_copro |
|---|---|---|
| 2020 | 21.47 | 6.48 |
| 2021 | 19.03 | 5.24 |
| 2022 | 20.09 | 5.37 |
| 2023 | 21.67 | 5.90 |
| 2024 | 24.00 | 6.01 |
| 2025 | 23.24 | 4.16 |

Croisements minés une fois sur le fold ancien (2017-18→2019) :
tenure×permis, tenure×surface, ndvi×zone_plu, tenure×rot_nu, surface×permis.

Stabilité des signes : **24/29 features
stables ≥5/6 folds** ; aucune monotonie contrainte violée ; les instables
(permis_24m_norm, filo_dens_pop, qpv, window_coverage, dormance_droits) sont des
coefficients quasi nuls. Suivis explicites, stables 6/6 et positifs :

| fold | lh_permis_recent | lh_piscine |
|---|---|---|
| 2020 | 1.166 | 0.319 |
| 2021 | 1.201 | 0.306 |
| 2022 | 1.255 | 0.333 |
| 2023 | 1.258 | 0.360 |
| 2024 | 1.269 | 0.389 |
| 2025 | 1.284 | 0.419 |

## Lot 3 — Verdict final

| modele | cible_eval | rr | ic95_bas | ic95_haut | ece |
|---|---|---|---|---|---|
| M3 (L2, gelé) | L2 hors copro | 2.904 | 2.036 | 3.611 | 0.002 |
| M3 (L2, gelé) | L2-F hors copro | 2.907 | 2.039 | 3.614 | 0.001 |
| M3.6 (L2-F, fold 2025) | L2-F hors copro | 6.727 | 5.525 | 7.841 | 0.001 |

Overlap top-1158 M3 vs M3.6 sur 2025 : 13.9%.

Critères de promotion : RR@1158 L2-F 2025 hors copro = 6.73
vs barre lot 0.2 = 2,85 (mandat) et 5,07 (Z-seul, barre effective retenue — sinon
on promouvrait un modèle sous sa propre ablation) ; RR ≥ 2× sur tous les folds :
True ; signes : 24/29 (aucune monotonie contrainte violée ; instables = coefs ~0).

### → PROMOTION : M3.6 (L2-F) devient le modèle de référence.

Préversion produit : top-1158-2026-foncier.csv (univers hors copro, modèle
train 2017-2024 + calibration 2025, jamais évalué contre un test, 5 contributions
lisibles par parcelle).

## Fichiers

effectifs-copro.csv · verdict-strate.csv · permis-signe-copro.csv ·
volumetrie-l2f.csv · completude-censure.csv · concordance-censure.csv ·
annotation-taux-2023-2025.csv · walk-forward.csv · stabilite-signes.csv ·
suivi-permis-piscine.csv · interactions-fold-ancien.csv · comparatif.csv ·
decision-promotion.csv · top-1158-2026-foncier.csv
