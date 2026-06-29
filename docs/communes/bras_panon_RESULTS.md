# Bras-Panon — résultats import gold standard (2026-06-28T19:36:45)

- **Commune / INSEE** : Bras-Panon / 97402
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **6041**
- Sections : **14**
- Bâti (couche) : 0 → **14272**
- Évaluées : **6041 / 6041** (100 %)

## Couches

- batiment : 14272
- voirie : 7744
- pente : 5676
- plu_gpu_zone : 243
- ppr : 4
- sar : 54
- ravine : 787
- plu_gpu_prescription : 542
- osm_faux_positif : 125
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **212**
- À creuser : **1676**
- Écartée : **253**
- Faux positif probable : **3900**
- Taux d'opportunité : **3.5 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 61

## Temps d'exécution

- parcelles : 3s
- couches : 131s
- cascade : 61s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6041) — 6041 (min 6041)
- ✓ OK   sections présentes — 14
- ✓ OK  [critique] 0 doublon IDU — 6041/6041
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6041/6041
- ✓ OK  [critique] bâti présent (> 0) — 14272
- ✓ OK  [critique] zonage PLU présent — 243
- ✓ OK  [critique] pente présente — 5676
- ✓ OK  [critique] voirie présente — 7744
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 54 features
- ✓ OK   ravine : complet — 787 features
- ✓ OK   plu_gpu_prescription : complet — 542 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6041/6041
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.5 % (212 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

