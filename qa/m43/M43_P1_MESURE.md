# M43 — PHASE 1 · MESURE À BLANC du pouvoir prédictif (le cœur)

**Harnais gelé RR M36** : `p_model_ext_dataset` (fold `annee=2025`, `label` = mutation ; base
1,72 % de mutation). **0 poids de modèle touché** — mesure informative pour le geste [S] de Vic.
Population : parcelles à propriétaire PM courant (millésime 2024). `scripts/m43_lift_signaux.py`.

## 1. Lift BRUT + résiduel à la tenure (`lifts_signaux_p1.csv`)

| Signal | n | mutés | taux | **RR brut [IC95]** | RR \| tenure (MH) [IC95] |
|---|---|---|---|---|---|
| **cessée** | 1 143 | 48 | 4,20 % | **2,49 [1,88 ; 3,30]** | 2,54 [1,92 ; 3,36] |
| **radiée** | 467 | 36 | 7,71 % | **4,57 [3,33 ; 6,29]** | 4,49 [3,27 ; 6,17] |
| **procédure coll. (pcl)** | 749 | 23 | 3,07 % | **1,82 [1,21 ; 2,73]** | 1,88 [1,25 ; 2,82] |

Les trois RR bruts excluent 1, et **survivent à l'ajustement tenure** (MH ≈ brut → le signal n'est
PAS qu'une répétition de la tenure). **À première vue, les trois seraient intégrables** — et
l'hypothèse backlog (+1/+2 RR) semblerait même dépassée.

## 2. ⚠ Le piège éprouvé : causalité inverse (constater avant présumer)

**Le RR brut mélange prédiction et CONSÉQUENCE.** Un signal de société n'est prédictif que s'il
**PRÉCÈDE** la mutation. Test temporel (date du signal vs date de mutation, parcelles mutées) :

| Signal | signal AVANT la mutation | signal APRÈS (rétro-causal) |
|---|---|---|
| cessée | **10 %** | 90 % |
| radiée | **23 %** | 77 % |
| pcl | **52 %** | 48 % |

**cessée et radiée sont majoritairement des artefacts « dissolution SUIT la vente »** : la SCI vend
son unique foncier, PUIS se ferme / se fait radier. Leur RR brut (2,5 / 4,6) est **essentiellement
rétro-causal**.

## 3. Le lift honnête : AS-OF (signal daté AVANT le fold → mutation dans le fold) — `lifts_asof_p1.csv`

| Signal | n (as-of) | mutés | taux | **RR AS-OF [IC95]** | verdict |
|---|---|---|---|---|---|
| cessée | 785 | 9 | 1,15 % | **0,67 [0,35 ; 1,28]** | **NON prédictif** (sous la base ; RR brut = rétro-causal) |
| radiée | 385 | 5 | 1,30 % | **0,76 [0,32 ; 1,81]** | **NON prédictif** (rétro-causal ; effectif faible) |
| **procédure coll. (pcl)** | 687 | 22 | 3,20 % | **1,86 [1,23 ; 2,82]** | **CONCLUANT** — lift réel |

**Une fois l'as-of imposé, cessée et radiée s'effondrent** (RR < 1) : leur pouvoir « prédictif »
était de la causalité inverse. **Seule la procédure collective résiste** : as-of RR ≈ 1,86, IC
excluant 1, causalement solide (une société en redressement/liquidation vend son foncier pour payer
ses créanciers, la procédure PRÉCÈDE la vente ~1 fois sur 2).

## 4. Recommandation d'intégration — signal par signal

| Signal | Prédictif (as-of) | **Recommandation** |
|---|---|---|
| **procédure collective** | oui, RR ≈ 1,86 [1,23;2,82], résiduel à la tenure | **INTÉGRABLE** au scoring (geste [S] Vic) — feature « SIREN en procédure collective as-of ». +0,86 RR réel, l'hypothèse backlog éprouvée et confirmée pour CE signal. |
| **cessée** | non (RR as-of 0,67) | **NE PAS intégrer** au scoring — rétro-causal. Reste un FAIT public (fiche Phase 2). |
| **radiée** | non (RR as-of 0,76, n faible) | **NE PAS intégrer** — rétro-causal + effectif faible. Fait public (fiche Phase 2). |

**Ma lecture** : le pari du backlog (propension à vendre côté sociétés) est **partiellement vrai** —
mais seul le signal **procédure collective** le porte réellement ; « cessée » et « radiée » sont des
**indicateurs RETARDÉS** (la fin de la société suit la vente), séduisants en RR brut, morts en as-of.
Intégrer cessée/radiée aurait injecté du **futur dans le passé** (fuite temporelle). Éprouvé, pas présumé.

## Limites honnêtes
- Effectifs modestes (pcl as-of : 22 mutations) → IC réel mais large ; à re-mesurer sur folds poolés
  au geste [S]. « Non concluant » dit tel quel pour cessée/radiée as-of.
- Un seul fold (2025, gelé M36) ; le geste d'intégration devra valider en walk-forward.
- 0 poids touché. La décision d'intégration (re-fit) est un geste [S] de Vic sur cette mesure.
