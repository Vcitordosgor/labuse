# Les Trois-Bassins — résultats import gold standard (2026-06-29T03:02:11)

- **Commune / INSEE** : Les Trois-Bassins / 97423
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **5314**
- Sections : **9**
- Bâti (couche) : 0 → **7898**
- Évaluées : **5314 / 5314** (100 %)

## Couches

- batiment : 7898
- voirie : 3625
- pente : 2629
- plu_gpu_zone : 224
- ppr : 4
- sar : 50
- ravine : 229
- plu_gpu_prescription : 293
- osm_faux_positif : 33
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **2**
- À creuser : **1149**
- Écartée : **222**
- Faux positif probable : **3941**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 12s
- couches : 69s
- cascade : 355s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (5314) — 5314 (min 5314)
- ✓ OK   sections présentes — 9
- ✓ OK  [critique] 0 doublon IDU — 5314/5314
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 5314/5314
- ✓ OK  [critique] bâti présent (> 0) — 7898
- ✓ OK  [critique] zonage PLU présent — 224
- ✓ OK  [critique] pente présente — 2629
- ✓ OK  [critique] voirie présente — 3625
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 50 features
- ✓ OK   ravine : complet — 229 features
- ✓ OK   plu_gpu_prescription : complet — 293 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 5314/5314
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (2 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

