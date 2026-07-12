# Lot 5 — ordre des opérations (gel → contrôles → churn → test UNIQUE)

- [2026-07-12 15:18:57] modèle gelé le 2026-07-12 15:17:54 (sha256 9042ee9dd3bcdefd…)
- [2026-07-12 15:19:16] contrôle labels permutés intra-année (val) : RR@1158 = 0.866 (attendu ≈ 1)
- [2026-07-12 15:19:19] contrôle features rassies d'un an (val) : RR@1158 21.20 vs 23.79 à jour (chute attendue)
- [2026-07-12 15:19:31] churn top-1158 2024→2025 : overlap 484 (41.8%)
- [2026-07-12 15:19:31] === LECTURE UNIQUE DU TEST 2025 — début ===
- [2026-07-12 15:19:32] test 2025 : 431663 lignes, 1.7349% positifs
- [2026-07-12 15:31:56] résultats test :
                                     score    k  taux_global  taux_topk        rr  positifs_topk  ic95_bas  ic95_haut  n_boot
                          P (Z+D, calibré) 1158     0.017349   0.408463 23.543638            473 21.750627  25.091491    1000
                          P (Z+D, calibré)  500     0.017349   0.590000 34.007367            295 31.147896  36.093969    1000
                           ablation Z seul 1158     0.017349   0.096718  5.574815            112  4.524133   6.363301    1000
                           ablation Z seul  500     0.017349   0.136000  7.838986             68  6.467532   9.923553    1000
             baseline rotation DVF secteur 1158     0.017349   0.063040  3.633585             73  2.850476   4.455496    1000
             baseline rotation DVF secteur  500     0.017349   0.062000  3.573655             31  2.559382   5.034004    1000
baseline V v1.3 (ties à 0/NULL seedés 974) 1158     0.017349   0.007772  0.447976              9  0.151298   0.739835    1000
baseline V v1.3 (ties à 0/NULL seedés 974)  500     0.017349   0.018000  1.037513              9  0.350407   1.713458    1000
- [2026-07-12 15:31:57] ECE test : 0.00149 | AP 0.08052 | AUC 0.6569
- [2026-07-12 15:31:57] === LECTURE UNIQUE DU TEST 2025 — fin ===
