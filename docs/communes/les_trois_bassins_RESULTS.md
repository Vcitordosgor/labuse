# Les Trois-Bassins — résultats import gold standard (2026-06-23T15:46:28)

- **Commune / INSEE** : Les Trois-Bassins / 97423
- **Stratégie appliquée** : import_complet
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **5314**
- Sections : **9**
- Bâti (couche) : 0 → **7898**
- Évaluées : **5314 / 5314** (100 %)

## Couches

- batiment : 7898
- voirie : 3625
- pente : 2629
- plu_gpu_zone : 224
- ppr : 4
- sar : 50
- ravine : 229
- plu_gpu_prescription : 293
- osm_faux_positif : 33
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **1**
- À creuser : **1265**
- Écartée : **215**
- Faux positif probable : **3833**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 20s
- couches : 111s
- cascade : 504s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (5314) — 5314 (min 5314)
- ✓ OK   sections présentes — 9
- ✓ OK  [critique] 0 doublon IDU — 5314/5314
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 5314/5314
- ✓ OK  [critique] bâti présent (> 0) — 7898
- ✓ OK  [critique] zonage PLU présent — 224
- ✓ OK  [critique] pente présente — 2629
- ✓ OK  [critique] voirie présente — 3625
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 50 features
- ✓ OK   ravine : complet — 229 features
- ✓ OK   plu_gpu_prescription : complet — 293 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 5314/5314
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (1 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Validation du run & décision (NO-GO gold)

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-les-trois-bassins-20260623-153129.dump`
  · SHA-256 `048b944c6798a73190f3a58281490d70ed3b66dcb9969c0022deb4269174f618` (vérifié `sha256sum -c` → OK ; `pg_restore --list` 190 TOC, tables critiques présentes).
- **Dry-run** : OK (état ABSENT, plan cohérent) · confirm phrase `IMPORT_LES_TROIS_BASSINS_COMPLET`.
- **Exit code technique** : **0** (SUCCÈS — tous contrôles critiques verts).
- **Parcelles** : **5 314** · **Évaluées** : **5 314 / 5 314** (100 %) · sections **9** · 0 doublon IDU.
- **PLU/GPU propre `DU_97423`** : couverture **100 %** (5 314 / 5 314 ; idurba `97423_PLU_20220602`).
- **Voirie** : **3 625** — **non tronquée** (≠ 5 000).
- **Bâti** : **7 898** (> 0, dense ≈ 1,49/parcelle).
- **DVF** : **157** · **PPR** : **4** · **`osm_faux_positif`** : **33** (ingéré OK, pas d'échec Overpass) · **prescriptions** : 293 · **doublons couche** : **0**.
- **Verdicts** : opportunité **1** · à creuser **1 265** · écartée **215** · faux positif probable **3 833**.
- **Taux d'opportunité** : **0,0 %**.

> 🔴 **NO-GO GOLD** : run techniquement propre (exit 0) **mais résultat métier = 1 opportunité (0,0 %)** → pattern « quasi-0 opportunité » proche de **La Plaine-des-Palmistes**. Commune **différée** pour arbitrage produit/scoring ultérieur (cf. `les_trois_bassins_NO_GO_QUASI_0_OPPORTUNITE.md`). Data **conservée** en DB, **aucun rollback**, **pas de gold**.

## Conclusion : SUCCÈS TECHNIQUE (exit 0) mais **NO-GO GOLD** — quasi-0 opportunité (1 / 5 314, 0,0 %) ; commune différée (cf. `les_trois_bassins_NO_GO_QUASI_0_OPPORTUNITE.md`)

