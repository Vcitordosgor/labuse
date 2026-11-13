# MENAGE-PROD-1 — inventaire (étapes 0 et 1), lecture seule

Prod `ssh labuse-vps`. **Aucune suppression, aucune promotion, aucun déploiement.** `labuse purge-runs-morts --apply` INTERDIT (il ne protège pas la cascade servie). `dryrun_cascade_results` n'est dans AUCUN dump. Arrêt après l'étape 1 pour validation.

## ÉTAPE 0 — Préalables ✓
- **calcul-nuit gelé** : ligne commentée dans `/etc/cron.d/labuse` (« gelé le 13/11 sur ordre de Vic »). Sauvegarde du cron sortie de `/etc/cron.d` → `/root/labuse-cron.bak-20261113-freeze`.
- **Aucun job lourd en cours** (flux-run/cascade/score/résiduel/scenario/VACUUM/pg_dump : néant). Le calcul q_v24 a été arrêté (SIGTERM).
- **Dumps présents** : `hebdo-…-20261108` 6,56 Go (08/11 13:48) · `…-20261112` 6,76 Go (12/11 13:49). = 2 nets. `df` : **7,3 Go libres**.

## ÉTAPE 1.1 — Pointeurs réellement servis (`served_manifest.json` + `residuel_runs`)
| Rôle | Servi (q_v20, promu 27/10) | Précédent (retour arrière) | Candidat |
|---|---|---|---|
| score (scoring_run) | **q_v20** | q_v18 | **q_v23** |
| cascade | **q_v19_sources** ⬅ à garder | **q_v18_sources** ⬅ à garder | q_v23 |
| division | **q_v19** | q_v18 | — |
| mvt | q_v20 | q_v18 | — |
| résiduel (seq) | **17** | 15 | 18 |

**Cascade du run servi = `q_v19_sources`. Cascade du précédent = `q_v18_sources`. Les deux sont À GARDER.**

## ÉTAPE 1.2 — Lignes et taille par run

Tailles totales : `dryrun_cascade_results` **22 Go** (109,5 M) · `score_labuse` 7,5 Go · `parcel_p_score_v2` 5,3 Go · `p_model_ext_dataset` 1,57 Go · `cascade_results` 1,42 Go (hors-run, non daté) · `parcel_scenario_v2_runs` 1,06 Go · `p_model_candidates` 862 Mo · `dryrun_parcel_evaluations` 537 Mo · `score_snapshot_parcelles` 476 Mo · `parcel_residuel_runs` 469 Mo.

