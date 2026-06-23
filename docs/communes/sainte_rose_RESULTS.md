# Sainte-Rose — résultats import gold standard (2026-06-23T16:27:53)

- **Commune / INSEE** : Sainte-Rose / 97419
- **Stratégie appliquée** : import_complet
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **6287**
- Sections : **24**
- Bâti (couche) : 0 → **6229**
- Évaluées : **6287 / 6287** (100 %)

## Couches

- batiment : 6229
- voirie : 6941
- pente : 8391
- plu_gpu_zone : 200
- ppr : 2
- sar : 49
- ravine : 456
- plu_gpu_prescription : 293
- osm_faux_positif : 35
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **8**
- À creuser : **1818**
- Écartée : **764**
- Faux positif probable : **3697**
- Taux d'opportunité : **0.1 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 10s
- couches : 206s
- cascade : 1004s
- dédup safer ciblée : 0s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6287) — 6287 (min 6287)
- ✓ OK   sections présentes — 24
- ✓ OK  [critique] 0 doublon IDU — 6287/6287
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6287/6287
- ✓ OK  [critique] bâti présent (> 0) — 6229
- ✓ OK  [critique] zonage PLU présent — 200
- ✓ OK  [critique] pente présente — 8391
- ✓ OK  [critique] voirie présente — 6941
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 49 features
- ✓ OK   ravine : complet — 456 features
- ✓ OK   plu_gpu_prescription : complet — 293 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6287/6287
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.1 % (8 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Validation du run (gates & contexte)

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-sainte-rose-20260623-160441.dump`
  · SHA-256 `b42194cdf5032dd724a0904d5a2e4f7f87af3f99f79153cdff5be38b2cef7bda` (vérifié `sha256sum -c` → OK ; `pg_restore --list` 190 TOC, tables critiques présentes).
- **Dry-run** : OK (état ABSENT, plan cohérent) · confirm phrase `IMPORT_SAINTE_ROSE_COMPLET`.
- **Run initial** : **exit 1** (ROLLBACK) — 1 doublon SAFER exact (cf. section dédup) → **corrigé** : dédup ciblée (gardé `1357411`, supprimé `1357421`, duplication **1 → 0**, `safer` **1 400 → 1 399**) → **post-checks finaux exit 0 / 22 contrôles sur 22 verts**.
- **Parcelles** : **6 287** · **Évaluées** : **6 287 / 6 287** (100 %) · sections **24** · 0 doublon IDU.
- **PLU/GPU propre `DU_97419`** : couverture **100 %** (6 287 / 6 287 ; idurba `97419_PLU_20190504`) · zonage total 100 %.
- **Voirie** : **6 941** — **non tronquée** (≠ 5 000).
- **Bâti** : **6 229** (> 0).
- **DVF** : **126** · **PPR** : **2** · **`osm_faux_positif`** : **35** (ingéré OK) · **prescriptions** : 293 · **doublons couche** : **0**.
- **Verdicts finaux (inchangés après dédup)** : opportunité **8** · à creuser **1 818** · écartée **764** · faux positif probable **3 697**.
- **Taux d'opportunité** : **0,1 %** → **NO-GO gold** (cf. décision ci-dessous).

> ℹ️ Statut : run technique **exit 0** (après dédup `safer`), **non-gold** (Sainte-Rose reste `absent` en config) — NO-GO métier (quasi-0 opportunité).

## Dédup post-run (doublon SAFER)

Le run initial a abouti **exit 1 (ROLLBACK)** : **1 doublon EXACT** de couche `safer` (RPG agricole).
Dédup **ciblée** appliquée (sans rollback, sans re-cascade, sans toucher aux autres lignes).

**Preuve — les 2 lignes, strictement identiques sauf l'`id`** :

| Champ | `1357411` (gardée) | `1357421` (supprimée) |
|---|---|---|
| kind / subtype / name | safer / rpg / Parcelle agricole RPG (CSA) | identiques |
| commune | Sainte-Rose | Sainte-Rose |
| data_source_id / ingestion_run_id | 38 / 47 | 38 / 47 |
| created_at | 2026-06-23 16:07:39.257427+00 | idem |
| geom (type, SRID) | ST_MultiPolygon, 4326 | ST_MultiPolygon, 4326 |
| md5(WKB) / md5(geom_2975) | `ef7b77b2…16ca` / `6176cace…9d5a` | identiques |
| attrs | `{"src":"RPG.LATEST","code_cultu":"CSA","code_group":"26"}` | identiques |
| ST_Equals / ST_OrderingEquals / attrs_eq | — | **true / true / true** |

Suppression **explicite par id** `DELETE FROM spatial_layers WHERE id = 1357421` (transaction gardée,
rollback auto si ≠ 1 ligne) : **deleted=1**, gardée `1357411` intacte, `1357421` supprimée.

**Doublons : 1 → 0.** **Verdicts strictement inchangés** (opportunité 8 · à creuser 1 818 · écartée 764 ·
faux positif probable 3 697, Σ 6 287). `safer` 1 400 → 1 399. Post-checks re-passés (**sans re-cascade**)
→ **exit recalculé : 0** (le doublon `safer` était la **seule** cause technique de l'exit 1).

## Décision : NO-GO gold (quasi-0 opportunité)

Run **techniquement propre après dédup (exit 0)** **MAIS résultat métier NO-GO** : **8 opportunités
(0,1 %)** sur 6 287 → pattern **La Plaine / Les Trois-Bassins** (commune volcan/coulées : 58,8 % faux
positifs + 12,2 % écartées → quasi aucune parcelle libre). Sainte-Rose **reste non-gold / différée**,
arbitrage produit/scoring ultérieur. Data conservée en DB, aucun rollback, aucun gold.

## Conclusion : SUCCÈS TECHNIQUE (exit 0 après dédup `safer`) mais **NO-GO GOLD** — quasi-0 opportunité (8 / 6 287, 0,1 %) ; commune différée

