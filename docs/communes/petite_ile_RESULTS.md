# Petite-Île — résultats import gold standard (2026-06-29T01:06:09)

- **Commune / INSEE** : Petite-Île / 97405
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **13137**
- Sections : **25**
- Bâti (couche) : 0 → **17222**
- Évaluées : **13137 / 13137** (100 %)

## Couches

- batiment : 17222
- voirie : 6585
- pente : 2272
- plu_gpu_zone : 477
- ppr : 4
- sar : 70
- ravine : 124
- plu_gpu_prescription : 144
- osm_faux_positif : 67
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **116**
- À creuser : **1684**
- Écartée : **217**
- Faux positif probable : **11120**
- Taux d'opportunité : **0.9 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 26

## Temps d'exécution

- parcelles : 6s
- couches : 95s
- cascade : 307s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (13137) — 13137 (min 13137)
- ✓ OK   sections présentes — 25
- ✓ OK  [critique] 0 doublon IDU — 13137/13137
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 13137/13137
- ✓ OK  [critique] bâti présent (> 0) — 17222
- ✓ OK  [critique] zonage PLU présent — 477
- ✓ OK  [critique] pente présente — 2272
- ✓ OK  [critique] voirie présente — 6585
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 70 features
- ✓ OK   ravine : complet — 124 features
- ✓ OK   plu_gpu_prescription : complet — 144 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 13137/13137
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.9 % (116 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

