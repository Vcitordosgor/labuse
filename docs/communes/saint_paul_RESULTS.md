# Saint-Paul — résultats import gold standard (2026-06-28T19:15:51)

- **Commune / INSEE** : Saint-Paul / 97415
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 3000 → **51129**
- Sections : **98**
- Bâti (couche) : 0 → **83981**
- Évaluées : **51129 / 51129** (100 %)

## Couches

- batiment : 83981
- voirie : 22999
- pente : 13062
- plu_gpu_zone : 1097
- ppr : 4
- sar : 303
- ravine : 1244
- plu_gpu_prescription : 710
- osm_faux_positif : 808
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 1 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **2092**
- À creuser : **18476**
- Écartée : **1490**
- Faux positif probable : **29071**
- Taux d'opportunité : **4.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 582

## Temps d'exécution

- parcelles : 14s
- couches : 327s
- cascade : 3464s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (51129) — 51129 (min 51129)
- ✓ OK   sections présentes — 98
- ✓ OK  [critique] 0 doublon IDU — 51129/51129
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 51129/51129
- ✓ OK  [critique] bâti présent (> 0) — 83981
- ✓ OK  [critique] zonage PLU présent — 1097
- ✓ OK  [critique] pente présente — 13062
- ✓ OK  [critique] voirie présente — 22999
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 1 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 303 features
- ✓ OK   ravine : complet — 1244 features
- ✓ OK   plu_gpu_prescription : complet — 710 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 51129/51129
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 4.1 % (2092 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 4 → 4
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

