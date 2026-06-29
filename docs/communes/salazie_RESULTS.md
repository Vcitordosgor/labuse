# Salazie — résultats import gold standard (2026-06-29T03:16:23)

- **Commune / INSEE** : Salazie / 97421
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **7035**
- Sections : **32**
- Bâti (couche) : 0 → **7410**
- Évaluées : **7035 / 7035** (100 %)

## Couches

- batiment : 7410
- voirie : 2736
- pente : 5986
- plu_gpu_zone : 336
- ppr : 2
- sar : 57
- ravine : 629
- plu_gpu_prescription : 879
- osm_faux_positif : 74
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **0**
- À creuser : **836**
- Écartée : **761**
- Faux positif probable : **5438**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 16s
- couches : 129s
- cascade : 697s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (7035) — 7035 (min 7035)
- ✓ OK   sections présentes — 32
- ✓ OK  [critique] 0 doublon IDU — 7035/7035
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 7035/7035
- ✓ OK  [critique] bâti présent (> 0) — 7410
- ✓ OK  [critique] zonage PLU présent — 336
- ✓ OK  [critique] pente présente — 5986
- ✓ OK  [critique] voirie présente — 2736
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 57 features
- ✓ OK   ravine : complet — 629 features
- ✓ OK   plu_gpu_prescription : complet — 879 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 7035/7035
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (None opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

