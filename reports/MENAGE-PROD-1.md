# MENAGE-PROD-1 — inventaire + exécution (étapes 0→F)

Prod `ssh labuse-vps`. **Aucune promotion, aucun déploiement.** `labuse purge-runs-morts --apply` INTERDIT (il ne protège pas la cascade servie) — jamais lancé. `dryrun_cascade_results` n'est dans AUCUN dump. Suppressions **par égalité stricte uniquement**, sur la liste §A figée validée par Vic ; chaque geste autorisé explicitement. État : inventaire §0-1 + liste §A, puis exécution §B→§F **terminée** (df 7,6 → 25 Go, sauvegarde relancée verte).

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

---

## §A — LISTE FIGÉE (validée Vic 13/11), comptes exacts + requêtes

Suppressions par **égalité stricte** uniquement. Tout run non listé est conservé (q_v20/q_v19/q_v19_sources/seq17 servi ; q_v18/q_v18_sources/seq15 précédent ; q_v23/seq18 candidat ; q_v8_* calibrages ; tous les instantanés ; ligne cache ia `q_v20+e77eb6f564`).

**q_v10_m129** : présent UNIQUEMENT dans `score_snapshots` (1 ligne) → **on n'y touche pas**. **q_v14** : introuvable dans toute table run-scoped (score_labuse, dryrun_parcel_evaluations, dryrun_cascade_results, parcel_p_score_v2, score_snapshots, score_labuse_runs, p_score_v2_runs) → **on n'y touche pas**.

### Données à supprimer
| Ordre | Table | Runs (égalité stricte) | Lignes | Requête exacte |
|---|---|---|--:|---|
| 1 | **p_model_candidates** | (table morte) | 4 316 630 | `TRUNCATE p_model_candidates;` |
| 1 | **p_model_dataset** | (table morte) | 2 166 145 | `TRUNCATE p_model_dataset;` |
| 2 | **parcel_residuel_runs** | seq 1, 2, 13 | 3×431 663 = 1 294 989 | `DELETE FROM parcel_residuel_runs WHERE run_seq IN (1,2,13);` |
| 3 | **dryrun_parcel_evaluations** | q_v11_m137, q_v13_sources1, q_v21, q_v22, q_v24 | 431 663+431 663+433 229+433 229+81 476 = 1 811 260 | `DELETE FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v11_m137','q_v13_sources1','q_v21','q_v22','q_v24');` |
| 4 | **score_labuse** | q_v16 | 431 663 | `DELETE FROM score_labuse WHERE run_label='q_v16';` |
| 5 | **parcel_p_score_v2** | q_v11_m137, q_v16, q_v21, q_v22 | 431 663+431 663+431 663+433 229 = 1 728 218 | `DELETE FROM parcel_p_score_v2 WHERE run_id IN ('q_v11_m137','q_v16','q_v21','q_v22');` |
| 6 (ARRÊT avant, §D) | **dryrun_cascade_results** | q_v21, q_v22, q_v24 | 21 094 673+21 094 673+3 981 033 = 46 170 379 | `DELETE FROM dryrun_cascade_results WHERE run_label IN ('q_v21','q_v22','q_v24');` |

### En-têtes à retirer (pour qu'aucun candidat fantôme ne reste proposé)
- `residuel_runs` : seq 1, 2, 13 (is_served=f) → `DELETE FROM residuel_runs WHERE run_seq IN (1,2,13);`
- `score_labuse_runs` : q_v16 → `DELETE FROM score_labuse_runs WHERE run_label='q_v16';`
- `p_score_v2_runs` : q_v11_m137, q_v16, q_v21, q_v22 → `DELETE FROM p_score_v2_runs WHERE run_id IN ('q_v11_m137','q_v16','q_v21','q_v22');`

### Incident q_v21 à fermer
`ops_incidents` id 81 (`calcul-nuit:q_v21`, « contrôles en échec ») + id 112 (`escalade:ancien:calcul-nuit:q_v21`), tous deux `resolu_at` NULL → résolus (motif : q_v21 purgé, jamais promu).

### Contrôle des runs GARDÉS (invariant avant/après chaque table, doit rester constant)
`score_labuse` q_v20=433 229, q_v18=433 229, q_v23=433 229 · `parcel_residuel_runs` seq 17=433 229, seq 15=433 229, seq 18=433 229 · `parcel_p_score_v2` q_v18/q_v20/q_v23=433 229 · `dryrun_cascade_results` q_v18_sources=21 157 172, q_v19_sources=21 097 100, q_v23=21 094 673 · `dryrun_parcel_evaluations` q_v18_sources/q_v19_sources/q_v23=433 229.

### Place récupérée estimée
TRUNCATE : ~1,6 Go (instantané). parcel_residuel_runs ~0,23 Go · dryrun_parcel_evaluations ~0,31 Go · score_labuse ~1,9 Go · parcel_p_score_v2 ~3,0 Go (via VACUUM FULL). dryrun_cascade_results (§D) ~9,3 Go. **Total ~16,3 Go.**

---

## §B — EXÉCUTION (14/11, fenêtre autorisée explicitement par Vic) — place provisoire

**Un seul dump retiré : l'hebdo du 08/11**, et seulement après copie prouvée.
- Copié serveur → Mac `~/labuse-backups/vps-hebdo/hebdo-labuse-labuse-20261108-133003.dump` (6,56 Go, 2043 s).
- **sha256 identique** serveur = Mac : `8c90b5a9…672e8ca9` ✓.
- Supprimé du serveur (copie prouvée). Aucun autre dump touché. df serveur **7,6 → 14 Go**.