| Table | Runs présents (lignes) |
|---|---|
| **dryrun_cascade_results** | q_v18_sources 21,16M · q_v19_sources 21,10M · **q_v21 21,09M · q_v22 21,09M · q_v24 3,98M** · q_v23 21,09M |
| **dryrun_parcel_evaluations** | q_v11_m137 · q_v13_sources1 · q_v18_sources · q_v19_sources · q_v21 · q_v22 · q_v23 · q_v24 (81k) |
| **score_labuse** | q_v16 · q_v18 · q_v20 · q_v23 (433k ch.) |
| **parcel_p_score_v2** (run_id) | q_v11_m137 · q_v16 · q_v18 · q_v20 · q_v21 · q_v22 · q_v23 |
| **parcel_scenario_v2_runs** | q_v20 · q_v23 (866k ch.) — aucun run mort |
| **parcel_residuel_runs** (seq) | 1 · 2 · 13 · 15 · 17 · 18 (431–433k ch.) |
| **score_snapshot_parcelles** | par snapshot_id (snapshots M5 d'août : q_v8_calibre, q_v10_m129, q_v11_m137…) |
| **cascade_results** | pas de colonne run (table courante, non historisée) → GARDER |

## ÉTAPE 1.3 — run × table : garder / supprimer + comparaison `purge-runs-morts`

**À GARDER d'office :** q_v20 (servi) · **q_v19_sources** (cascade servie) · **q_v19** (division/signal servis) · seq 17 · q_v18 + **q_v18_sources** + seq 15 (précédent) · **q_v23 + seq 18 + cascade q_v23 + scénarios q_v23** (candidat) · **q_v8_calibre / _pre_m28 / _pre_m39 / _pre_pond / _pre_regle** (calibrage).

**À SUPPRIMER (morts, non référencés) :** **q_v21, q_v22** (jamais promus, remplacés par q_v23) · **q_v24** (partiel, calcul tué) · **q_v16** (score ancien) · **q_v11_m137, q_v13_sources1, q_v10_m129, q_v14** (anciens modèles/dev) · **q_v20+e77eb6f564** (variante q_v20 taguée git, non servie) · **seq résiduel 1, 2, 13** · snapshots M5 d'août.

**Comparaison avec `labuse purge-runs-morts` (dry-run) — DIVERGENCES GRAVES :**
- purge GARDE : q_v18, q_v20, q_v8_calibre*. purge SUPPRIMERAIT (13) : q_v10_m129, q_v11_m137, q_v13_sources1, q_v14, q_v16, **q_v18_sources, q_v19, q_v19_sources, q_v23**, q_v20+e77eb6f564, q_v21, q_v22, q_v24.
- **⚠ purge supprimerait `q_v19_sources` = la CASCADE SERVIE → casserait q_v20.**
- **⚠ purge supprimerait `q_v18_sources` (cascade du précédent/retour arrière).**
- **⚠ purge supprimerait `q_v19` (division servie).**
- **⚠ purge supprimerait `q_v23` (le candidat).**
- → **Ne jamais lancer `--apply`.** Ma liste = celle de purge MOINS {q_v19_sources, q_v18_sources, q_v19, q_v23}. Le reste (vraiment morts) coïncide.

## ÉTAPE 1.4 — Hors base
- Filets : `/opt/labuse/app-avant-groupe3c` 4,9 Go · `venv-avant-groupe3c` 963 Mo (retour arrière du déploiement 2 ; à vérifier hardlinks avant de compter le gain réel).
- Journaux : `/var/log/labuse` 2,3 Mo · `/var/log` total 414 Mo.
- Dumps : `/var/backups/labuse` 13 Go (2 nets) — déplaçables temporairement (étape 2) pour dégager l'espace du VACUUM FULL.

## ÉTAPE 1.5 — Plan chiffré + Go réellement récupérables

Espace récupérable en base (suppression des runs morts + `VACUUM FULL`) :
| Table | Runs morts | ≈ récupérable |
|---|---|---|
| dryrun_cascade_results | q_v21 + q_v22 + q_v24 (46,2 M lignes) | **~9,3 Go** |
| parcel_p_score_v2 | q_v11_m137 + q_v16 + q_v21 + q_v22 | ~3,0 Go |
| score_labuse | q_v16 | ~1,9 Go |
| dryrun_parcel_evaluations | q_v11_m137 + q_v13_sources1 + q_v21 + q_v22 + q_v24 | ~0,3 Go |
| parcel_residuel_runs | seq 1 + 2 + 13 | ~0,23 Go |
| score_snapshot_parcelles | snapshots M5 morts | partie de 476 Mo |
| **Total base** | | **~14,7 Go** |

**Contrainte dure : `VACUUM FULL` réécrit la table entière → il lui faut ~la taille de la nouvelle table en espace libre PENDANT la réécriture.** Pour `dryrun_cascade_results` (22 Go → ~13 Go après purge) il faut ~13 Go libres : **impossible aujourd'hui (7,3 Go)**. D'où l'ordre :

1. **Dégager l'espace provisoire** (étape 2, après ton accord + preuve de copie) : sortir les 13 Go de dumps du serveur → ~20 Go libres.
2. **Tables les plus petites d'abord** (DELETE en transaction + contrôle des comptes + VACUUM FULL) : parcel_residuel_runs, dryrun_parcel_evaluations, score_snapshot_parcelles, puis score_labuse, parcel_p_score_v2.
3. **dryrun_cascade_results en DERNIER** (le plus gros, non sauvegardé → double contrôle, DELETE par run explicite, VACUUM FULL).
4. Après chaque table : `df`, comptes des runs gardés inchangés, une fiche servie répond. Arrêt si < 5 Go ou si un compte bouge.

**Honnêtement récupérable : ~14,7 Go en base** (une fois l'espace du VACUUM FULL dégagé) **+ 13 Go de dumps** (temporaire, reviennent en 2 nets) **+ jusqu'à ~5,9 Go de filets** (si non-hardlinkés — à vérifier). Verrou : `VACUUM FULL` prend un `ACCESS EXCLUSIVE` sur la table (la fiche qui la lit attend) → à faire hors heures de pointe, dryrun_cascade_results le plus lourd.

**— ARRÊT. En attente de ta validation de la liste avant toute étape 2/3.**
