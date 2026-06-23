# Sainte-Suzanne — résultats import gold standard (2026-06-23T13:38:38)

- **Commune / INSEE** : Sainte-Suzanne / 97420
- **Stratégie appliquée** : import_complet
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 0 → **12527**
- Sections : **26**
- Bâti (couche) : 0 → **28794**
- Évaluées : **12527 / 12527** (100 %)

## Couches

- batiment : 28794
- voirie : 10884
- pente : 4160
- plu_gpu_zone : 338
- ppr : 4
- sar : 54
- ravine : 417
- plu_gpu_prescription : 481
- osm_faux_positif : 175
- abf : 2

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **321**
- À creuser : **3475**
- Écartée : **212**
- Faux positif probable : **8519**
- Taux d'opportunité : **2.6 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 103

## Temps d'exécution

- parcelles : 13s
- couches : 373s
- cascade (initiale) : 1898s
- osm re-fetch ciblé : 3s
- re-cascade osm-aware : 1892s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (12527) — 12527 (min 12527)
- ✓ OK   sections présentes — 26
- ✓ OK  [critique] 0 doublon IDU — 12527/12527
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 12527/12527
- ✓ OK  [critique] bâti présent (> 0) — 28794
- ✓ OK  [critique] zonage PLU présent — 338
- ✓ OK  [critique] pente présente — 4160
- ✓ OK  [critique] voirie présente — 10884
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 4 features
- ✓ OK   sar : complet — 54 features
- ✓ OK   ravine : complet — 417 features
- ✓ OK   plu_gpu_prescription : complet — 481 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 12527/12527
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 2.6 % (321 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Validation du run (gates & contexte)

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-sainte-suzanne-20260623-125803.dump`
  · SHA-256 `ee199c8fe36a28b3375b1a9fa639a87a5a351c7032b0e0e7431c5db675413caa` (vérifié `sha256sum -c` → OK ; `pg_restore --list` 190 TOC, tables critiques présentes).
- **Dry-run** : OK (état ABSENT, plan cohérent, confirm phrase `IMPORT_SAINTE_SUZANNE_COMPLET`).
- **Run initial** : **exit 3** (RE-FETCH) — couche `osm_faux_positif` en échec (Overpass transitoire). **Corrigé** (cf. section suivante) : re-fetch ciblé `osm_faux_positif` **0 → 175** + re-cascade Sainte-Suzanne uniquement → **exit 0**.
- **Parcelles** : **12 527** · **Évaluées** : **12 527 / 12 527** (100 %) · sections **26**.
- **PLU/GPU propre `DU_97420`** : couverture **100 %** (12 527 / 12 527 ; 191 zones propres, idurba `97420_plu_20250929`). Zonage total 100 %.
- **Voirie** : **10 884** — **non tronquée** (≠ 5 000, pagination OK).
- **Bâti** : **28 794** (> 0).
- **DVF** : **383** mutations (geo-dvf 974).
- **PPR** : **4** (présent).
- **Prescriptions** : **481** — typepsc à risque `DU_97420` : **02=18, 15/24=0** (charge faible).
- **Doublons de couche** : **0** (critère durci `md5(geom_2975)+subtype+name+md5(attrs)`).
- **Verdicts finaux (après OSM)** : opportunité **321** · à creuser **3 475** · écartée **212** · faux positif probable **8 519**.
- **Taux d'opportunité** : **2,6 %** — sain, sous le plafond QA 5 %.
- **Évaluations stale** : l'ancien set `parcel_evaluations` osm-less est **conservé** (non nettoyé) mais **non canonique** — le verdict canonique est la **dernière évaluation par parcelle** (set osm-aware).

> ℹ️ Statut : run corrigé **exit 0**, **non-gold** (Sainte-Suzanne reste `absent` en config). Le passage gold est une étape séparée soumise à validation.

## Correction post-run (osm_faux_positif)

Le run initial a abouti **exit 3 (RE-FETCH)** : la couche `osm_faux_positif` (Overpass) avait échoué
(saturation transitoire) → 0 ligne. Cette couche alimente le **déclassement** (`scoring/declassement.py`).
Correction **ciblée** appliquée (sans rollback, sans ré-import, sans toucher aux autres couches/communes) :

- **Re-fetch ciblé `osm_faux_positif`** (Sainte-Suzanne uniquement, `ingest_osm_faux_positifs`, bbox commune) :
  **0 → 175** features (parking 115, pitch 45, school 12, cemetery 3) ; réussi à la 1ʳᵉ tentative · 3 s.
- **Re-cascade Sainte-Suzanne uniquement** (`evaluate_commune`) : 12 527 parcelles ré-évaluées · 1 892 s
  (verdict canonique = dernière éval/parcelle ; ancien set osm-less conservé, non nettoyé).

Verdicts **avant (osm-less) → après (osm-aware)** : opportunité 329 → **321** · à creuser 3 482 → 3 475 ·
écartée 205 → **212** · faux positif probable 8 511 → **8 519**. Le filtre OSM a déclassé ~8 « opportunités »
(équipements publics : cimetière/école/terrain/parking). **Exit recalculé : 0 (SUCCÈS).**

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

