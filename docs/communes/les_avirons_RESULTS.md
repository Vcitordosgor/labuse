# Les Avirons — résultats import gold standard (2026-06-28T18:09:07)

- **Commune / INSEE** : Les Avirons / 97401
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **8611**
- Sections : **15**
- Bâti (couche) : 0 → **18077**
- Évaluées : **8611 / 8611** (100 %)

## Couches

- batiment : 18077
- voirie : 6063
- pente : 3500
- plu_gpu_zone : 240
- ppr : 6
- sar : 38
- ravine : 286
- plu_gpu_prescription : 217
- osm_faux_positif : 63
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **225**
- À creuser : **3087**
- Écartée : **748**
- Faux positif probable : **4551**
- Taux d'opportunité : **2.6 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 58

## Temps d'exécution

- parcelles : 2s
- couches : 79s
- cascade : 69s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (8611) — 8611 (min 8611)
- ✓ OK   sections présentes — 15
- ✓ OK  [critique] 0 doublon IDU — 8611/8611
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 8611/8611
- ✓ OK  [critique] bâti présent (> 0) — 18077
- ✓ OK  [critique] zonage PLU présent — 240
- ✓ OK  [critique] pente présente — 3500
- ✓ OK  [critique] voirie présente — 6063
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 6 features
- ✓ OK   sar : complet — 38 features
- ✓ OK   ravine : complet — 286 features
- ✓ OK   plu_gpu_prescription : complet — 217 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 8611/8611
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 2.6 % (225 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

