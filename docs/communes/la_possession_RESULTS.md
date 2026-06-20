# La Possession — résultats import gold standard (2026-06-20T20:12:01)

- **Commune / INSEE** : La Possession / 97408
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 13338 → **13338**
- Sections : **30**
- Bâti (couche) : 0 → **42217**
- Évaluées : **13338 / 13338** (100 %)

## Couches

- batiment : 42217
- voirie : 5000
- pente : 10115
- plu_gpu_zone : 663
- ppr : 2
- sar : 29
- ravine : 1169
- plu_gpu_prescription : 52
- osm_faux_positif : 360
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **420**
- À creuser : **4141**
- Écartée : **790**
- Faux positif probable : **7987**
- Taux d'opportunité : **3.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 143

## Temps d'exécution

- parcelles : 16s
- couches : 244s
- cascade : 506s

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
- ✓ OK  [critique] voirie présente — 5000
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 29 features
- ✓ OK   ravine : complet — 1169 features
- ✓ OK   plu_gpu_prescription : complet — 52 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 13338/13338
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.1 % (420 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

