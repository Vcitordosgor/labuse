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

---

## PHASE 1 — Purge (arbitrage Vic : GO 1, 2, 4 ; pre_* HELD ; m6_ gardés) — **FAITE**

Ordre strict respecté : (2a) RUN_PRECEDENT versionné + repointé sur q_v8_calibre_pre_m28, (2b) accueil
vérifié (bascules_tiers_hauts=306), (2c) **commité SEUL** (`29af7e78`), (2d) purge ensuite.

**Mesures pre_* (point 3) — NON purgés** : `lignee_tete.build_parcel_entree_tete` **lit la DONNÉE** de
pre_pond/pre_regle/pre_m28 (JOINs `parcel_p_score_v2`) pour bâtir `parcel_entree_tete` (servi, matérialisé
514 lignes). Par la règle Vic « s'il lit les lignes, le run n'est pas mort » → **gardés**. (pre_m39 hors
chaîne de lignée, seulement dans served_run_exceptions ; gardé avec le set pour cohérence.)

**Backups** : 91 tables `backup_*` (223 Mo) droppées ; **2 `*_avant_littoral` gardées** (état avant une
correction irréversible, règle Vic). **`m6_*` (694 Mo) gardés** (reproductibilité d'audit — inscrits au
BACKLOG avec leur date et ce qu'ils rejouent).

**Purge exécutée** (app arrêtée, 0 connexion, VACUUM FULL — petites tables d'abord puis grosses) :
| Table | Action | Lignes |
|---|---|---|
| dryrun_parcel_evaluations | DELETE q_v7_defisc + Vdefisc + Vcaduc | 1 294 989 |
| division_or_candidates / ia_cache / p_score_v2_runs | DELETE 5 runs morts | 27 / 6 / 4 |
| 91 × backup_* | DROP TABLE | — |
| dryrun_cascade_results | DELETE q_v7_defisc | 14 652 811 |
| parcel_p_score_v2 | DELETE q_v12_m28 + q_v13_m32_mesure + q_v7_defisc | 1 294 989 |

**Taille base : 27 Go → (vague 1) → 20 Go APRÈS** ; disque libre 21 Gi → 28 Gi. **~7 Go rendus au disque.**
Runs restants dans parcel_p_score_v2 : q_v8_calibre (servi) + pre_m28/m39/pond/regle (lignée) = 5.

**Vérification** (app redémarrée) : healthz/accueil 200 · fiche 200 (canari 97415000AC0253 + 97410000BV0120
+ 97417000AE0003, 3 communes) · exports premium/dossier/one-pager 200 · **golden 33 FAIL = baseline (diff 0)**
· `served_run.txt` inchangé (q_v8_calibre). *Réserve : le set exact « M55-O » n'a pas été localisé dans le
dépôt ; vérifié sur le canari + 3 parcelles M73 de 3 communes + l'invariant golden.*

### Défaut d'architecture #1 (imposé en Phase 2)
Les runs existaient « à moitié » : jeux différents selon les tables (8 dans parcel_p_score_v2, 2 dans
dryrun_cascade_results, 5 dans dryrun_parcel_evaluations). **Le cycle de vie d'un run doit être ATOMIQUE :
créé ensemble, purgé ensemble.**

---

## PHASE 2 — Règle de rétention (écrite ET appliquée)

**Règle** : garder le **SERVI** + le **PRÉCÉDENT** (les deux points de vérité versionnés,
`config/served_run.txt` + `config/run_precedent.txt`) + **tout run encore RÉFÉRENCÉ** (lignée
`lignee_tete`, `served_run_exceptions`, démo `q_v2_demo`). Purger le reste, **de façon ATOMIQUE** (un run
retiré de TOUTES les tables run-scoped ensemble). Déclenchée **À LA BASCULE**, jamais par un cron.

**Commande** `labuse purge-runs-morts` (`cli.py`) — dry-run par défaut, `--apply` (app arrêtée, VACUUM
FULL). Elle découvre les tables run-scoped (colonnes texte `run_id`/`run_label`), calcule l'ensemble « à
garder » depuis les points de vérité + les références RÉELLES en base (ne devine rien), purge le reste,
VACUUM. Runbook : `docs/BASCULE_RUN_RUNBOOK.md` ; règle inscrite `docs/BACKLOG.md`.

**Pourquoi « servi + précédent »** : le précédent mesure le diff d'une bascule (accueil) ; au-delà, un
dérivé matérialisé (ex. `parcel_entree_tete`) porte déjà l'histoire. **Un run référencé n'est jamais
purgé** (la commande le garantit par construction).

**Appliquée** : la règle a découvert **5 runs ORPHELINS** (le défaut #1) présents dans de petites tables
mais absents de parcel_p_score_v2 — `m36-l2f-2026-07-12/14`, `q_v2`, `q_v3_datagap`, `q_v6_m8` (vérifiés
non référencés en code vif ; docstring périmée « run servi q_v6_m8 » corrigée au passage). Purgés
atomiquement (entonnoir_motifs 634, ia_cache 13, p_score_v2_runs 3, score_snapshots 4) + VACUUM. Dry-run
de contrôle : **« Aucun run à purger »**. Golden inchangé, fiche/app 200.

### Garde-fous Phase 2
Règle testée (dry-run puis apply, VACUUM), golden 33=baseline (diff 0), app+fiche 200, garde-fou de branche
vérifié avant chaque commit. Base finale ~20 Go (−7 Go vs départ). **NE PAS MERGER.**
