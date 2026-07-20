# Arène — q_v7_defisc_Vcaduc vs q_v7_defisc

**AVIS : REJETÉ**

Critère(s) en cause :
- RR@1158 non significativement supérieur (IC95 apparié de ΔRR : borne basse -0.91 ≤ 0)

_L'avis est indicatif : la bascule du run servi reste une décision humaine._  
_Généré 2026-07-20 22:02 UTC · seed 974 · RR@1158 · bootstrap n=1000 · année d'éval 2025._

> ⚠ **NATURE DE LA MESURE — RR ABSOLU IN-SAMPLE, NON COMPARABLE AU WALK-FORWARD.**
> Les scores servis sont calculés **features as-of 01/01/2026** (le run
> servi score l'année suivante), or on les évalue contre le label de **2025** — la
> dernière année labellisée complète. Les fenêtres de features as-of 2026
> **encodent déjà les mutations 2025** → le RR absolu (ici RR@1158) est
> **IN-SAMPLE / optimiste**. Il ne doit PAS être comparé au RR out-of-sample du walk-forward
> M3.6 (fold 2025 hors copro = **6,73**, features as-of 01/01/2025). Même univers (hors copro),
> même k (1158), même label (L2-F) ; SEULE la date as-of diffère (2026 vs 2025).
> **La comparaison RELATIVE champion↔challenger reste valide** (les deux runs subissent la même
> fuite) : c'est le rôle de l'IC apparié de ΔRR ci-dessous, PAS le niveau absolu.

## 1. Contrôle d'univers
- champion `q_v7_defisc` : 431 663 parcelles · challenger `q_v7_defisc_Vcaduc` : 431 663
- **intersection ∩ label 2025 : 431 663** (hors copro : 428 239)
- écart de couverture : 0 chez le champion seul · 0 chez le challenger seul · 0 sans label

## 2. Golden — gate boussole (éliminatoire)
- parcelles golden négatives `factuelle` (attendues écartées/exclues) : **64**
- **compteur boussole — 3 axes (tier brûlante/chaude · statut opportunite · matrice_statut chaude) : 0**
- ✅ aucune violation (aucun faux positif servi introduit).

## 3. Performance — RR@1158
| run | RR@1158 | IC95 | positifs top-k | taux global |
| --- | --- | --- | --- | --- |
| champion | **13.17** | [11.93 ; 15.06] | 231 | 0.0151 |
| challenger | **13.05** | [11.80 ; 14.96] | 229 | 0.0151 |

**Différence APPARIÉE (challenger − champion), bootstrap sur les mêmes parcelles** :
- ΔRR = **-0.11** · IC95 apparié [-0.91 ; +0.73] · significatif (borne basse > 0) : **NON**
- _Critère d'AVIS : le challenger n'est retenu que si cet IC EXCLUT zéro par le bas (pas deux IC indépendants qui se chevauchent)._

**Lift (challenger)** :
| percentile | k | positifs | taux | rr | rappel |
| --- | --- | --- | --- | --- | --- |
| 0.100 | 428 | 57 | 0.133 | 8.792 | 0.009 |
| 0.250 | 1071 | 209 | 0.195 | 12.882 | 0.032 |
| 0.500 | 2141 | 546 | 0.255 | 16.835 | 0.084 |
| 1.000 | 4282 | 1193 | 0.279 | 18.392 | 0.184 |
| 2.000 | 8565 | 2175 | 0.254 | 16.764 | 0.335 |
| 5.000 | 21412 | 3974 | 0.186 | 12.252 | 0.613 |
| 10.000 | 42824 | 4944 | 0.115 | 7.621 | 0.762 |
| 20.000 | 85648 | 5476 | 0.064 | 4.221 | 0.844 |
| 50.000 | 214120 | 5909 | 0.028 | 1.822 | 0.911 |
| 100.000 | 428239 | 6487 | 0.015 | 1.000 | 1.000 |

**Ventilation par commune (top-k challenger)** :
| commune | n_total | taux_base | n_topk | rr_segment |
| --- | --- | --- | --- | --- |
| 97401 | 8560 | 0.015 | 19 | 3.466 |
| 97402 | 6016 | 0.010 | 11 | 9.429 |
| 97403 | 6301 | 0.013 | 20 | 3.890 |
| 97404 | 9011 | 0.016 | 23 | 0.000 |
| 97405 | 13122 | 0.015 | 19 | 3.616 |
| 97406 | 6446 | 0.016 | 24 | 2.608 |
| 97407 | 10114 | 0.018 | 24 | 11.328 |
| 97408 | 13148 | 0.022 | 74 | 16.040 |
| 97409 | 22513 | 0.013 | 46 | 8.076 |
| 97410 | 21622 | 0.015 | 42 | 0.000 |
| 97411 | 36981 | 0.016 | 137 | 12.353 |
| 97412 | 28875 | 0.016 | 58 | 3.326 |

**Ventilation par tier challenger** :
| tier_chall | n_total | taux_base | n_topk | rr_segment |
| --- | --- | --- | --- | --- |
| ecartee | 350871 | 0.013 | 542 | 20.811 |
| a_creuser | 72638 | 0.022 | 50 | 5.338 |
| reserve_fonciere | 3579 | 0.003 | 0 | — |
| chaude | 1031 | 0.200 | 472 | 0.774 |
| brulante | 120 | 0.017 | 94 | 0.638 |

## 4. Calibration — ECE
- champion : **0.0167** · challenger : **0.0168** · Δ = +0.0001 (tolérance 0.01)

## 5. Churn — top-1158
- overlap : 1149/1158 (99%) · **churn 1%** (budget 25%) · 9 entrants / 9 sortants

## 6. Contrôle négatif — permutation
- RR@1158 sur labels permutés intra-année : **0.68** (attendu ≈ 1 ; s'en écarter = fuite/artefact).

## 7. Avis synthétique
**REJETÉ** — RR@1158 non significativement supérieur (IC95 apparié de ΔRR : borne basse -0.91 ≤ 0).
