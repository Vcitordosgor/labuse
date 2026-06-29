# Cilaos — résultats import gold standard (2026-06-29T03:27:00)

- **Commune / INSEE** : Cilaos / 97424
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **6560**
- Sections : **13**
- Bâti (couche) : 0 → **5584**
- Évaluées : **6560 / 6560** (100 %)

## Couches

- batiment : 5584
- voirie : 2327
- pente : 4080
- plu_gpu_zone : 232
- ppr : 2
- sar : 31
- ravine : 402
- plu_gpu_prescription : 255
- osm_faux_positif : 95
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **4**
- À creuser : **1429**
- Écartée : **1467**
- Faux positif probable : **3660**
- Taux d'opportunité : **0.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 14s
- couches : 79s
- cascade : 532s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6560) — 6560 (min 6560)
- ✓ OK   sections présentes — 13
- ✓ OK  [critique] 0 doublon IDU — 6560/6560
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6560/6560
- ✓ OK  [critique] bâti présent (> 0) — 5584
- ✓ OK  [critique] zonage PLU présent — 232
- ✓ OK  [critique] pente présente — 4080
- ✓ OK  [critique] voirie présente — 2327
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 31 features
- ✓ OK   ravine : complet — 402 features
- ✓ OK   plu_gpu_prescription : complet — 255 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6560/6560
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.1 % (4 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

