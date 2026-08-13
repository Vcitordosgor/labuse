# RAPPORT M80 — Purge des runs morts et règle de rétention
## PHASE 0 — Inventaire (lecture seule) — **STOP, arbitrage attendu**

Branche `feat/m80-purge`. Base **27 Go**, disque à 98 %. Aucune écriture, aucune purge. Run servi
confirmé = **`q_v8_calibre`** (`config/served_run.txt`).

---

## 1. Tables run-scoped (colonne `run_id`/`run_label`) + volume

| Table | Taille | Runs présents | Servi seul ? |
|---|---|---|---|
| **dryrun_cascade_results** | **6,7 Go** | q_v7_defisc, **q_v8_calibre** | 1 mort (3,38 Go) |
| **parcel_p_score_v2** | **5,5 Go** | **q_v8_calibre** + 7 morts (q_v12_m28, q_v13_m32_mesure, q_v7_defisc, q_v8_calibre_pre_m28/m39/pond/regle) | ~693 Mo/run × 7 = ~4,85 Go morts |
| dryrun_parcel_evaluations | 397 Mo | **q_v8_calibre**, q_v7_defisc, q_v6_m8_Vdefisc, q_v7_defisc_Vcaduc, q_v2_demo(8) | ~130 Mo/run × 3 morts |
| served_run_exceptions | 32 Ko | q_v8_calibre(9) + pre_m39(5)/pre_regle(17)/pre_pond(2)/pre_m28(1) | stale des pre_* à purger AVEC leur run |
| score_snapshots, parcel_flags, parcel_renouvellement, score_e, division_or_candidates, entonnoir_motifs, p_score_v2_runs, agent_run_parcels, agent_events, ia_cache | < 50 Mo | à purger de façon cohérente avec les runs retenus | — |

**Défaut d'architecture #1** : les jeux de runs **diffèrent d'une table à l'autre** (8 dans
parcel_p_score_v2, 2 dans dryrun_cascade_results, 5 dans dryrun_parcel_evaluations). Des runs existent
« à moitié » — c'est la dette que le mandat vise : une table run-scoped doit entrer dans le geste de
bascule (créée/purgée avec le run) ou être déclarée cache. Ici le cycle de vie des runs n'est pas atomique.

## 2. Run servi + runs morts

Servi : **q_v8_calibre** (jamais purgé). Morts (candidats) : q_v12_m28, q_v13_m32_mesure, q_v7_defisc,
q_v8_calibre_pre_m28, q_v8_calibre_pre_m39, q_v8_calibre_pre_pond, q_v8_calibre_pre_regle,
q_v6_m8_Vdefisc, q_v7_defisc_Vcaduc. Plus **q_v2_demo** (run de démo, à conserver — voir §3).

## 3. Vérification des références — **un run référencé n'est pas mort** (le cœur du STOP)

| Run | Référencé où | Verdict |
|---|---|---|
| **q_v8_calibre** | served_run.txt, golden, partout | **SERVI — garder** |
| **q_v2_demo** | `api/events.py` (le GÉNÈRE, 8 parcelles), `cli.py`, front `Header.tsx` | **run de DÉMO VIVANT — garder** (régénéré, 8 lignes) |
| **q_v7_defisc** | **`api/accueil.py:25 RUN_PRECEDENT = "q_v7_defisc"` (VIF)** + commentaires lignée (score_v_constants, score_e, pc_caducs) + garde `bascule_gardes.py:191` | **RÉFÉRENCÉ VIVANT** — l'accueil s'en sert comme « run précédent ». Purge = **maj code d'abord** (dériver RUN_PRECEDENT, ou le repointer sur le vrai précédent q_v8_calibre_pre_m28) |
| **q_v8_calibre_pre_regle / pre_pond / pre_m28** | `scoring/lignee_tete.py:18-20` (chaîne de lignée des bascules) + served_run_exceptions | **RÉFÉRENCÉ** (lignée) — vérifier si lignee_tete LIT la donnée du run ou n'affiche que des tuples statiques (from,to,date,motif). Si statique → purge OK ; sinon maj |
| **q_v8_calibre_pre_m39** | served_run_exceptions(5) uniquement (stale) | purgeable (exceptions stales à purger avec) |
| **q_v12_m28, q_v13_m32_mesure** | seulement docs `qa/m*/` (historiques de mandat) | **PURGEABLES** (les docs sont des archives, pas des dépendances) |
| **q_v6_m8_Vdefisc, q_v7_defisc_Vcaduc** | nulle part (ni code ni config) | **PURGEABLES** |
| ~~q_v5_m6b~~ | golden_check.py:60 (commentaire « plus de repli sur run mort »), e2e_m_via.mjs (défaut stale) | déjà mort, **0 ligne en base** — rien à purger |

