# La Plaine-des-Palmistes — résultats import gold standard (2026-06-29T02:49:30)

- **Commune / INSEE** : La Plaine-des-Palmistes / 97406
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **6450**
- Sections : **18**
- Bâti (couche) : 0 → **7618**
- Évaluées : **6450 / 6450** (100 %)

## Couches

- batiment : 7618
- voirie : 3178
- pente : 5146
- plu_gpu_zone : 340
- ppr : 2
- sar : 133
- ravine : 504
- plu_gpu_prescription : 986
- osm_faux_positif : 103
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **0**
- À creuser : **1285**
- Écartée : **421**
- Faux positif probable : **4744**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 13s
- couches : 104s
- cascade : 459s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6450) — 6450 (min 6450)
- ✓ OK   sections présentes — 18
- ✓ OK  [critique] 0 doublon IDU — 6450/6450
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6450/6450
- ✓ OK  [critique] bâti présent (> 0) — 7618
- ✓ OK  [critique] zonage PLU présent — 340
- ✓ OK  [critique] pente présente — 5146
- ✓ OK  [critique] voirie présente — 3178
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 133 features
- ✓ OK   ravine : complet — 504 features
- ✓ OK   plu_gpu_prescription : complet — 986 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6450/6450
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (None opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

