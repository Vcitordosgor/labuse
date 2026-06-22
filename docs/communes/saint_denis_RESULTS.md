# Saint-Denis — résultats import gold standard (2026-06-21T22:52:20)

- **Commune / INSEE** : Saint-Denis / 97411
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 38138 → **38138**
- Sections : **124**
- Bâti (couche) : 0 → **61522**
- Évaluées : **38138 / 38138** (100 %)

## Couches

- batiment : 61522
- voirie : 13542
- pente : 6900
- plu_gpu_zone : 369
- ppr : 2
- sar : 263
- ravine : 856
- plu_gpu_prescription : 3066
- osm_faux_positif : 718
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **84**
- À creuser : **11643**
- Écartée : **2165**
- Faux positif probable : **24246**
- Taux d'opportunité : **0.2 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 53s
- couches : 245s
- cascade : 2767s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (38138) — 38138 (min 38138)
- ✓ OK   sections présentes — 124
- ✓ OK  [critique] 0 doublon IDU — 38138/38138
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 38138/38138
- ✓ OK  [critique] bâti présent (> 0) — 61522
- ✓ OK  [critique] zonage PLU présent — 369
- ✓ OK  [critique] pente présente — 6900
- ✓ OK  [critique] voirie présente — 13542
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 263 features
- ✓ OK   ravine : complet — 856 features
- ✓ OK   plu_gpu_prescription : complet — 3066 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 38138/38138
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.2 % (84 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

