# Bras-Panon — résultats import gold standard (2026-06-22T12:20:46)

- **Commune / INSEE** : Bras-Panon / 97402
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 6041 → **6041**
- Sections : **14**
- Bâti (couche) : 0 → **14272**
- Évaluées : **6041 / 6041** (100 %)

## Couches

- batiment : 14272
- voirie : 7744
- pente : 5676
- plu_gpu_zone : 243
- ppr : 4
- sar : 54
- ravine : 787
- plu_gpu_prescription : 542
- osm_faux_positif : 125
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **210**
- À creuser : **1624**
- Écartée : **253**
- Faux positif probable : **3954**
- Taux d'opportunité : **3.5 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 61

## Temps d'exécution

- parcelles : 11s
- couches : 207s
- cascade : 218s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6041) — 6041 (min 6041)
- ✓ OK   sections présentes — 14
- ✓ OK  [critique] 0 doublon IDU — 6041/6041
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6041/6041
- ✓ OK  [critique] bâti présent (> 0) — 14272
- ✓ OK  [critique] zonage PLU présent — 243
- ✓ OK  [critique] pente présente — 5676
- ✓ OK  [critique] voirie présente — 7744
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 54 features
- ✓ OK   ravine : complet — 787 features
- ✓ OK   plu_gpu_prescription : complet — 542 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6041/6041
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 3.5 % (210 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Backup pré-commune & synthèse

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-bras-panon-20260622-121132.dump`
- **SHA-256** : `f3c8f436d961be938a23eb1260a2ad984ac171c96f5c9576e8970ca27b722aaa`
- **Code de sortie** : **0** (SUCCÈS)
- **Post-checks** : **22/22 verts** (critiques + QA + infos)
- **Voirie** : **5 000 → 7 744** (déplafonnée, re-fetch paginé)
- **Bâti (couche)** : **0 → 14 272**
- **Couverture zonage (PLU propre `97402`)** : **100 %**
- **Verdicts fiables** : opportunité **210** · à creuser **1 624** · écartée **253** · faux positif probable **3 954**

## Note — lignes d'évaluation « stale » (non bloquant)

Bras-Panon était `partiel_evalue` : la cascade **ajoute** les nouvelles évaluations **sans supprimer**
les anciennes. La table `parcel_evaluations` contient donc **12 082 lignes pour 6 041 parcelles** (×2).
Les verdicts canoniques (**dernière évaluation par parcelle**) sont corrects et **tous les post-checks
passent** (logique « latest » appliquée partout) → **impact fonctionnel nul**. **Aucun nettoyage
effectué ici** (purge éventuelle des évaluations périmées = hors périmètre de ce run).

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

