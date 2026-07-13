# Golden dataset — parcelles étalon (M6 Phase 1 §1.2)

- **Référence** : `reports/m6-audit/golden/golden-parcelles.json` (générée le 2026-07-13T08:43:54)
- **Run cascade** : `q_v3_datagap` · **Run v2 servi** : `m36-l2f-2026-2026-07-12` · **API** : http://127.0.0.1:8010
- **Contrôleur** : `qa/golden_check.py` (usage en tête de fichier) — exit 0 = 100 % PASS
- **Tolérances** : canopee_pct ±2.0, distance_cote_m ±10.0, mult_base ±0.011, ndvi_moyen ±0.03, obstruction_pct ±2.0, pente_moy_deg ±0.5, percentile ±0.11, prod_spec_kwh_kwc ±5.0, surface_m2 ±1.0 ; le reste en égalité stricte.

| IDU | Commune | Rôle dans le set | Tier v2 (rang) | Statut cascade | Étage 0 (motifs) | Surface m² | Zone PLU | Couches notables |
|---|---|---|---|---|---|---|---|---|
| 97410000AS1425 | Saint-Benoît | Témoin M5.1 (obligatoire) — brûlante, veille succession, permis récent, PM, vue mer | brulante (16) | ecartee | non | 300 | AUc | vue mer, solaire 92, veille succession, permis 2025-05-15 |
| 97410000CD0905 | Saint-Benoît | Témoin M5.1 — brûlante r8, Saint-Benoît | brulante (8) | ecartee | non | 334 | AUc | permis 2024-06-05 |
| 97423000AB1908 | Les Trois-Bassins | Témoin M5.1 (obligatoire) — brûlante rang 1 | brulante (1) | ecartee | non | 313 | AUc | vue mer, permis 2024-03-11 |
| 97423000AB1341 | Les Trois-Bassins | Témoin M5.1 — écartée étage 0 (PPR rouge + zonage N) | ecartee (19) | ecartee | oui — risques, zonage_plu_gpu | 355 | N 95 % | vue mer, permis 2024-11-08 |
| 97415000EY1509 | Saint-Paul | Témoin M5.1 — réserve foncière, propriétaire bailleur | reserve_fonciere (231 138) | chaude | non | 1352 | U | bailleur |
| 97411000KA0296 | Saint-Denis | Brûlante r7 — Saint-Denis (chef-lieu) | brulante (7) | ecartee | non | 300 | AUc | solaire 64, permis 2025-01-29 |
| 97422000AD1237 | Le Tampon | Brûlante r17 — Le Tampon (hauts urbains) | brulante (17) | a_creuser | non | 599 | AUs | solaire 69, permis 2025-02-05 |
| 97403000AR1423 | Entre-Deux | Brûlante r28 — Entre-Deux (commune non premium, hauts) | brulante (28) | ecartee | non | 298 | U | permis 2025-11-13 |
| 97418000AT2379 | Sainte-Marie | Brûlante r9 — Sainte-Marie | brulante (9) | ecartee | non | 253 | U | solaire 74, permis 2025-11-19 |
| 97413000CD0729 | Saint-Leu | Brûlante r194 MAIS étage 0 (foncier public) — 1 des 2 brûlantes écartées (117 effectives) | brulante (194) | ecartee | oui — foncier_public | 337 | AU | permis 2025-04-04, public |
| 97408000AP1647 | La Possession | Chaude rang 2 — cas frontière tiers (devant des brûlantes) | chaude (2) | a_creuser | non | 382 | AUc | solaire 42, permis 2025-10-27 |
| 97415000CX1395 | Saint-Paul | Chaude r22 — piscine détectée (ortho), Saint-Paul | chaude (22) | a_creuser | non | 608 | U | permis 2024-06-05 |
| 97410000AS1450 | Saint-Benoît | Chaude r37 — veille succession (dirigeant 73 ans) | chaude (37) | ecartee | non | 477 | AUc | solaire 92, veille succession, permis 2024-02-12 |
| 97422000AX1253 | Le Tampon | Chaude r56 — mutation DVF récente (2025-09) | chaude (56) | ecartee | non | 27084 | AUs | solaire 45, DVF 2025-09-05 |
| 97420000AO0654 | Sainte-Suzanne | Chaude r35 — Sainte-Suzanne (géocodage permis 64,6 %) | chaude (35) | ecartee | non | 366 | U | vue mer, solaire 81, permis 2026-05-12 |
| 97407000BI0350 | Le Port | Chaude r707 — Le Port, score solaire 44 | chaude (707) | a_creuser | non | 683 | AUc | solaire 44, veille succession, DVF 2025-04-16 |
| 97408000AC1870 | La Possession | Réserve foncière — canopée 87 % (LiDAR) | reserve_fonciere (230 109) | a_surveiller | non | 3462 | U | canopée 87% |
| 97416000CR1351 | Saint-Pierre | Réserve foncière — vue mer, MAIS étage 0 foncier public (tier non aligné) | reserve_fonciere (229 673) | ecartee | oui — foncier_public | 3562 | AUs | vue mer, solaire 90, public |
| 97409000AX0289 | Saint-André | Réserve foncière — vue mer à 83 m de la côte, Saint-André | reserve_fonciere (229 538) | a_surveiller | non | 2599 | U | vue mer, solaire 86, permis 2020-12-30 |
| 97415000CW1056 | Saint-Paul | À creuser rang 33 — cas frontière (rang bas, tier bas) | a_creuser (33) | ecartee | non | 130 | — | permis 2025-05-15 |
| 97413000CS0160 | Saint-Leu | À creuser — DPE G rattaché | a_creuser (6 817) | ecartee | non | 581 | U | vue mer, DPE G, DVF 2025-08-28 |
| 97411000AL0360 | Saint-Denis | À creuser — copro RNIC 31 lots, copro=true, rang NULL (hors classement) | a_creuser (—) | ecartee | non | 439 | U | solaire 96, copro RNIC×1, permis 2015-12-23, DVF 2024-12-10 |
| 97402000AK1725 | Bras-Panon | À creuser — cas pauvre en données (a_completude 67) | a_creuser (56 295) | ecartee | non | 735 | U | vue mer, solaire 76, permis 2016-12-22 |
| 97424000AI0355 | Cilaos | À creuser — Cilaos (cirque, non littoral), a_completude 67 | a_creuser (150 803) | a_creuser | non | 679 | U | — |
| 97413000DM0210 | Saint-Leu | Écartée v2 (étage 0 bâti) — DPE F rattaché | ecartee (48 453) | ecartee | oui — bati | 687 | U | DPE F |
| 97422000BY0489 | Le Tampon | Écartée v2 (étage 0 prescription PLU) — DPE F | ecartee (9 845) | ecartee | oui — prescription_plu | 481 | U | DPE F, DVF 2025-03-11 |
| 97424000AD0409 | Cilaos | Étage 0 — motif zonage A (+bâti, surface 8 m²), Cilaos | ecartee (109 664) | ecartee | oui — bati, risques, surface, zonage_plu_gpu | 8 | A 100 % | solaire 40 |
| 97416000CD0765 | Saint-Pierre | Étage 0 — motif surface (+bâti), Saint-Pierre | ecartee (120 447) | ecartee | oui — bati, surface | 95 | U | solaire 48 |
| 97411000AO0748 | Saint-Denis | Étage 0 — motif foncier public, Saint-Denis | a_creuser (218 645) | ecartee | oui — foncier_public | 7483 | U | vue mer, solaire 96, public |
| 97419000AC0159 | Sainte-Rose | Étage 0 — motif emprise linéaire/voirie (+surface), Sainte-Rose | ecartee (289 940) | ecartee | oui — emprise_lineaire, surface | 43 | U | solaire 71 |
| 97421000AC0156 | Salazie | Étage 0 — motif pente (+risques), Salazie | ecartee (406 570) | ecartee | oui — pente, risques | 1092 | — | — |
| 97405000AB0168 | Petite-Île | Étage 0 — motif bâti (+risques, zonage), Petite-Île | ecartee (319 800) | ecartee | oui — bati, risques, zonage_plu_gpu | 4403 | A 100 % | — |

Les valeurs complètes (toutes couches, base ET API, cohérence base↔API) sont dans le JSON ; chaque entrée porte `db` (18 blocs de couches), `api` (fiche premium + /v2/score) et `coherence_db_api` (vide = cohérent).
