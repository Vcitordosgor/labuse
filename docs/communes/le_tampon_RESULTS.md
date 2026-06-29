# Le Tampon — résultats import gold standard (2026-06-28T21:15:42)

- **Commune / INSEE** : Le Tampon / 97422
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **42756**
- Sections : **79**
- Bâti (couche) : 0 → **74136**
- Évaluées : **42756 / 42756** (100 %)

## Couches

- batiment : 74136
- voirie : 17349
- pente : 11865
- plu_gpu_zone : 825
- ppr : 2
- sar : 229
- ravine : 583
- plu_gpu_prescription : 1386
- osm_faux_positif : 395
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **788**
- À creuser : **11013**
- Écartée : **1030**
- Faux positif probable : **29925**
- Taux d'opportunité : **1.8 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 171

## Temps d'exécution

- parcelles : 66s
- couches : 256s
- cascade : 2658s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (42756) — 42756 (min 42756)
- ✓ OK   sections présentes — 79
- ✓ OK  [critique] 0 doublon IDU — 42756/42756
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 42756/42756
- ✓ OK  [critique] bâti présent (> 0) — 74136
- ✓ OK  [critique] zonage PLU présent — 825
- ✓ OK  [critique] pente présente — 11865
- ✓ OK  [critique] voirie présente — 17349
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 229 features
- ✓ OK   ravine : complet — 583 features
- ✓ OK   plu_gpu_prescription : complet — 1386 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 42756/42756
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.8 % (788 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

