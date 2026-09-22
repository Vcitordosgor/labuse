# SCORING-6-DRYRUN-RUN5 — le moteur rejoué sur l'assiette RÉELLEMENT clippée

**Date : 22/09/2026 · Branche `feat/scoring-6` · résiduel servi = run 5 (bascule faite) · `q_v11_m137` reste le run servi du scoring.**
**Même protocole que SCORING-6-DRYRUN (`dryrun_r3.py`), script `reports/scoring-6/dryrun_run5/dryrun_r5.py`, CSV/JSON à côté. `score_version = labuse_v1+1518ba79` (identique).**

Ce que le dry-run précédent ne pouvait pas mesurer (run 3 = tout-ou-rien, l'assiette clippée n'avait
jamais été produite), celui-ci le mesure : **AVANT = run 3 (tout-ou-rien), APRÈS = run 5 (assiette
clippée réelle, fix bâti `13d8fefd` + delta 90 438 parcelles, complétude vérifiée).** L'écart isole
donc l'effet de **l'assiette**, pas du calibrage.

---

## 0. Contrôles

| Contrôle | Résultat |
|---|---|
| résiduel servi (base) | **run 5** (`is_served`) |
| run servi scoring | `q_v11_m137` (inchangé — run 5 ne touche que le résiduel) |
| AVANT = run 3 | `score_labuse` `dryrun_r3` (SP) / `dryrun_r3_temoins` / `dryrun_r3_an3112` (persistés run 3 servi) |
| APRÈS = run 5 | `dryrun_r5` (SP, CLI `score-labuse --communes 97415`) + `dryrun_r5_temoins` + `dryrun_r5_an3112` |
| cascade | `q_v13_sources1` · Signal stand-in `q_v14` (recette `q_v15`) |

---

## 1. Saint-Paul (51 129) — bandes AVANT (run 3) → APRÈS (run 5)

| bande | avant run 3 | après run 5 | delta |
|---|---|---|---|
| A | 617 | 615 | **−2** |
| B | 4 506 | 4 366 | **−140** |
| C | 6 551 | 6 404 | **−147** |
| D | 26 877 | 29 281 | **+2 404** |
| NC | 12 578 | 10 463 | **−2 115** |

**Lecture : l'assiette clippée fait sortir 2 115 parcelles de « NC »** (non calculable — tout-ou-rien
zone fermée) **vers un score**, presque toutes en D (petits résiduels sur une portion U/AU réduite).
En parallèle elle **rabote** ~290 parcelles B/C d'un cran (la greve certaine — PPR rouge/ravine/DPF/
50 pas/PEB — ampute l'assiette de parcelles U grevées). Effet net : NC −2 115, D +2 404.

### Transitions (hors diagonale, 2 992 parcelles bougent)

| avant→après | n | sens |
|---|---|---|
| NC→D | 1 866 | rescousse (petit résiduel) |
| C→D | 464 | rabot greve |
| B→C | 170 | rabot greve |
| NC→C | 123 | rescousse |
| B→D | 124 | rabot greve |
| NC→B | 110 | rescousse |
| D→C / D→B / D→A | 27 / 19 / 17 | rescousse forte |
| A→B / A→D / A→C | 22 / 13 / 6 | rabot greve |
| NC→A | 16 | rescousse forte |

Deux mécanismes, tous deux légitimes : **rescousse** (une portion U/AU existe → capacité > 0 là où
le tout-ou-rien mettait 0/NC) et **rabot** (contrainte certaine sur l'assiette → capacité réduite).

### Anomalies (46 — bascule A↔NC ou saut > 2 bandes)

| type | n | mécanisme (spot-checks) |
|---|---|---|
| D→A (>2) | 17 | ex. `AB0796` AU-dominante 99,9 % : tout-ou-rien 0 → sous-zone résolue, résiduel 45 794 m² → A |
| NC→A | 16 | ex. `AX0231` N-dominante, 37 % U : résiduel 1 731 m² → A |
| A→D (>2) | 13 | ex. `BI0043` 100 % U mais grevée → assiette `terrain_exigu` → 0 → D |

Les 46 sont les **extrêmes** du mécanisme d'assiette (grande portion U/AU récupérée, ou parcelle U
presque entièrement grevée), aucune n'est un artefact. À comparer aux 6 anomalies du dry-run run 3
(qui n'étaient que du calibrage PLU-6/7) : ici elles portent l'effet d'assiette, jamais mesuré avant.

---

## 2. Les 3 112 A/N 90-99 % — la question bloquante du dry-run précédent

| | run 3 (tout-ou-rien) | run 5 (assiette clippée) |
|---|---|---|
| **score > 0** | **0 / 3 112** | **542 / 3 112** |
| bandes | NC 287 · D 2 825 | A 14 · B 76 · C 114 · D 2 895 · NC 13 |

**C'est le résultat central** : le bloquant « 0/3112 » du dry-run run 3 est levé — **542 parcelles
A/N à cheval ont désormais un score > 0** (dont 14 en A, 76 en B, 114 en C), parce que leur portion
U/AU produit enfin une capacité. Les 2 895 restées en D ont une portion U/AU trop petite/bâtie ou une
greve certaine (résiduel faible mais non nul), les 13 NC sont hors PLU outillé.

---

## 3. 30 témoins (avant run 3 → après run 5) — 6 changent

| idu | cat | av | ap | pourquoi |
|---|---|---|---|---|
| `97402000AB1117` | limite | D 0 | **C 35** | témoin-école lot A : sous-zone Uc, résiduel 81 → score enfin > 0 |
| `97415000AC0070` | limite | NC | **B 68** | NC → calculable (portion U/AU) |
| `97415000AC0109` | limite | NC | **D 15** | NC → petit résiduel |
| `97406000AV0888` | limite | D 0 | D 14 | résiduel apparaît (reste D) |
| `97406000AM0664` | limite | C 36 | **D 10** | rabot greve (assiette réduite) |
| `97409000AY0786` | bonne | A 90 | A 80 | léger rabot (reste A) |

Aucun témoin « bon » ne tombe du côté « mauvais » ; **monotonicité VERTE** (bonne_min 64 ≥
mauvaise_max 45).

---

## 4. Bilan

- L'assiette clippée **fait ce qu'elle promet** : elle transforme le tout-ou-rien en capacité
  proportionnée sur la portion U/AU. Effet **bidirectionnel** — rescousse (NC/D → score, 3112 A/N :
  0 → 542) et rabot (greve certaine ampute les U grevées).
- **Saint-Paul** : NC −2 115, mouvement dominé par NC→D (petits résiduels) ; A/B/C quasi stables
  (−2/−140/−147). Aucun bouleversement des têtes de classement.
- **Monotonicité VERTE, 46 anomalies toutes explicables** (extrêmes du mécanisme, spot-checkées).
- Recalibrer les seuils de bande **maintenant** reste prématuré : le dry-run éclaire l'effet
  d'assiette, il ne fixe pas une nouvelle grille (décision Vic).

Run 5 est servi. Rien d'autre n'est basculé ni mergé.
