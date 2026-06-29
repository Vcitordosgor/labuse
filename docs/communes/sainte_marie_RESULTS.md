# Sainte-Marie — résultats import gold standard (2026-06-29T01:52:58)

- **Commune / INSEE** : Sainte-Marie / 97418
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **16746**
- Sections : **33**
- Bâti (couche) : 0 → **48795**
- Évaluées : **16746 / 16746** (100 %)

## Couches

- batiment : 48795
- voirie : 12745
- pente : 4977
- plu_gpu_zone : 423
- ppr : absent
- sar : 122
- ravine : 578
- plu_gpu_prescription : 1093
- osm_faux_positif : 532
- abf : 3

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **757**
- À creuser : **5142**
- Écartée : **424**
- Faux positif probable : **10423**
- Taux d'opportunité : **4.5 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 167

## Temps d'exécution

- parcelles : 8s
- couches : 121s
- cascade : 558s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (16746) — 16746 (min 16746)
- ✓ OK   sections présentes — 33
- ✓ OK  [critique] 0 doublon IDU — 16746/16746
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 16746/16746
- ✓ OK  [critique] bâti présent (> 0) — 48795
- ✓ OK  [critique] zonage PLU présent — 423
- ✓ OK  [critique] pente présente — 4977
- ✓ OK  [critique] voirie présente — 12745
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : absent/partiel — None features
- ✓ OK   sar : complet — 122 features
- ✓ OK   ravine : complet — 578 features
- ✓ OK   plu_gpu_prescription : complet — 1093 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 16746/16746
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 4.5 % (757 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

