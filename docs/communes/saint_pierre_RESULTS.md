# Saint-Pierre — résultats import gold standard (2026-06-28T20:25:38)

- **Commune / INSEE** : Saint-Pierre / 97416
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **42425**
- Sections : **66**
- Bâti (couche) : 0 → **119094**
- Évaluées : **42425 / 42425** (100 %)

## Couches

- batiment : 119094
- voirie : 25949
- pente : 7201
- plu_gpu_zone : 1001
- ppr : 4
- sar : 174
- ravine : 411
- plu_gpu_prescription : 1473
- osm_faux_positif : 756
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 2 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **1569**
- À creuser : **12387**
- Écartée : **1141**
- Faux positif probable : **27328**
- Taux d'opportunité : **3.7 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 475

## Temps d'exécution

- parcelles : 62s
- couches : 238s
- cascade : 613s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (42425) — 42425 (min 42425)
- ✓ OK   sections présentes — 66
- ✓ OK  [critique] 0 doublon IDU — 42425/42425
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 42425/42425
- ✓ OK  [critique] bâti présent (> 0) — 119094
- ✓ OK  [critique] zonage PLU présent — 1001
- ✓ OK  [critique] pente présente — 7201
- ✓ OK  [critique] voirie présente — 25949
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 2 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 174 features
- ✓ OK   ravine : complet — 411 features
- ✓ OK   plu_gpu_prescription : complet — 1473 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 42425/42425
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.7 % (1569 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

