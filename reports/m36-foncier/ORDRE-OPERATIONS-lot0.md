# M3.6 lot 0 — re-stratification post-hoc (modèle gelé, zéro re-fit)

- [2026-07-12 15:48:47] modèle gelé M3 9042ee9dd3bcdefd… ; test 2025 déjà lu le 2026-07-12 15:19:31 — lot 0 = re-stratification post-hoc, aucun re-fit
- [2026-07-12 15:48:48] effectifs copro : {'parcelles': 431663, 'copro_rnic': 2465, 'copro_dvf': 2072, 'copro_total': 3424}
- [2026-07-12 15:59:35] strate hors_copro : n=428239, taux base=1.5167%
- [2026-07-12 15:59:38] strate copro : n=3424, taux base=29.0304%
- [2026-07-12 16:15:13] strate tout : n=431663, taux base=1.7349%
- [2026-07-12 16:15:13] VERDICT PRODUIT (hors copro, RR@1158) :
                                     score       rr  ic95_bas  ic95_haut  taux_topk  positifs_topk
                          P (Z+D, calibré) 2.846876  2.046246   3.671339   0.043178             50
                           ablation Z seul 5.067439  4.153615   6.121480   0.076857             89
             baseline rotation DVF secteur 1.081813  0.624762   1.545265   0.016408             19
baseline V v1.3 (ties à 0/NULL seedés 974) 0.512438  0.224942   0.863818   0.007772              9
- [2026-07-12 16:15:36] décomposition permis (2023-24) :
 copro permis_bin      n  taux_mutation
 False       10a+   2562       0.008977
 False       2-5a  18619       0.013642
 False      5-10a  27846       0.011779
 False        <2a  14234       0.054026
 False     jamais 793217       0.015339
  True       10a+     45       0.311111
  True       2-5a    223       0.210762
  True      5-10a    384       0.239583
  True        <2a    145       0.262069
  True     jamais   6051       0.312510
