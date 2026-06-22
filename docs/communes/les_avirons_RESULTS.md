# Les Avirons — résultats import gold standard (2026-06-22T13:14:04)

- **Commune / INSEE** : Les Avirons / 97401
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 8611 → **8611**
- Sections : **15**
- Bâti (couche) : 0 → **18077**
- Évaluées : **8611 / 8611** (100 %)

## Couches

- batiment : 18077
- voirie : 6063
- pente : 3500
- plu_gpu_zone : 240
- ppr : 6
- sar : 38
- ravine : 286
- plu_gpu_prescription : 62
- osm_faux_positif : 63
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **104**
- À creuser : **1260**
- Écartée : **794**
- Faux positif probable : **6453**
- Taux d'opportunité : **1.2 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 33

## Temps d'exécution

- parcelles : 12s
- couches : 161s
- cascade : 377s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (8611) — 8611 (min 8611)
- ✓ OK   sections présentes — 15
- ✓ OK  [critique] 0 doublon IDU — 8611/8611
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 8611/8611
- ✓ OK  [critique] bâti présent (> 0) — 18077
- ✓ OK  [critique] zonage PLU présent — 240
- ✓ OK  [critique] pente présente — 3500
- ✓ OK  [critique] voirie présente — 6063
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 6 features
- ✓ OK   sar : complet — 38 features
- ✓ OK   ravine : complet — 286 features
- ✓ OK   plu_gpu_prescription : complet — 62 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 8611/8611
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 1.2 % (104 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Backup pré-commune & synthèse

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-les-avirons-20260622-130253.dump`
- **SHA-256** : `d4c48850d331ea7042088a039aa9c310ca92b22dcd74a77bf054ecb4533f9bda`
- **Code de sortie** : **0** (SUCCÈS)
- **Post-checks** : **22/22 verts** (critiques + QA + infos)
- **Voirie** : **5 000 → 6 063** (déplafonnée, re-fetch paginé)
- **Bâti (couche)** : **0 → 18 077**
- **Couverture zonage** : **100 % total** / **99,99 % par le PLU propre `97401`** (≥ 99 %)
- **Verdicts fiables** : opportunité **104** · à creuser **1 260** · écartée **794** · faux positif probable **6 453**

## Note — lignes d'évaluation « stale » (non bloquant)

Les Avirons était `partiel_evalue` : la cascade **ajoute** les nouvelles évaluations **sans supprimer**
les anciennes. La table `parcel_evaluations` contient donc **17 222 lignes pour 8 611 parcelles** (×2).
Les verdicts canoniques (**dernière évaluation par parcelle**) sont corrects et **tous les post-checks
passent** (logique « latest » appliquée partout) → **impact fonctionnel nul**. **Aucun nettoyage
effectué ici** (purge éventuelle des évaluations périmées = hors périmètre de ce run).

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

