# SCORING-6-DRYRUN — Rejeu du moteur sur le résiduel post-calibrage

**Date : 22/09/2026 · Branche `feat/scoring-6` (worktree `~/Desktop/labuse-scoring6`) · `git merge main` fait (`88a498e0`, sans conflit) · aucun run île, aucune bascule, aucun merge, aucune promotion.**
**Résiduel servi = run 3 (`--assiette-clippee`), vérifié en base. `q_v11_m137` reste servi (`config/served_run.txt` inchangé).**
**Preuves : `reports/scoring-6/dryrun_post_residuel/` (script `dryrun_r3.py`, CSV, JSON). `score_version = labuse_v1+1518ba79` (identique à SCORING-6).**

---

## ⛔ BLOQUANT EN TÊTE — le run 3 servi n'est PAS calculé sur assiette clippée

Le mandat pose comme acquis : *« residuel-serve 3 est servi (PLU-6/7 mergés dans main, assiette clippée). Le moteur doit être rejoué sur la bonne capacité. »* **La base dit le contraire : le run 3 ne porte pas l'assiette clippée.** Ce n'est pas un témoin qui bascule — c'est la capacité elle-même qui n'a pas été recalculée comme annoncé. À trancher avant toute lecture des tableaux ci-dessous.

Cinq preuves convergentes (aucune supposition) :

1. **Le code de l'assiette clippée (lot A, `9d6b1a0e`) n'existe que sur `feat/scoring-6`.** `git grep` de `assiette_clippee` / `_sous_zone_constructible` / `_greve_certaine` : **3 fichiers sur `feat/scoring-6`/HEAD, 0 sur `main`, 0 sur `69bd6906`**. `git merge-base --is-ancestor 9d6b1a0e main` → **NON, pas dans main**.
2. **Le run 3 a été calculé par le code de main.** `residuel_runs` : run 3, `code_commit = 69bd6906` (= le merge de PLU-CALIBRAGE-6 dans main), durée 9 350 s, île entière, calculé le 21-22/09. Ce commit ne contient ni le flag `--assiette-clippee` (grep vide dans `cli.py@69bd6906`) ni la logique de sous-zone. Le **libellé** du run est `« --assiette-clippee »` — une intention, pas un fait : le flag n'existe pas dans le code qui a produit le run.
3. **Le témoin de preuve du lot A ne bascule pas.** SCORING-6 lot A a démontré que `97402000AB1117` (N-96 %) passe, sur assiette clippée, de tout-ou-rien à **sous-zone Uc, SDP 81 m² > 0**. En base : SDP **0**, cause `zone_non_constructible:N`, dans les runs **1, 2 ET 3**. Aucun effet d'assiette dans le run 3.
4. **Les 3 112 A/N 90-99 % sont tous à SDP 0 dans le run 3** (run 2 en avait 17 positifs → run 3 : **0**). Leur cause est `zone_non_constructible:A/N` = la signature exacte du tout-ou-rien, pas d'une portion U/AU clippée.
5. **Conséquence directe** : les attendus §2.2 (« la part résiduel absent / pré-calibrage disparaît ») et §2.3 (« combien des 3 112 ont un score > 0 ») ne peuvent pas être satisfaits par ce run, non par défaut du moteur mais parce que **la capacité clippée n'a jamais été produite**. Le run 3 est un résiduel **tout-ou-rien recalculé sur main calibré PLU-6/7** — utile pour mesurer l'effet du calibrage, muet sur l'effet de l'assiette.

**Ce que le dry-run mesure donc réellement** : le moteur SCORING-6 rejoué sur *run 3 = résiduel tout-ou-rien + calibrage PLU-6/7*, comparé à *run 2 = résiduel tout-ou-rien pré-PLU-6/7*. C'est l'effet **du seul calibrage PLU-6/7** sur les scores, pas l'effet de l'assiette clippée. Les tableaux ci-dessous sont exacts et exploitables sous cette lecture. **Recommandation : avant de rejouer un dry-run « post-résiduel » au sens du mandat, produire un run résiduel île entière avec un code contenant le lot A (`compute-residuel --assiette-clippee`), c.-à-d. porter/merger le lot A dans le tronc qui sert les runs, puis le servir. Décision Vic.**

---

## 0. Étape 0 — vérifications

