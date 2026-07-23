# LABUSE en chiffres — inventaire quantifié

> **Audit `audit/panorama` · M9 · Lecture seule · 2026-07-23**
> Valeurs mesurées ce jour sur la base `labuse` (21 Go) et l'arbre de travail. Les rares valeurs issues d'un document plutôt que d'une mesure directe sont annotées « (doc) ». Document destiné à la démo et à la levée : chaque chiffre est traçable à sa source.

---

## 1. Les données (base PostgreSQL)

| Métrique | Valeur | Source |
|---|---|---|
| Taille totale de la base | **21 Go** | `pg_database_size` |
| Nombre de tables | **233** | `pg_stat_user_tables` |
| Total de lignes (toutes tables) | **~73,2 millions** (73 227 750) | `sum(n_live_tup)` |
| **Parcelles cadastrales** (unité de base) | **431 663** | `p_model_geo` / `parcel_amenites` (exact, récurrent) |
| Communes couvertes | **24 / 24** — l'île entière | parcels |
| Permis de construire (Sitadel) | **50 043** | `sitadel_permits` |
| Mutations DVF | **29 565** (fait) · 110 463 (historique) · 102 551 (par parcelle) | `dvf_mutations*` |
| DPE (ADEME 974) | **914** — gisement complet | `dpe_records` |
| Parcelles effectivement scorées (run servi) | **431 663** | `p_model_scores_2026` |

### Les 30 plus grosses tables

| # | Table | Lignes | # | Table | Lignes |
|--:|---|--:|--:|---|--:|
| 1 | dryrun_cascade_results | 36 241 842 | 16 | m6_snapshot_mvt_post2b | 431 663 |
| 2 | cascade_results | 9 175 136 | 17 | p_model_frame | 431 663 |
| 3 | p_model_ext_dataset | 4 318 880 | 18 | parcel_viabilisation | 431 663 |
| 4 | parcel_p_score_v2 | 2 590 707 | 19 | parcel_v_score | 431 663 |
| 5 | p_model_dataset | 2 158 295 | 20 | parcel_vegetation | 426 107 |
| 6 | dryrun_parcel_evaluations | 1 982 365 | 21 | parcel_terrain | 423 452 |
| 7 | score_snapshot_parcelles | 1 726 652 | 22 | adresse_parcelles | 416 357 |
| 8 | spatial_layers | 1 338 818 | 23 | p_model_filo | 385 379 |
| 9 | vegetation_zonal_acc | 1 156 556 | 24 | adresses | 341 426 |
| 10 | parcel_evaluations | 1 003 033 | 25 | parcel_zone_plu | 305 017 |
| 11 | pm_proprietaires_millesimes | 461 570 | 26 | p_model_bati | 304 488 |
| 12 | parcels | 432 146 | 27 | parcel_anc | 278 685 |
| 13 | parcel_amenites | 431 663 | 28 | parcel_residuel | 263 169 |
| 14 | p_model_geo | 431 663 | 29 | parcel_adresse | 257 145 |
| 15 | parcel_solar | 431 663 | 30 | p_model_ext_dvf | 213 014 |

Également notables : `dvf_mutations_histo` 110 463 · `parcelle_personne_morale` 82 701 · `score_e` 77 718 · `parcel_signals` 69 357 · `m10_permit_delais` 50 290 · `ortho_detections` 43 448 · `pm_dirigeants` 27 146 · `solar_grid` 15 680 · `filosofi_carreaux_200m` 14 773.

---

## 2. Sources & couches

| Métrique | Valeur | Source |
|---|---|---|
| **Sources de données ingérées** (registre `data_sources`) | **52** | table `data_sources` |
| Sources surveillées par le radar | **52** (les mêmes) | `src/labuse/radar.py` + cron hebdo `deploy/cron.d/radar` |
| Catégories de sources | **24** | `distinct category` |
| Couches réglementaires / risque / urbanisme / patrimoine | **14** | catégories risques(7)+réglement(3)+urbanisme(2)+patrimoine(1)+réglementaire(1) |
| Couches spatiales — types distincts (`kind`) | **32** | `spatial_layers` |
| Objets spatiaux ingérés | **1 338 818** | `spatial_layers` |
| Crons planifiés | **9** | `deploy/cron.d/` : abuse, backup, ban, bodacc, catnat, dpe, dvf, radar, sitadel |

