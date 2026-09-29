# DONNEES-FIX-1 — Rapport d'état (revérification avant point 4)

- **Date** : 2026-09-29 · worktree `~/Desktop/labuse-donneesfix` · branche `fix/donnees-fix-1` à `cd1fd67e` (= `origin/main`).
- **DB** : `postgresql://openclaw@localhost:5432/labuse` (lecture seule). venv `~/Desktop/labuse/.venv`.

## Constat de départ : le mandat est déjà livré à 3/4

Les points **1, 2, 3** du mandat DONNEES-FIX-1 sont **déjà implémentés et mergés dans `origin/main`** :

| Point | Commit | Fichiers |
|---|---|---|
| 1 — hauteur LiDAR égout dans le résiduel | `a32e1a5c` (lot C) | `faisabilite/hauteur_lidar.py`, `residuel.py` (`_niveaux_existants`, colonne `hauteur_source`) |
| 2 — badge « Sources discordantes » égout↔égout | `9f637de9` (lot A) | `hauteur_lidar.py` `discordance_hauteur()` |
| 3 — filtre pseudo-SIREN fiche §Identité | `9cc58260` (lot B) | `proprietaire_historique.py` `changements_millesimes()` |
| livrables (rapport, golden-55, captures, run 11 test) | `6323f0ab`, mergé via `bcc32144` | `docs/audit-2026-09/donnees-fix-1/` |

Le point **4** (81 exceptions PLU `modifie_calcul=true` appliquées au moteur) **n'est PAS fait** : `zonage.py:279` dit explicitement « n'entre dans aucun calcul (PLU-EXCEPTIONS-1 Lot C) » ; `app.py:5737` ne les collecte que comme drapeaux « à vérifier ».

## Étape 0 — garde run servi

- **Run résiduel servi = run 10** (`residuel_runs.is_served=t`, label « q_v15 assiette gabarit », code `babcc084`). ✅
- **Manifeste** `config/served_manifest.json` : `residuel_run_seq: 10` → **miroir cohérent**, pas de divergence. ✅
- Runs 11 (« q_v15 lidar + ER/EBC », île, code `cc419770`) et 12 sont des runs de test **non servis**.

## Preuve chiffrée que les points 1–3 tiennent (live DB)

### Point 1 — hauteur LiDAR dans le résiduel (run 10 servi vs run 11 lidar)

`hauteur_source` : run 10 = NULL partout (calculé avant le fix) ; run 11 = lidar 232 589 · bdtopo 1 097 · sans 28 529 · NULL 169 448.

| IDU | run 10 restant | run 11 restant | source r11 | lecture |
|---|---:|---:|---|---|
| 97411000AB0012 (égout 12,8 → R+3) | 33 366 | **0** | lidar | existant révélé, résiduel fantôme retiré |
| 97411000DE0210 (égout 19,8) | 32 156 | **0** | lidar | idem |
| 97411000BN0537 (égout 10,4) | 30 741 | **0** | lidar | idem |
| 97411000BL0108 (égout 5,2) | 26 590 | **10 798** | lidar | baisse partielle |
| **97415000EO0796** (témoin, bâti bas 3,3 m) | 179 | **187** | lidar | R+1 bas, +8 = coef plancher 0,95 |
| **97408000AO1424** (témoin, zone A) | 0 | 0 | — | terrain_exigu, pas de résiduel |
| 97411000BZ1065 | 26 | 36 | lidar | égout 3,6 → R+0, +10 coef plancher |

→ Les chiffres du rapport livré sont reproduits **à l'identique** sur la base. ✅

### Point 2 — badge égout↔égout (règle live sur `batiment_hauteur_lidar`)

273 552 comparables. **Ancienne règle** (|faîtage − BD TOPO| > 3 m) : **53 326** badges (~19,5 %). **Nouvelle règle** (|égout − BD TOPO| > 15 m **ou** faîtage ≤ 0 / > 60 m) : **189** (58 faîtage aberrant + 132 discordance égout, 1 recouvrement).

| IDU | faîtage | égout | BD TOPO | badge ancien | badge nouveau |
|---|---:|---:|---:|:--:|:--:|
| 97411000BZ1065 | 10,3 | 3,6 | 4,2 | ✅ (à tort) | ❌ |
| **97415000EO0796** (témoin) | 3,3 | 2,2 | 6,0 | ❌ | ❌ |
| 97418000AZ0128 / 0417 (aberration) | 53 401 | 4,3 | 6,1 | ✅ | ✅ (faîtage aberrant) |

→ Le faux-badge de 16 % disparaît ; les vraies aberrations restent. ✅

### Point 3 — filtre pseudo-SIREN (règle unique, fiche + frise)

`changements_millesimes()` (fiche §Identité) et la frise `moteurs.py:446` lisent le **même** drapeau `non_identifiable`.

| Témoin | chaîne SIREN | n_changements_reels | n_transitions |
|---|---|---:|---:|
| 97411000CD1214 (SCI Laurent Grandpre) | NULL→U23719996→483339628 | **0** | 2 (non id.) |
| 97415000AB0001 (ONF) | U15960284→U15960284→662043116 | **0** | 1 (non id.) |
| 97402000AD0359 (vrai chgt Dépt→Commune) | 229740014→219740024 | **1** conservé | 1 |

→ Faux changements neutralisés, vrai changement conservé. ✅

## Verdict

**Les points 1, 2, 3 tiennent (preuve chiffrée live).** Aucune régression détectée. Je poursuis sur le **point 4** (exceptions PLU `modifie_calcul` au moteur), le seul reste du mandat.
