# Le Port — résultats import gold standard (2026-06-29T00:59:12)

- **Commune / INSEE** : Le Port / 97407
- **Stratégie appliquée** : gold_valide
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **10195**
- Sections : **26**
- Bâti (couche) : 0 → **15828**
- Évaluées : **10195 / 10195** (100 %)

## Couches

- batiment : 15828
- voirie : 4897
- pente : 768
- plu_gpu_zone : 159
- ppr : 2
- sar : 84
- ravine : 66
- plu_gpu_prescription : 218
- osm_faux_positif : 517
- abf : 1

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **237**
- À creuser : **2117**
- Écartée : **912**
- Faux positif probable : **6929**
- Taux d'opportunité : **2.3 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 14

## Temps d'exécution

- parcelles : 6s
- couches : 36s
- cascade : 162s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (10195) — 10195 (min 10195)
- ✓ OK   sections présentes — 26
- ✓ OK  [critique] 0 doublon IDU — 10195/10195
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 10195/10195
- ✓ OK  [critique] bâti présent (> 0) — 15828
- ✓ OK  [critique] zonage PLU présent — 159
- ✓ OK  [critique] pente présente — 768
- ✓ OK  [critique] voirie présente — 4897
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 84 features
- ✓ OK   ravine : complet — 66 features
- ✓ OK   plu_gpu_prescription : complet — 218 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 10195/10195
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 2.3 % (237 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