| Contrôle | Résultat |
|---|---|
| `pwd` | `/Users/openclaw/Desktop/labuse-scoring6` |
| branche | `feat/scoring-6` |
| arbre propre avant travail | oui (seul `reports/scoring-6/` ajouté ensuite) |
| `git merge main` | **`88a498e0`, sans conflit** (PLU-6/7 `69bd6906`/`003e75f2`/`d3036756` + DASHBOARD-4 entrent) |
| résiduel servi (base, pas supposé) | `SELECT run_seq FROM residuel_runs WHERE is_served` → **3** (`--assiette-clippee`, n=431 663) |
| run servi scoring | `config/served_run.txt` → **`q_v11_m137`** (inchangé) |

Protocole = SCORING-6 §3 : Score + Signal (stand-in `q_v14`, recette `q_v15`) sur les 30 témoins + Saint-Paul entière, `cascade_label=q_v13_sources1`.
Commande mandat exécutée : `labuse score-labuse --run dryrun_r3 --communes 97415 --signal-run q_v14 --signal-recette q_v15` (Saint-Paul persistée sous `dryrun_r3`).

**Avant / après** — définition rigoureuse, sans bascule du pointeur servi (donc sans perturber les worktrees voisins sur la base partagée) :
- **avant** = `score_labuse` run_label `scoring6-dryrun` (le dry-run SCORING-6, **run 2**). Vérifié : sur les parcelles calculables, la SDP persistée = run 2 à **38 562/38 562**, run 3 à 36 642 seulement → l'avant est bien le run 2.
- **après** = `dryrun_r3` (Saint-Paul), `dryrun_r3_temoins` (30 témoins), `dryrun_r3_an3112` (les 3 112), tous calculés sur le run 3 servi.

---

## 1. Dry-run — exécuté

- **30 témoins** : `dryrun_r3_temoins` (persisté), comparés à `TEMOINS.csv` (= avant, run 2, reproduit 30/30 par SCORING-6).
- **Saint-Paul entière** : 51 129 parcelles, `dryrun_r3` (persisté). **33 s → 0,65 ms/parcelle** (SCORING-6 : 0,86 ms).
- **3 112 A/N 90-99 % (île)** : reconstruites depuis `dryrun_cascade_results` (couche `zonage_plu_gpu`, HARD_EXCLUDE, « Zone A/N PLU … recouvrement 90-99 % » inclus) → exactement **3 112** (2 310 à 90-98 % = classe B « rescuable », 802 à 99 % = classe A). Scorées sous `dryrun_r3_an3112`.

---

## 2. Tableaux avant / après

### 2.1 — 30 témoins (avant = TEMOINS.csv/run 2 → après = run 3)

