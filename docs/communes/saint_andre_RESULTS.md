# Saint-André — résultats import gold standard (2026-06-28T22:38:37)

- **Commune / INSEE** : Saint-André / 97409
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **22600**
- Sections : **33**
- Bâti (couche) : 0 → **50910**
- Évaluées : **22600 / 22600** (100 %)

## Couches

- batiment : 50910
- voirie : 13264
- pente : 3819
- plu_gpu_zone : 419
- ppr : 4
- sar : 121
- ravine : 353
- plu_gpu_prescription : 308
- osm_faux_positif : 188
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **82**
- À creuser : **7320**
- Écartée : **527**
- Faux positif probable : **14671**
- Taux d'opportunité : **0.4 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 13

## Temps d'exécution

- parcelles : 9s
- couches : 112s
- cascade : 2083s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (22600) — 22600 (min 22600)
- ✓ OK   sections présentes — 33
- ✓ OK  [critique] 0 doublon IDU — 22600/22600
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 22600/22600
- ✓ OK  [critique] bâti présent (> 0) — 50910
- ✓ OK  [critique] zonage PLU présent — 419
- ✓ OK  [critique] pente présente — 3819
- ✓ OK  [critique] voirie présente — 13264
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 121 features
- ✓ OK   ravine : complet — 353 features
- ✓ OK   plu_gpu_prescription : complet — 308 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 22600/22600
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.4 % (82 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

