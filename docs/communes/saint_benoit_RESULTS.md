# Saint-Benoît — résultats import gold standard (2026-06-29T00:55:42)

- **Commune / INSEE** : Saint-Benoît / 97410
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **21671**
- Sections : **50**
- Bâti (couche) : 0 → **34683**
- Évaluées : **21671 / 21671** (100 %)

## Couches

- batiment : 34683
- voirie : 14922
- pente : 15169
- plu_gpu_zone : 909
- ppr : 4
- sar : 118
- ravine : 1670
- plu_gpu_prescription : 2079
- osm_faux_positif : 318
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 1 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **595**
- À creuser : **4681**
- Écartée : **1035**
- Faux positif probable : **15360**
- Taux d'opportunité : **2.7 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 135

## Temps d'exécution

- parcelles : 17s
- couches : 319s
- cascade : 3613s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (21671) — 21671 (min 21671)
- ✓ OK   sections présentes — 50
- ✓ OK  [critique] 0 doublon IDU — 21671/21671
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 21671/21671
- ✓ OK  [critique] bâti présent (> 0) — 34683
- ✓ OK  [critique] zonage PLU présent — 909
- ✓ OK  [critique] pente présente — 15169
- ✓ OK  [critique] voirie présente — 14922
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 1 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 118 features
- ✓ OK   ravine : complet — 1670 features
- ✓ OK   plu_gpu_prescription : complet — 2079 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 21671/21671
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 2.7 % (595 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