**3/30 changent**, tous par recalibrage PLU-6/7 (jamais par l'assiette). Aucun témoin ne bascule d'un côté « évident » à l'autre.

| idu | cat | av. score/bande | ap. score/bande | pourquoi (une ligne) |
|---|---|---|---|---|
| 97411000CP0427 | mauvaise | 21 · D | **45 · C** | SDP résiduelle 82 → 413 m² (zone recalibrée PLU-6/7, capacité désormais estimée) — remonte dans C |
| 97413000CR0421 | mauvaise | 18 · D | 8 · D | SDP 102 → 68 m² — baisse, reste D |
| 97406000AV0888 | limite | 30 · C | **0 · D** | zone AU rebasculée `zone_non_constructible:AUs1` (SDP 526 → 0) — tombe en D |
| *(27 autres)* | — | — | *identiques* | résiduel/zone inchangés par PLU-6/7 |

Détail complet : `reports/scoring-6/dryrun_post_residuel/temoins_avant_apres.json`. Le témoin école `97411000AB0798` (lame R+2) reste **64 · B** ; les A/N 96 % `97402000AL0088`/`97402000AB1117` restent **0 · D** (preuve du bloquant : l'assiette clippée les aurait remontés, elle n'agit pas).

### 2.2 — NC Saint-Paul par cause (avant vs après)

| cause NC | avant (run 2) | après (run 3) |
|---|---:|---:|
| zone non résolue | 12 567 | 12 578 |
| donnée critique absente | 0 | 0 |
| géométrie | 0 | 0 |
| règle PLU non validée | 0 | 0 |
| **total NC** | **12 567** | **12 578 (+11)** |

**Lecture.** Le résiduel est **présent pour 100 % des parcelles** dans les deux runs (n=431 663 chacun) : il n'y a **aucune** NC « résiduel absent ». La part « pré-calibrage » attendue disparaissant n'existait pas comme bucket NC séparé à Saint-Paul — le NC y est **entièrement « zone non résolue »**, une cause réelle (Saint-Paul est la commune `strict` gold ; ses zones A/N non calibrées ne se résolvent pas). Le run 3 ne réduit pas ce NC : **+11 net**, pur brassage d'étiquettes A↔N sous PLU-6/7 (au niveau résiduel : `zone_non_resolue:A` 8 115→8 257, `:N` 2 421→2 278…). Le NC restant est donc bien « zone non résolue », cause réelle — mais ce n'est **pas** l'assiette clippée qui l'a assaini, car il n'y avait rien à assainir de ce côté.

### 2.3 — Les 3 112 A/N à 90-99 % (île)

| | après run 3 |
|---|---:|
| **score > 0** | **0 / 3 112** |
| bande D (score 0, vrai zéro) | 2 825 |
| bande NC (zone non résolue) | 287 |
| bande A/B/C | 0 |

Rappel run 2 : 17 avaient une SDP > 0 ; run 3 : **0** (le run 3 est légèrement *pire* sur ce sous-ensemble). **Aucune des 3 112 n'est remontée** — conséquence directe du bloquant : sans assiette clippée, le reclassement B de la cascade v2 reste sans effet (exactement ce que SCORING-5-RETOUR §3 avait prédit : *« le reclassement B ne produit rien tant que le résiduel n'est pas recalculé sur assiette clippée »*). `an_3112_apres.json`.

### 2.4 — Bandes Saint-Paul (avant vs après) + déciles

| bande | avant (run 2) | % | après (run 3) | % | Δ |
|---|---:|---:|---:|---:|---:|
| A (≥80) | 622 | 1,2 % | 617 | 1,2 % | −5 |
| B (50-79) | 4 541 | 8,9 % | 4 506 | 8,8 % | −35 |
| C (30-49) | 6 613 | 12,9 % | 6 551 | 12,8 % | −62 |
| D (<30) | 26 786 | 52,4 % | 26 877 | 52,6 % | +91 |
| NC | 12 567 | 24,6 % | 12 578 | 24,6 % | +11 |
| **total** | **51 129** | | **51 129** | | |

**Déciles des scores calculables (Saint-Paul)** — quasi identiques, léger glissement vers le bas :

| | n | moy | p40 | p50 | p60 | p70 | p80 | p90 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| avant (run 2) | 38 562 | 20,2 | 6 | 10 | 23 | 30 | 41 | 55 | 64 | 81 | 100 |
| après (run 3) | 38 551 | 19,8 | 0 | 10 | 23 | 30 | 41 | 55 | 64 | 81 | 100 |

Scores > 0 : 23 323 → 22 818 (**−505**). Le run 3 déplace Saint-Paul très légèrement vers le bas (le calibrage PLU-6/7 clippe/recadre des zones résolues, sans l'effet compensateur de l'assiette). Distribution complète : `hist_scores_saint_paul_apres.csv`, matrice de transition : `transitions_saint_paul.csv`.

### 2.5 — Monotonicité

