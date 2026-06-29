# La Possession — résultats import gold standard (2026-06-28T20:06:44)

- **Commune / INSEE** : La Possession / 97408
- **Stratégie appliquée** : gold_valide
- **Verdict** : ROLLBACK RECOMMANDÉ — contrôles critiques KO ['aucune duplication de couche'] (code de sortie 1)

## État avant → après

- Parcelles : 0 → **13338**
- Sections : **30**
- Bâti (couche) : 0 → **42217**
- Évaluées : **13338 / 13338** (100 %)

## Couches

- batiment : 42217
- voirie : 11825
- pente : 10115
- plu_gpu_zone : 663
- ppr : 2
- sar : 29
- ravine : 1169
- plu_gpu_prescription : 524
- osm_faux_positif : 360
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 1 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **553**
- À creuser : **4054**
- Écartée : **790**
- Faux positif probable : **7941**
- Taux d'opportunité : **4.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 177

## Temps d'exécution

- parcelles : 4s
- couches : 226s
- cascade : 151s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (13338) — 13338 (min 13338)
- ✓ OK   sections présentes — 30
- ✓ OK  [critique] 0 doublon IDU — 13338/13338
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 13338/13338
- ✓ OK  [critique] bâti présent (> 0) — 42217
- ✓ OK  [critique] zonage PLU présent — 663
- ✓ OK  [critique] pente présente — 10115
- ✓ OK  [critique] voirie présente — 11825
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✗ ÉCHEC [critique] aucune duplication de couche — 1 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 29 features
- ✓ OK   ravine : complet — 1169 features
- ✓ OK   plu_gpu_prescription : complet — 524 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 13338/13338
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 4.1 % (553 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : ROLLBACK RECOMMANDÉ — restaurer le backup pré-commune