Types de couches les plus volumineux : bâtiment 817 506 · voirie 235 643 · pente 147 398 · SAFER 38 460 · trait de côte 24 168 · aménité 14 933 · ravine 12 716 · prescriptions PLU-GPU 10 490 · zones PLU-GPU 5 848 · OCS-GE 3 250 · ICPE 1 252 · aléas Géorisques 993 · sols pollués 486 · SUP 417.

---

## 3. Le modèle

| Métrique | Valeur | Source |
|---|---|---|
| **Golden set** (jeu de contrôle) | **116 parcelles**, 116/116 PASS | `reports/m6-audit/golden/golden-parcelles.json` (run servi `q_v7_defisc`) |
| Score V — familles de signaux | **5** (A Détresse juridique · B Cycle de vie proprio · C Détachement géo · D Dormance actif · E Pression réglementaire DPE) | `score_v_constants.py` `FAMILY_CAPS {A:35, B:25, C:15, D:25, E:15}` |
| Score V — signaux barémés | **~22** codes (BODACC, RNE, GEO, FRICHE, DVF, DPE…) | `SIGNALS` dict |
| Matrice de statut | **Q × A** (Qualité × Accessibilité), seuils Q≥65 · A≥60 · complétude≥50 | `config/scoring_matrice.yaml` |
| Poids d'opportunité | **30** paramètres | `config/opportunity_weights.yaml` |
| Presets de segments (moteur Habitat/Vues) | **18** (14 actifs, 4 désactivés) | `config/segment_presets.yaml` |
| **Outils métier « O » exposés** | **14** (O0 → O12 + O0b) | `docs/mandats/OUTILS_SUITE.md` (doc) |
| Sous-commandes CLI `labuse` | ~90 | `src/labuse/cli.py` |

> **Note pour le pitch** — le registre traçable est de **14 outils « O »**. Un « ~27 outils » n'est pas formalisé dans un registre unique (il additionne outils + presets + modules). Formulation recommandée et défendable : **« 18 segments de prospection + 14 outils métier »**.

---

## 4. Le code

| Langage / catégorie | Fichiers | Lignes |
|---|--:|--:|
| Python (`src` + `scripts`) | **238** | **51 842** |
| — dont `src/labuse` | 199 | 45 458 |
| — dont `scripts` | 39 | 6 384 |
| Front TS + TSX (`frontend/src`) | **51** | **11 395** |
| — dont `.tsx` | 38 | 9 700 |
| — dont `.ts` | 13 | 1 695 |
| **Total Python + Front** | **289 fichiers** | **~63 200 lignes** |

### Tests & endpoints

| Métrique | Valeur | Source |
|---|---|---|
| Fichiers de tests | **146** | `find tests -name test_*.py` |
| Fonctions de test | **1 124** (suite documentée **1 125/0**) | `grep 'def test_'` |
| Harnais QA (`qa/*.mjs` + golden + smoke) | **21** | `qa/` |
| Modules API (`src/labuse/api/*.py`) | **44** | |
| **Endpoints HTTP** | **204** | GET 131 · POST 63 · DELETE 6 · PATCH 3 · PUT 1 |

---

## 5. Le calcul — la « grande passe »

| Métrique | Valeur | Source |
|---|---|---|
| Parcelles évaluées par passe complète | **431 663** | `p_model_scores_2026` |
| Empreinte brute d'une passe de cascade | **36,2 M** lignes (`dryrun_cascade_results`) + 9,2 M (`cascade_results`) | tables |
| Convention « chaudes » île | **719 chaudes / 166 dossiers** (Q≥65·A≥60·complétude≥50) | `config/scoring_matrice.yaml` (doc) |
| Réingestion Mac→VPS | `deploy/scripts/sync-run.sh` : dump ciblé des **10 tables** de la grande passe → transfert checksum → bascule | (doc) |
| PDF « dossier banquier » | **~9,3 s** de génération → rendu asynchrone (clic instantané), cache LRU 32×(idu,run), PDF servi ~6 ms | rapports perf BLOC B (doc) |
| Liste / tuiles (perf BLOC B) | liste ×30, tuiles ×8 | rapports perf (doc) |

---

## Statistiques-phares (les plus solides à mettre en avant)

1. **431 663 parcelles · 24/24 communes · 100 % de couverture** — la statistique reine, exacte et récurrente.
2. **73,2 M de lignes · 21 Go · 233 tables · 52 sources** ingérées et surveillées.
3. **116/116 golden vert · 1 124 tests · 204 endpoints · ~63 200 lignes de code.**
4. **32 types de couches spatiales · 1,34 M d'objets géographiques.**

*Fin M9.*