## §C — EXÉCUTION — tables de runs morts (chaque geste : transaction, contrôle des gardés avant COMMIT, VACUUM FULL, df, readyz 200)

| Ordre | Table | Supprimé (égalité stricte) | Contrôle gardés | VACUUM | df après |
|---|---|--:|---|---|--:|
| 1 | p_model_candidates + p_model_dataset | TRUNCATE 4 316 630 + 2 166 145 | (tables mortes, 0 lecteur) | — | 14 → 16 Go |
| 2 | parcel_residuel_runs seq 1,2,13 + en-têtes `residuel_runs` | 1 294 989 | seq 15/17/18 = 433 229 ✓ | FULL | 16 Go |
| 3 | dryrun_parcel_evaluations (q_v11_m137, q_v13_sources1, q_v21, q_v22, q_v24) | 1 811 260 | q_v18_sources/q_v19_sources/q_v23 = 433 229 ✓ | FULL | 16 Go |
| 4 | score_labuse q_v16 + en-tête `score_labuse_runs` | 431 663 | q_v18/q_v20/q_v23 = 433 229 ✓ | FULL (100 s) | 16 → 18 Go |
| 5 | parcel_p_score_v2 (q_v11_m137, q_v16, q_v21, q_v22) + en-têtes `p_score_v2_runs` | 1 728 218 | q_v18/q_v20/q_v23 = 433 229 ✓ | FULL (34 s) | 18 → 21 Go |

readyz 200 à chaque pas, aucun compte servi bougé. **Incident q_v21 fermé** : `ops_incidents` id 81 + 112, `resolu_at` posé 14/11, motif « q_v21 purgé, jamais promu ».

## §D — EXÉCUTION — `dryrun_cascade_results` (dernier geste, autorisé explicitement par Vic ; table dans AUCUNE sauvegarde)
- DELETE q_v21 + q_v22 + q_v24 = **46 170 379** lignes, en transaction. Contrôle avant COMMIT : q_v18_sources = 21 157 172, q_v19_sources = 21 097 100, q_v23 = 21 094 673 — **exacts** → COMMIT.
- VACUUM FULL sous **surveillance df** (plancher 6 Go, annulation auto + rollback si franchi) : réécriture en ~4,5 min, **creux de place libre 7,3 Go** (jamais sous le plancher), `aborted=0`. Table **22 → 12 Go**.
- Après : df **21 → 31 Go**, 3 comptes gardés intacts, readyz 200. (q_v19_sources servie et q_v23 candidate préservées.)

## §E — Sauvegarde relancée VERTE + df final
- `labuse jobs run backup-postgres` (invocation cron identique) : **rc=0 en 1166 s**. Nouveau dump `labuse-labuse-20261114-020727.dump` **6,56 Go** (plus petit que le 13/11 6,76 Go — les runs morts purgés n'y sont plus = cohérent). Rotation : **2 quotidiens gardés** (13/11 + 14/11), rien d'autre supprimé.
- Un `pg_dump rc=0` relit **toutes** les tables servies sans erreur → **preuve d'intégrité bout-en-bout** après le ménage.
- **df final : 25 Go libres** (75 % utilisé). Départ du ménage ≈ 7,6 Go → **+17,4 Go** récupérés sans agrandir le disque, conforme à l'estimation (~16,3 Go + l'hebdo 6,56 Go − le nouveau dump).

## §F — Recompte §K bis par famille de zone canonique = §K ter (déjà fait, `DEPLOY-GROUPE-3.md`)
La correction demandée (reconnaître U/AU par `subtype`/`typezone`, pas par le préfixe du `name`) **est le §K ter** de `reports/DEPLOY-GROUPE-3.md` (commit `0e1588a84`). Le ménage **n'a touché aucune de ses entrées** (score_labuse q_v20/q_v23 gardés à 433 229, géométries parcellaires et `spatial_layers` intactes) → ses chiffres tiennent à l'identique :

| Classe U/AU réel (par `subtype`) | q_v20 (servi) | q_v23 (candidat) |
|---|--:|--:|
| au-delà (à-cheval légitime) | 4 959 | 7 712 |
| infime | 196 | 2 217 |
| **nulle (0 U/AU réel, phantom)** | **0** | **4 487** (HC 4 380 · bande 0 107 · aucune A/B/C/D) |

- Run **servi (q_v20) propre** : 0 parcelle nulle. L'alarme « Excellente/Bonne servies à 0 m² » de §K bis était un **faux positif** (méthode par préfixe de nom) — **retirée**.
- Phantom **uniquement dans q_v23** (4 487, introduites par le ré-examen exigu), **toutes HC** → le Score les met hors champ.
- 10 parcelles vérifiées à la main (dont `97402000AB1039` = à-cheval légitime, et `97408000BI0351` = phantom HC).
- **Correctif moteur côté `main`** (hors ménage) : `_sous_zone_constructible` doit refuser la sous-zone quand l'intersection U/AU réelle (`subtype`) est nulle, en gardant le clip quand elle est réelle.

## Observation (sans action — hors liste validée)
`/etc/cron.d/` contient **21 fichiers `labuse.bak-deploy-*`** (copies de sauvegarde du cron faites à chaque déploiement). Leur nom contient des points → **cron les ignore** (règle de nommage `run-parts`), donc **aucun double-lancement** ; seul `/etc/cron.d/labuse` est actif. C'est du **clutter inerte**, pas un risque. À proposer à Vic pour un ménage ultérieur (hors périmètre ici).
