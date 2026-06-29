# Sainte-Rose — résultats import gold standard (2026-06-29T02:33:41)

- **Commune / INSEE** : Sainte-Rose / 97419
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **6287**
- Sections : **24**
- Bâti (couche) : 0 → **6229**
- Évaluées : **6287 / 6287** (100 %)

## Couches

- batiment : 6229
- voirie : 6941
- pente : 8391
- plu_gpu_zone : 200
- ppr : 2
- sar : 49
- ravine : 456
- plu_gpu_prescription : 293
- osm_faux_positif : 35
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 1 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **9**
- À creuser : **1817**
- Écartée : **764**
- Faux positif probable : **3697**
- Taux d'opportunité : **0.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 5s
- couches : 184s
- cascade : 539s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6287) — 6287 (min 6287)
- ✓ OK   sections présentes — 24
- ✓ OK  [critique] 0 doublon IDU — 6287/6287
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6287/6287
- ✓ OK  [critique] bâti présent (> 0) — 6229
- ✓ OK  [critique] zonage PLU présent — 200
- ✓ OK  [critique] pente présente — 8391
- ✓ OK  [critique] voirie présente — 6941
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 1 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 49 features
- ✓ OK   ravine : complet — 456 features
- ✓ OK   plu_gpu_prescription : complet — 293 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6287/6287
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.1 % (9 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

