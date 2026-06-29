# Sainte-Suzanne — résultats import gold standard (2026-06-29T02:21:27)

- **Commune / INSEE** : Sainte-Suzanne / 97420
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **12527**
- Sections : **26**
- Bâti (couche) : 0 → **28794**
- Évaluées : **12527 / 12527** (100 %)

## Couches

- batiment : 28794
- voirie : 10884
- pente : 4160
- plu_gpu_zone : 338
- ppr : 4
- sar : 54
- ravine : 417
- plu_gpu_prescription : 481
- osm_faux_positif : 175
- abf : 2

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **231**
- À creuser : **1818**
- Écartée : **260**
- Faux positif probable : **10218**
- Taux d'opportunité : **1.8 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 90

## Temps d'exécution

- parcelles : 7s
- couches : 107s
- cascade : 1583s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (12527) — 12527 (min 12527)
- ✓ OK   sections présentes — 26
- ✓ OK  [critique] 0 doublon IDU — 12527/12527
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 12527/12527
- ✓ OK  [critique] bâti présent (> 0) — 28794
- ✓ OK  [critique] zonage PLU présent — 338
- ✓ OK  [critique] pente présente — 4160
- ✓ OK  [critique] voirie présente — 10884
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 54 features
- ✓ OK   ravine : complet — 417 features
- ✓ OK   plu_gpu_prescription : complet — 481 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 12527/12527
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.8 % (231 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

