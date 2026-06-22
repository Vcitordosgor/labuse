# Saint-Joseph — résultats import gold standard (2026-06-22T11:05:45)

- **Commune / INSEE** : Saint-Joseph / 97412
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 28959 → **28959**
- Sections : **57**
- Bâti (couche) : 0 → **25454**
- Évaluées : **28959 / 28959** (100 %)

## Couches

- batiment : 25454
- voirie : 8909
- pente : 8488
- plu_gpu_zone : 435
- ppr : 4
- sar : 155
- ravine : 482
- plu_gpu_prescription : 476
- osm_faux_positif : 211
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **530**
- À creuser : **7653**
- Écartée : **1032**
- Faux positif probable : **19744**
- Taux d'opportunité : **1.8 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 120

## Temps d'exécution

- parcelles : 27s
- couches : 299s
- cascade : 6090s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (28959) — 28959 (min 28959)
- ✓ OK   sections présentes — 57
- ✓ OK  [critique] 0 doublon IDU — 28959/28959
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 28959/28959
- ✓ OK  [critique] bâti présent (> 0) — 25454
- ✓ OK  [critique] zonage PLU présent — 435
- ✓ OK  [critique] pente présente — 8488
- ✓ OK  [critique] voirie présente — 8909
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 155 features
- ✓ OK   ravine : complet — 482 features
- ✓ OK   plu_gpu_prescription : complet — 476 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 28959/28959
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.8 % (530 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Performance à surveiller

⚠️ Cascade anormalement lente sur ce run : **6090 s (~1 h 41)** pour 28 959 parcelles, soit ~3,7× le débit habituel (~1650 s attendu pour ce volume). Batchs à temps très variable (certains ~14 min). Run **fonctionnellement correct** (100 % évaluées, verdicts cohérents, doublon dédupliqué).

Cause probable : **statistiques du planificateur périmées** après la ré-ingestion massive des couches (étape D) — le join spatial `ST_Intersects` n'exploite pas l'index GIST de façon optimale. **Aucune optimisation lancée ici.** Piste à étudier séparément (hors périmètre de ce run) : `ANALYZE spatial_layers` après l'étape D dans le script générique.

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

