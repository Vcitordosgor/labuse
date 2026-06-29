# Saint-Philippe — résultats import gold standard (2026-06-29T02:54:47)

- **Commune / INSEE** : Saint-Philippe / 97417
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['couverture zonage ≥ 99 %'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **4162**
- Sections : **29**
- Bâti (couche) : 0 → **4512**
- Évaluées : **4162 / 4162** (100 %)

## Couches

- batiment : 4512
- voirie : 2590
- pente : 5111
- plu_gpu_zone : 19
- ppr : 2
- sar : 56
- ravine : 35
- plu_gpu_prescription : 13
- osm_faux_positif : 35
- abf : absent

- Couverture zonage PLU : **0.2 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **0**
- À creuser : **2408**
- Écartée : **641**
- Faux positif probable : **1113**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 5s
- couches : 98s
- cascade : 207s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (4162) — 4162 (min 4162)
- ✓ OK   sections présentes — 29
- ✓ OK  [critique] 0 doublon IDU — 4162/4162
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 4162/4162
- ✓ OK  [critique] bâti présent (> 0) — 4512
- ✓ OK  [critique] zonage PLU présent — 19
- ✓ OK  [critique] pente présente — 5111
- ✓ OK  [critique] voirie présente — 2590
- ✗ ÉCHEC [critique] couverture zonage ≥ 99 % — 0.2 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 56 features
- ✓ OK   ravine : complet — 35 features
- ✓ OK   plu_gpu_prescription : complet — 13 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 4162/4162
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (None opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

