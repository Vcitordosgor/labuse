# L'Étang-Salé — résultats import gold standard (2026-06-28T20:10:14)

- **Commune / INSEE** : L'Étang-Salé / 97404
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **9070**
- Sections : **19**
- Bâti (couche) : 0 → **20407**
- Évaluées : **9070 / 9070** (100 %)

## Couches

- batiment : 20407
- voirie : 6986
- pente : 2804
- plu_gpu_zone : 254
- ppr : 6
- sar : 35
- ravine : 169
- plu_gpu_prescription : 247
- osm_faux_positif : 158
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **294**
- À creuser : **1912**
- Écartée : **519**
- Faux positif probable : **6345**
- Taux d'opportunité : **3.2 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 120

## Temps d'exécution

- parcelles : 14s
- couches : 77s
- cascade : 117s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (9070) — 9070 (min 9070)
- ✓ OK   sections présentes — 19
- ✓ OK  [critique] 0 doublon IDU — 9070/9070
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 9070/9070
- ✓ OK  [critique] bâti présent (> 0) — 20407
- ✓ OK  [critique] zonage PLU présent — 254
- ✓ OK  [critique] pente présente — 2804
- ✓ OK  [critique] voirie présente — 6986
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 6 features
- ✓ OK   sar : complet — 35 features
- ✓ OK   ravine : complet — 169 features
- ✓ OK   plu_gpu_prescription : complet — 247 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 9070/9070
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.2 % (294 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

