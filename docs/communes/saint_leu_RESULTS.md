# Saint-Leu — résultats import gold standard (2026-06-28T21:40:42)

- **Commune / INSEE** : Saint-Leu / 97413
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **22959**
- Sections : **50**
- Bâti (couche) : 0 → **35339**
- Évaluées : **22959 / 22959** (100 %)

## Couches

- batiment : 35339
- voirie : 11761
- pente : 6582
- plu_gpu_zone : 663
- ppr : 4
- sar : 128
- ravine : 477
- plu_gpu_prescription : 274
- osm_faux_positif : 174
- abf : absent

- Couverture zonage PLU : **99.6 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **976**
- À creuser : **7547**
- Écartée : **997**
- Faux positif probable : **13439**
- Taux d'opportunité : **4.3 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 262

## Temps d'exécution

- parcelles : 24s
- couches : 158s
- cascade : 1295s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (22959) — 22959 (min 22959)
- ✓ OK   sections présentes — 50
- ✓ OK  [critique] 0 doublon IDU — 22959/22959
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 22959/22959
- ✓ OK  [critique] bâti présent (> 0) — 35339
- ✓ OK  [critique] zonage PLU présent — 663
- ✓ OK  [critique] pente présente — 6582
- ✓ OK  [critique] voirie présente — 11761
- ✓ OK  [critique] couverture zonage ≥ 99 % — 99.6 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 128 features
- ✓ OK   ravine : complet — 477 features
- ✓ OK   plu_gpu_prescription : complet — 274 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 22959/22959
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 4.3 % (976 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