**VERT.** Sur les scores après run 3 : `bonne_min = 64` (lame R+2) ≥ `mauvaise_max = 45`. Aucune « bonne » ne passe sous une « mauvaise ». *Watch* : la marge se resserre (avant, `mauvaise_max` ≈ 21 ; le témoin `97411000CP0427` monte à 45 sous PLU-6/7) — à re-vérifier au prochain calibrage. Tests moteur `test_scoring6_score_labuse.py` + `test_scoring6_garanties.py` + `test_scoring6_assiette.py` : **23 passés** (monotonicité SDP, NC≠0, B n'exclut jamais, sous-zone du lot A).

### 2.6 — Temps

Saint-Paul : **33 s / 51 129 = 0,65 ms/parcelle** (le Score est déterministe, à la volée ; pas de cascade rejouée). Cohérent avec SCORING-6 (0,86 ms).

---

## 3. Proposition de bandes (décision Vic — ne PAS appliquer)

⚠️ **Recalibrer les seuils sur le run 3 serait prématuré et faux** : la distribution du run 3 fige les zéros du tout-ou-rien (les 3 112 A/N + toutes les A/N à 0) que l'assiette clippée est précisément censée relever en B/C. Bouger les seuils maintenant, c'est caler la grille sur la **mauvaise** capacité. La grille doit être arrêtée **après** un vrai run assiette clippée. Ci-dessous, pour information, la lecture de la distribution actuelle.

Référence île (SCORING-5-RETOUR, univers 281 403 non-écartées ; le run 3 n'en change quasi pas la forme — cf. déciles §2.4 identiques) et effectif sous les seuils **actuels 80/50/30** :

| bande | seuil actuel | effectif île estimé | % |
|---|---|---:|---:|
| A | ≥ 80 | ~4 114 | 1,5 % |
| B | 50-79 | ~25 199 | 9,0 % |
| C | 30-49 | ~36 354 | 12,9 % |
| D | < 30 | ~211 922 | 75,3 % |
| NC | — | ~3 814 | 1,4 % |

La distribution est très « tassée en bas » (médiane ≈ 10, p90 ≈ 55, p99 ≈ 81). Deux pistes possibles *quand la capacité sera juste* :
- **Garder 80/50/30** : A reste un vrai « top » (~1,5 %). Simple, lisible. Rien ne change.
- **Percentiles plutôt que valeurs absolues** (ex. A = p98 ≈ 80, B = p90 ≈ 55, C = p75 ≈ 35) : rend la grille auto-adaptative au prochain run et évite qu'une simple ré-échelle du barème ne vide une bande. À évaluer sur la distribution assiette-clippée, pas celle-ci.

**Ce qui changerait vs 80/50/30** : sur le run 3 tel quel, **rien de significatif** (les seuils tombent au même endroit, ±quelques dizaines de parcelles à Saint-Paul). Le vrai gain attendu — faire remonter les 3 112 et leurs semblables de D vers B/C — **n'est pas mesurable ici** faute d'assiette clippée. Décision reportée.

---

## 4. Anomalies

**Bascule > 2 bandes entre calculables : 0** (aucun A↔D à Saint-Paul ; `anomalies.csv`). La matrice de transition (§2.4) est quasi diagonale — pas de réordonnancement grossier.

**Basculements calculable ↔ NC** (changement de *nature*, pas de rang) — tous dus au brassage de résolution de zone sous PLU-6/7 :

| idu | avant | après | cause |
|---|---|---|---|
| 97415000DK1000 | **A · 100** | NC | run 2 : SDP 83 609 m² résolu → run 3 : `zone_non_resolue:A` |
| 97415000CR1120 | A · 90 | NC | idem, SDP 2 385 → zone non résolue A |
| 97415000CW0387 | A · 85 | NC | idem, SDP 2 838 → zone non résolue N |
| 97415000CW0737 | NC | **A · 100** | miroir : zone non résolue → résolue |
| 97415000DE0725 | NC | A · 100 | idem |
| 97415000DK0986 | NC | A · 100 | idem |

À signaler : 3 parcelles qui scoraient A (dont une à 100, 83 609 m² de SDP) deviennent non calculables sous PLU-6/7 — churn de calibrage à surveiller, mais symétrique (3 dans l'autre sens) et sans effet sur la monotonicité.

**Témoin « évident » qui change de côté : AUCUN** (cf. §2.5 — monotonicité verte). Le seul mouvement notable est `97411000CP0427` (mauvaise) qui remonte D→C (45) : à surveiller, mais reste sous toutes les « bonnes ».

---

## 5. Hors mandat — respecté

Aucune modification du moteur, des seuils ou de la cascade · aucun run île · aucun fit q_v15 · aucun merge · aucune UI · aucune bascule du pointeur servi (résiduel run 3 et scoring `q_v11_m137` intacts, vérifiés en base après travail).

## Reproduire

```
cd ~/Desktop/labuse-scoring6 && export PYTHONPATH=src \
  LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse
# après (Saint-Paul) — commande du mandat :
python -c "from labuse.cli import app; app()" score-labuse --run dryrun_r3 --communes 97415 --signal-run q_v14 --signal-recette q_v15
# témoins + monotonicité + 3 112 :
python reports/scoring-6/dryrun_post_residuel/dryrun_r3.py
```
