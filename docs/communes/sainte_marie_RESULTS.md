# Sainte-Marie — résultats import gold standard (2026-06-23T12:10:08)

- **Commune / INSEE** : Sainte-Marie / 97418
- **Stratégie appliquée** : import_complet
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **16746**
- Sections : **33**
- Bâti (couche) : 0 → **48795**
- Évaluées : **16746 / 16746** (100 %)

## Couches

- batiment : 48795
- voirie : 12745
- pente : 4977
- plu_gpu_zone : 423
- ppr : absent
- sar : 122
- ravine : 578
- plu_gpu_prescription : 1093
- osm_faux_positif : 532
- abf : 3

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **757**
- À creuser : **5142**
- Écartée : **424**
- Faux positif probable : **10423**
- Taux d'opportunité : **4.5 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 167

## Temps d'exécution

- parcelles : 22s
- couches : 183s
- cascade : 739s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (16746) — 16746 (min 16746)
- ✓ OK   sections présentes — 33
- ✓ OK  [critique] 0 doublon IDU — 16746/16746
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 16746/16746
- ✓ OK  [critique] bâti présent (> 0) — 48795
- ✓ OK  [critique] zonage PLU présent — 423
- ✓ OK  [critique] pente présente — 4977
- ✓ OK  [critique] voirie présente — 12745
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : absent/partiel — None features
- ✓ OK   sar : complet — 122 features
- ✓ OK   ravine : complet — 578 features
- ✓ OK   plu_gpu_prescription : complet — 1093 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 16746/16746
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 4.5 % (757 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Validation du run (gates & contexte)

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-sainte-marie-20260623-115133.dump`
  · SHA-256 `52b34fb5f12bbaf20e4ac5d07e189331ff615cb4eda27fbc9c0fe0703fb28595` (vérifié `sha256sum -c` → OK ; `pg_restore --list` 190 TOC, tables critiques présentes).
- **Run** : exit **0** (SUCCÈS) · stratégie `import_complet`.
- **Parcelles** : **16 746** · **Évaluées** : **16 746 / 16 746** (100 %) · sections **33**.
- **PLU/GPU propre `DU_97418`** : couverture **100 %** (16 746 / 16 746 ; 268 zones propres, idurba `97418_plu_20251126`). Zonage total 100 %.
- **Voirie** : **12 745** — **non tronquée** (≠ 5 000, pagination OK).
- **Bâti** : **48 795** (> 0).
- **DVF** : **967** mutations (geo-dvf 974).
- **Prescriptions** : **1 093** — **vigilance typepsc 02/15/24** (DU_97418 : 02=368, 15=11, 24=10) ; sans impact anormal sur le résultat.
- **Doublons de couche** : **0** (critère durci `md5(geom_2975)+subtype+name+md5(attrs)` ET cross-check `ST_AsBinary+attrs` tous kinds).
- **Verdicts** : opportunité **757** · à creuser **5 142** · écartée **424** · faux positif probable **10 423**.
- **Taux d'opportunité** : **4,5 %** — **accepté avec vigilance** (sous le seuil QA 5 % ; le plus haut des communes, légitimé par le bâti dense 48 795 → faux positifs réactivés 62,2 %).

> ℹ️ Statut : run validé, **non-gold** (Sainte-Marie reste `absent` en config). Le passage gold est une étape séparée soumise à validation.

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

