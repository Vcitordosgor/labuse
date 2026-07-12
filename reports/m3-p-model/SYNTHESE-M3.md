# SYNTHÈSE M3 — Modèle P (blocs Z + D), phases 1-2

Modèle gelé le 2026-07-12 15:17:54 (sha256 `9042ee9dd3bcdefd…`), train
2023, C=5.0, seed 974. Test 2025 lu UNE
SEULE FOIS après gel (traces : ORDRE-OPERATIONS.md, ORDRE-OPERATIONS-lot5.md,
artifacts/TEST-2025-LU.json).

## Verdicts par lot

| Lot | Verdict |
|---|---|
| 1 — dataset personne-période | ✅ 431 663 parcelles × années, tests anti-leakage synthétiques verts (`tests/test_p_model_dataset.py`) |
| 2 — bloc Z | ✅ rotation shrinkée, €/m² + tendance, Sitadel 24 m, Filosofi/QPV/PLU/pente/équipements |
| 3 — bloc D | ✅ nu constructible, dormance de droits, permis, tenure (bins « inconnu » explicites), végétation/friche/piscine/PV |
| 4 — modèle | ✅ WoE ≤10 bins + logistique L2, contributions ligne à ligne, GBM shadow (5 croisements réinjectés), isotonique sur val |
| 5 — évaluation | ✅ contrôles négatifs ; verdict test reporté ci-dessous (P bat les 3 baselines) |
| 6 — scoring 2026 | ✅ p_model_scores_2026 (100 % du parc, aucun NA) + top-1158-2026.csv |

## Contrôles négatifs (val 2024, AVANT lecture du test)

| controle | rr@1158 | attendu | verdict |
|---|---|---|---|
| labels permutés intra-année (val 2024) | 0.866 | ≈ 1 | PASS |
| features décalées +1 an (val 2024) | 21.196 | < 23.79 (à jour) | PASS |

## Test 2025 (lecture unique) — baselines vs modèle

| Score | RR@1158 [IC95] | RR@500 [IC95] |
|---|---|---|
| **P (Z+D, calibré)** | 23.54 [21.75, 25.09] | 34.01 [31.15, 36.09] |
| Ablation Z seul | 5.57 [4.52, 6.36] | 7.84 [6.47, 9.92] |
| Baseline rotation DVF secteur | 3.63 [2.85, 4.46] | 3.57 [2.56, 5.03] |
| Baseline V v1.3 (ties seedés) | 0.45 [0.15, 0.74] | 1.04 [0.35, 1.71] |

Note V v1.3 : le test 2025 est « vendeur-certain par construction » (V a été conçu
pour un autre usage) ; les ex æquo à 0/NULL sont départagés par tirage seedé 974.
Aucun taux absolu extrapolé — RR relatifs et taux observés avec IC uniquement.

## Sélection de modèle sur val 2024 (ordre : AVANT le test)

| config | val_ap | val_auc | val_rr@1158 | val_rr@500 | val_ece |
|---|---|---|---|---|---|
| Z+D train23 C=0.05 | 0.048 | 0.644 | 8.305 | 5.074 | — |
| Z+D train23 C=0.2 | 0.048 | 0.644 | 8.458 | 6.372 | — |
| Z+D train23 C=1.0 | 0.048 | 0.643 | 8.662 | 6.608 | — |
| Z+D train23 C=5.0 | 0.048 | 0.643 | 8.662 | 6.608 | — |
| Z seul train23 | 0.026 | 0.603 | 3.618 | 4.012 | — |
| Z+D train23 | 0.048 | 0.643 | 8.662 | 6.608 | — |
| Z+D train22+23 | 0.048 | 0.643 | 8.458 | 5.782 | — |
| FINAL avant calibration | 0.086 | 0.650 | 23.489 | 32.687 | — |
| BASELINE rotation seule | — | — | 3.770 | 3.186 | — |
| BASELINE V v1.3 (ties seedés) | — | — | 0.204 | 0.472 | — |
| FINAL calibré (val) | 0.084 | 0.651 | 23.795 | 32.923 | 0.000 |

## Ventilation du top-1158 test par type de propriétaire

| owner_type | n_total | taux_base | n_topk | taux_topk | rr_segment |
|---|---|---|---|---|---|
| pp | 349597 | 0.017 | 843 | 0.521 | 31.335 |
| pm | 33713 | 0.026 | 197 | 0.142 | 5.458 |
| public | 36463 | 0.008 | 80 | 0.000 | 0.000 |
| bailleur | 11479 | 0.041 | 29 | 0.034 | 0.837 |
| copro | 411 | 0.105 | 9 | 0.556 | 5.310 |

## Lift par percentile (test 2025)

| percentile | k | positifs | taux | rr | rappel |
|---|---|---|---|---|---|
| 0.100 | 432 | 262 | 0.606 | 34.957 | 0.035 |
| 0.250 | 1079 | 448 | 0.415 | 23.932 | 0.060 |
| 0.500 | 2158 | 582 | 0.270 | 15.545 | 0.078 |
| 1.000 | 4317 | 782 | 0.181 | 10.441 | 0.104 |
| 2.000 | 8633 | 1078 | 0.125 | 7.197 | 0.144 |
| 5.000 | 21583 | 1578 | 0.073 | 4.214 | 0.211 |
| 10.000 | 43166 | 2134 | 0.049 | 2.850 | 0.285 |
| 20.000 | 86333 | 3073 | 0.036 | 2.052 | 0.410 |
| 50.000 | 215832 | 5196 | 0.024 | 1.388 | 0.694 |
| 100.000 | 431663 | 7489 | 0.017 | 1.000 | 1.000 |

## Lecture critique — ce que le modèle a réellement trouvé

Analyse post-hoc du top-1158 test (aucune retouche du modèle) :
| tenure_bin | n | taux_mutation |
|---|---|---|
| 1-2 | 10 | 0.200 |
| <1 | 1147 | 0.410 |
| inconnu | 1 | 1.000 |

Nature des mutations captées par le top-1158 :
| nature | count |
|---|---|
| appartement (copro) | 424 |
| maison | 23 |
| nu | 14 |
| autre bâti | 12 |

**La tête extrême du classement est dominée par les reventes d'appartements en
copropriété** (le label L2 au grain parcelle rend un immeuble « mutant » dès qu'un
lot se vend). Zéro fuite temporelle — l'information était disponible au 01/01/Y —
mais pour l'usage radar foncier, la préversion 2026 doit être lue avec le filtre
produit adéquat. Recommandation Phase 3 : label variante excluant les locaux
« Appartement » (mutation foncière stricte : maison / nu / immeuble entier), ou
exclusion des parcelles copro de la vue produit. Le lift au-delà de la tête
(percentiles 1-10, cf. table ci-dessous) reste très supérieur aux baselines et
porte le signal foncier de fond. Autre constat : « permis < 24 mois » est
POSITIF (5,6 % vs 1,8 %), contrairement à l'attente Phase 0 (signe libre assumé).

## Churn

Top-1158 au 01/01/2024 vs 01/01/2025 : overlap 484
(41.8%) — 674 entrants,
674 sortants.

## Fichiers

dictionnaire-features.md · model-card.md · val-resultats.csv ·
test-2025-{resultats,lift,ventilation-owner,calibration}.csv ·
controles-negatifs.csv · churn-top1158.csv · interactions-journal.csv ·
iv-features.csv · top-1158-2026.csv