**Défaut d'architecture #2** : le « run précédent » est **codé en dur** (`accueil.py RUN_PRECEDENT = q_v7_defisc`)
au lieu d'être dérivé (le précédent réel de q_v8_calibre est q_v8_calibre_pre_m28). Un run est référencé
par une constante de code éparse, hors du mécanisme served_run.txt. **À corriger dans la même passe** que la purge.

## 4. Tables de sauvegarde / cache

- **97 tables `backup_*` / `m6_*` = 938 Mo** : sauvegardes ponctuelles datées juin-juillet 2026 (per-commune
  PPR/zonage/PM/permits avant ingestion + m6_a02_backup_plu_dup 252 Mo + m6_snapshot_mvt_post2a/b 442 Mo).
  **Reliquats** — proposition : purge (les ingestions sont validées depuis, la donnée live fait foi). À arbitrer.
- **cascade_results (1,8 Go, 9,2 M lignes)** : **PAS un run mort, PAS purgeable** — c'est la cascade LIVE
  (non-dryrun), encore lue par ~10 générateurs (copilote, modules, events, anti_fiche, renouvellement,
  moteurs, app). M73 n'avait déclaré mort que le rail **documents** ; les autres surfaces la consomment.
- **p_model_ext_dataset 1,5 Go + p_model_dataset 769 Mo** : scopés par **`annee`** (cache de features du
  modèle P, régénérable) — pas run-scoped ; hors périmètre purge-runs (cache déclaré, doctrine respectée).
- **score_snapshot_parcelles 461 Mo** : scopé par `snapshot_id` — snapshots, à trier séparément.
- **spatial_layers_sub 1,2 Go** : dérivé spatial (sous-découpage), pas run-scoped.

## 5. Espace récupérable (après VACUUM FULL — un DELETE seul ne rend rien au disque)

| Catégorie | Récupérable | Condition |
|---|---|---|
| q_v12_m28 + q_v13_m32_mesure (parcel_p_score_v2) | ~1,4 Go | **LIBRE** (non référencés) |
| q_v6_m8_Vdefisc + q_v7_defisc_Vcaduc (evaluations) | ~0,26 Go | **LIBRE** |
| q_v7_defisc (dryrun_cascade 3,38 Go + score_v2 0,69 + evals 0,13) | ~4,2 Go | après maj `accueil.RUN_PRECEDENT` |
| pre_m28/m39/pond/regle (parcel_p_score_v2, 4 × 693 Mo) | ~2,8 Go | après vérif lignee_tete |
| backups `backup_*`/`m6_*` | ~0,94 Go | si arbitrés reliquats |
| **TOTAL potentiel** | **~9,5 Go / 27 Go** | débloque largement le rejeu M79 |

## ARBITRAGE demandé (Vic tranche quels runs partent)

1. **Purge libre immédiate** (non référencés) : q_v12_m28, q_v13_m32_mesure, q_v6_m8_Vdefisc,
   q_v7_defisc_Vcaduc → ~1,7 Go. GO ?
2. **Purge après maj code** : q_v7_defisc (repointer `accueil.RUN_PRECEDENT` sur q_v8_calibre_pre_m28,
   le vrai précédent) → ~4,2 Go. GO sur la maj + purge ?
3. **pre_m28/m39/pond/regle** : à purger si `lignee_tete` n'a pas besoin de leur DONNÉE (à vérifier en
   Phase 1). GO sous cette réserve ? (garder le seul q_v8_calibre_pre_m28 comme « précédent » si (2) le repointe dessus)
4. **Backups `backup_*`/`m6_*`** (938 Mo) : purge des reliquats ? GO ?
5. **q_v2_demo** : conservé (démo vivant). **cascade_results** : conservé (live). Confirmes-tu ?

**Rappel Phase 1** : purge cohérente sur TOUTES les tables run-scoped (jamais un run à moitié) → VACUUM
FULL (verrou exclusif, **app arrêtée**, je préviens avant) → mesure taille avant/après → vérif app +
fiche + exports 200 (4 parcelles M55-O + canari 97415000AC0253) + golden diff 0. Phase 2 : règle de
rétention (servi + précédent), purge auto au moment de la bascule, jamais un run référencé, doc
BACKLOG + BASCULE_LIVE_CHECKLIST.

### Garde-fous Phase 0
Lecture seule, 0 écriture, garde-fou de branche vérifié. **NE PAS PURGER — STOP. Vic arbitre les runs
(points 1-5) avant toute suppression.**
