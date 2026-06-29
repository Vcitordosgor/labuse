# Saint-Joseph — résultats import gold standard (2026-06-28T23:49:41)

- **Commune / INSEE** : Saint-Joseph / 97412
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **28959**
- Sections : **57**
- Bâti (couche) : 0 → **25454**
- Évaluées : **28959 / 28959** (100 %)

## Couches

- batiment : 25454
- voirie : 8909
- pente : 8488
- plu_gpu_zone : 435
- ppr : 4
- sar : 155
- ravine : 482
- plu_gpu_prescription : 477
- osm_faux_positif : 211
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 1 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **534**
- À creuser : **7766**
- Écartée : **1032**
- Faux positif probable : **19627**
- Taux d'opportunité : **1.8 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 120

## Temps d'exécution

- parcelles : 46s
- couches : 167s
- cascade : 4039s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (28959) — 28959 (min 28959)
- ✓ OK   sections présentes — 57
- ✓ OK  [critique] 0 doublon IDU — 28959/28959
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 28959/28959
- ✓ OK  [critique] bâti présent (> 0) — 25454
- ✓ OK  [critique] zonage PLU présent — 435
- ✓ OK  [critique] pente présente — 8488
- ✓ OK  [critique] voirie présente — 8909
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 1 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 155 features
- ✓ OK   ravine : complet — 482 features
- ✓ OK   plu_gpu_prescription : complet — 477 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 28959/28959
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.8 % (534 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

