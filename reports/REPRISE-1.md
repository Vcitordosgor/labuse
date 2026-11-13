# REPRISE-1 — preuve de restauration (dump 13/11, sur le Mac)

Dump `~/labuse-backups/vps/labuse-labuse-20261113-133004.dump` (sha256 vérifié = serveur), restauré **sur le Mac**, jamais sur la base `labuse`. Prod touchée en **lecture seule** (comparaison de comptes). Mac : 47 Go libres au départ (plancher 10 Go). Base restaurée ≈ 30 Go.

## Étape 1 — Restauration
`createdb labuse_restore_manual` + `pg_restore --no-owner --no-acl`. **Durée 878 s (~14,6 min). rc=0. 0 erreur.**
- **Erreurs attendues** (tables dont la DATA est exclue du dump allégé) : **aucune** — pg_restore restaure le SCHÉMA de ces tables, il n'y a pas de COPY → pas d'erreur. L'exclusion de data ne produit pas d'erreur.
- **Erreurs anormales : aucune.** Restauration propre de bout en bout.

## Étape 2 — Comptes restauré vs prod (écart attendu 0)
| Table (scope) | Restauré | Prod | Écart |
|---|--:|--:|--:|
| parcels | 434 582 | 434 582 | **0** |
| data_sources | 130 | 130 | **0** |
| score_labuse (run servi q_v20) | 433 229 | 433 229 | **0** |
| parcel_residuel_runs (seq servie 17) | 433 229 | 433 229 | **0** |
| parcel_scenario_v2_runs (q_v20) | 866 458 | 866 458 | **0** |
| veilles | 9 | 9 | **0** |
| comptes | 28 | 28 | **0** |
| **parcel_constructibilite** | **11 404** | 11 404 | **0** (cache corrigé bien dans le dump) |

## Étape 3 — L'app démarre-t-elle ?
Backend `uvicorn labuse.api.app:app` sur **7450** pointé sur la base restaurée (jamais `labuse`) : **READYZ 200 en ~12 s**, « LA BUSE démarrée · schéma=ok ». Front `vite` sur **10250** (API 7450) : **l'UI charge** (carte de La Réunion, recherche, outils). Les 3 surfaces :
| Surface | Réponse | Ce qui manque à l'écran |
|---|---|---|
| **Fiche** `/parcels/{idu}` | **200**, 59,6 Ko, données complètes (surface, zone, SDP résiduelle, Signal) | rien de visible — rendue complète |
| **Analyse LABUSE** `/analyse/scenarios?commune=Saint-Denis` | **200**, n_selection 33 167, **run_calcule=True** | la part **cascade** (étage-0 / « hors projet » / foncier public) manque tant que la cascade est vide |
| **Dossier PDF** `/parcels/{idu}/export.pdf` | **200, application/pdf, 241 Ko, 9 pages rendues** (photo IGN, tuiles, sections sourcées) | rien de visible — rendu complet |
Captures : Dossier PDF (pages 1-2), front UI (accueil carte).

## Étape 4 — Tables vides restaurées : impact + remise en état
| Table vide (data exclue) | Casse à l'écran | Remise en état | Durée |
|---|---|---|---|
| **dryrun_cascade_results** (cascade par run) | l'**Analyse** (étage-0, « hors projet », foncier public) | **rechargée q_v19_sources depuis `~/labuse-backups/cascade/`** (COPY) | **253 s / 21 097 100 lignes** |
| cascade_results (cascade live, 9,2 M) | marginal (fiche/Dossier se rendent sans) | recompute job cascade, OU à la demande | heures |
| p_model_ext_dataset (1,57 Go) | stats accueil / recompute Signal LIVE (le Signal STOCKÉ `parcel_p_score_v2` marche) | rebuild socle (flux-run) | heures |
| score_snapshot_parcelles (476 Mo) | historique des prédictions | recompute | mineur |
| p_model_candidates / p_model_dataset | **rien (aucun lecteur, morts)** | — | — |

**Rechargement vérifié :** après COPY de `q_v19_sources` (21 097 100 = base exacte), l'**Analyse se complète** (`cascade_run=q_v19_sources`, `n_foncier_public=5050`). **La fiche était déjà complète** (le Dossier PDF 9 pages s'est rendu) — elle ne dépend pas de la cascade du run (taille inchangée après rechargement).

## Étape 5 — Verdict (3 lignes)
1. **OUI, on sait restaurer** : dump 13/11 → base propre (0 erreur, tous les comptes = prod à l'unité, cache 11 404), l'app boote (readyz 200 en 12 s), **fiche + Analyse + Dossier PDF répondent réellement**.
2. **Bout en bout ≈ 19 min** : restore 14,6 min (878 s) + rechargement de la cascade servie 4,2 min (253 s). (La reconstruction complète de `cascade_results`/`p_model_ext_dataset` par les jobs = heures, mais **inutile** pour fiche/Analyse/Dossier.)
3. **À ajouter à la sauvegarde pour que ce soit simple** : **expédier AVEC le dump la cascade du run servi** (`dryrun_cascade_results` du run servi, ~198 Mo compressée — comme ma copie `~/labuse-backups/cascade/`), sinon l'Analyse reste incomplète jusqu'au rechargement manuel. Accessoire : ne PAS sauvegarder `p_model_candidates`/`p_model_dataset` (morts) ; documenter que `cascade_results`/`p_model_ext_dataset` se reconstruisent par job.

## Étape 6 — Remise en état
Backend 7450 + front 10250 arrêtés (plus rien n'écoute), base `labuse_restore_manual` supprimée. **df Mac final : 42 Go libres.** Prod intacte (servi seq 17, readyz 200). Rien promu, rien supprimé en prod.

**— Ce rapport débloque l'étape 2 du ménage (après ta validation).**
