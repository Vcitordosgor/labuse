# Saint-Louis — résultats import gold standard (2026-06-28T22:01:44)

- **Commune / INSEE** : Saint-Louis / 97414
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **29241**
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
- plu_gpu_prescription : 686
- osm_faux_positif : 176
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 2 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **488**
- À creuser : **4230**
- Écartée : **1325**
- Faux positif probable : **23198**
- Taux d'opportunité : **1.7 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 134

## Temps d'exécution

- parcelles : 14s
- couches : 96s
- cascade : 1131s

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
- ✗ ÉCHEC [critique] aucune duplication de couche — 2 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 82 features
- ✓ OK   ravine : complet — 509 features
- ✓ OK   plu_gpu_prescription : complet — 686 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 29241/29241
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.7 % (488 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

