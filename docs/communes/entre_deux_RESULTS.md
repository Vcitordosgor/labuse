# Entre-Deux — résultats import gold standard (2026-06-29T02:39:45)

- **Commune / INSEE** : Entre-Deux / 97403
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **6312**
- Sections : **13**
- Bâti (couche) : 0 → **46493**
- Évaluées : **6312 / 6312** (100 %)

## Couches

- batiment : 46493
- voirie : 8802
- pente : 4140
- plu_gpu_zone : 506
- ppr : 2
- sar : 18
- ravine : 280
- plu_gpu_prescription : 1120
- osm_faux_positif : 230
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **1**
- À creuser : **1642**
- Écartée : **940**
- Faux positif probable : **3729**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 13s
- couches : 106s
- cascade : 236s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6312) — 6312 (min 6312)
- ✓ OK   sections présentes — 13
- ✓ OK  [critique] 0 doublon IDU — 6312/6312
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6312/6312
- ✓ OK  [critique] bâti présent (> 0) — 46493
- ✓ OK  [critique] zonage PLU présent — 506
- ✓ OK  [critique] pente présente — 4140
- ✓ OK  [critique] voirie présente — 8802
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 18 features
- ✓ OK   ravine : complet — 280 features
- ✓ OK   plu_gpu_prescription : complet — 1120 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6312/6312
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (1 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

