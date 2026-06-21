# Saint-Louis — résultats import gold standard (2026-06-21T19:20:42)

- **Commune / INSEE** : Saint-Louis / 97414
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 29241 → **29241**
- Sections : **53**
- Bâti (couche) : 0 → **41031**
- Évaluées : **29241 / 29241** (100 %)

## Couches

- batiment : 41031
- voirie : 9020
- pente : 4557
- plu_gpu_zone : 385
- ppr : 4
- sar : 82
- ravine : 509
- plu_gpu_prescription : 684
- osm_faux_positif : 176
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **474**
- À creuser : **4799**
- Écartée : **1307**
- Faux positif probable : **22661**
- Taux d'opportunité : **1.6 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 135

## Temps d'exécution

- parcelles : 29s
- couches : 162s
- cascade : 1649s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (29241) — 29241 (min 29241)
- ✓ OK   sections présentes — 53
- ✓ OK  [critique] 0 doublon IDU — 29241/29241
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 29241/29241
- ✓ OK  [critique] bâti présent (> 0) — 41031
- ✓ OK  [critique] zonage PLU présent — 385
- ✓ OK  [critique] pente présente — 4557
- ✓ OK  [critique] voirie présente — 9020
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 82 features
- ✓ OK   ravine : complet — 509 features
- ✓ OK   plu_gpu_prescription : complet — 684 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 29241/29241
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.6 % (474 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

