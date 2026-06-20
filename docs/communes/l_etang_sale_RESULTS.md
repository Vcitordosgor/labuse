# L'Étang-Salé — résultats import gold standard (2026-06-20T20:47:17)

- **Commune / INSEE** : L'Étang-Salé / 97404
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 9070 → **9070**
- Sections : **19**
- Bâti (couche) : 0 → **20407**
- Évaluées : **9070 / 9070** (100 %)

## Couches

- batiment : 20407
- voirie : 5000
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

- Opportunité : **286**
- À creuser : **2696**
- Écartée : **482**
- Faux positif probable : **5606**
- Taux d'opportunité : **3.2 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 100

## Temps d'exécution

- parcelles : 11s
- couches : 101s
- cascade : 312s

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
- ✓ OK  [critique] voirie présente — 5000
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 6 features
- ✓ OK   sar : complet — 35 features
- ✓ OK   ravine : complet — 169 features
- ✓ OK   plu_gpu_prescription : complet — 247 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 9070/9070
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.2 % (286 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

