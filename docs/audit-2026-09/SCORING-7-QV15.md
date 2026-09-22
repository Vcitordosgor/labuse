# SCORING-7 — Run candidat q_v15 (Score LABUSE + Signal), sans bascule

**Date : 22/09/2026 · Branche `feat/scoring-6` (worktree `~/Desktop/labuse-scoring6`) · résiduel servi = run 5 · scoring servi = `q_v11_m137` (inchangé) · AUCUN merge, AUCUN promote, AUCUN sync VPS.**
Toutes les commandes via `PYTHONPATH=src …/python -c "from labuse.cli import app; app()"` (jamais `.venv/bin/labuse`).

## 0. Étape 0 — contrôles
| Contrôle | Résultat |
|---|---|
| pwd / branche | `~/Desktop/labuse-scoring6` · `feat/scoring-6` |
| arbre propre avant travail | oui (untracked = docs/reports) |
| résiduel servi (base) | **run 5** (`is_served`) |
| scoring servi | `q_v11_m137` (`config/served_run.txt`, inchangé) |

---

## 1. Config gravée (décisions de Vic) — commit `47c08915`

Bandes **absolues** (seuils inchangés), le **0 devient une bande à part**, NC n'est jamais 0 :

| bande | règle | mot client |
|---|---|---|
| A | 80-100 | **Excellente** |
| B | 50-79 | **Bonne** |
| C | 30-49 | **À étudier** |
| D | **1-29** | **Faible** |
| 0 | **score == 0 exact** | **Sans potentiel constructible** |
| NC | non calculable | **Analyse incomplète** (+ cause lisible) |

`config/score_labuse.yaml` (`bandes.zero` + `bandes.vocabulaire_client`), `bande_de_score` (0 → « 0 »),
`libelle_client_bande()`, `BANDE_RANG` (0 sous D, au-dessus de NC). Tests gravés : **un score 0 n'est
jamais en D · NC n'est jamais 0** (vérifiés aussi à l'échelle île : 0 violation sur 431 663).
`score_version : labuse_v1+1518ba79 → labuse_v1+cd2220e3`. Option `--parcelles-fichier` : commit `1172e43e`.

---

## 2. Signal q_v15 — fit au banc K0 (gelé, jamais basculé)

Recette `qv15` = **q_v14 MOINS `piscine` et `pv_candidat`** (aucune variable nouvelle) → **33 features**.
Banc K0 : train ≤ 2023 · isotonique par segment 2024 · **test aveugle 2025** (24 mois : train ≤2022,
cal 2023, test 2024). **Test de fuite : négatif.** Garde-fou ECE PM : ΔECE = −0,0003 < 0,01 → `ventes_pm`
RESTE. Artefacts **gelés** `reports/q-v15/` (sha256 12m `d8520aba…`, 24m `cbe1029e…`), lus par le pipeline.

### Métriques K0 2025 (hors copro) — servi q_v11 / q_v12 / q_v14 / q_v15
| candidat | préc@100 commune (méd.) | lift décile | AUC global | ECE global | churn top-1158 |
|---|---|---|---|---|---|
| q_v11 servi (ligne de base) | 0,06 | 2,06 | 0,613 | 0,00125 | 0,180 |
| q_v12 | 0,08 | 2,27 | 0,620 | 0,00216 | 0,484 |
| q_v14 | 0,08 | 2,27 | 0,626 | 0,00205 | 0,513 |
| **q_v15** | **0,09** | **2,26** | **0,623** | 0,00221 | 0,509 |

### Métriques SUPPLÉMENTAIRES du mandat (K0 2025, q_v15 vs q_v14 refit sur le même banc)
| métrique | q_v15 | q_v14 |
|---|---|---|
| Brier | **0,014816** | 0,014827 |
| préc@100 | 0,38 | 0,39 |
| préc@500 | 0,190 | 0,194 |
| préc@1000 | **0,138** | 0,134 |
| préc@2000 | **0,1085** | 0,1015 |
| mutations captées @2000 | **3,35 %** | 3,13 % |
| préc niveau **fort** (p≥0,20) | **0,381** (n=105) | 0,349 (n=129) |
| préc niveau **moyen** (0,10-0,20) | **0,141** (n=411) | 0,127 (n=544) |
| préc niveau **faible** | 0,0149 | 0,0149 |
| rappel niveau fort / moyen | 0,62 % / 0,89 % | 0,69 % / 1,06 % |

**Lecture** : q_v15 fait **jeu égal avec q_v14 en retirant 2 variables mortes** — marginalement MEILLEUR
en précision haute (préc@1000/2000, préc fort/moyen) et en Brier, marginalement en dessous en AUC global
(0,623 vs 0,626). Face au **servi q_v11**, q_v15 est au-dessus sur toutes les métriques standard de tête
(préc@100 médiane 0,09 vs 0,06 · lift 2,26 vs 2,06 · AUC 0,623 vs 0,613). Modèle plus simple, tête au moins
aussi précise. `signal_version = signal_v2+q_v15`.

---

## 3. Cascade v2 (lot C) — estimation puis réel

**Estimation AVANT calcul** : la cascade v2 (`cascade_v2.reclasser_batch`) **ne rejoue PAS la cascade** —
elle RECLASSE en lecture les verdicts de la cascade existante `q_v13_sources1` (17,6 M verdicts déjà en
base), au moment du scoring. Étage 0 réutilisé via `LABUSE_ETAGE0_RUN=q_v13_sources1` (Score) et le même run
(Signal). **Parcelles à recalculer séparément : 0. Temps estimé : ~0 (inline au §4).** ≪ 1 h → aucun STOP.

**Réel** : la reclassification a tourné inline pendant le §4. **139 087 parcelles exclues** par la cascade v2
(`cascade_exclue`), motifs conservés pour les filtres. Complétude vérifiée au timestamp (cf. §4).

---

## 4. Score + Signal île → `score_labuse` (run_label `q_v15`)

- **q_v15 p-run (Signal gelé)** sur l'île : 431 663 parcelles, **421 s** (~7 min), sha `d8520aba` (= artefact
  12m), tiers priorité 144 / à suivre 662 / sans signal 280 597 / écartée 150 260. Étage 0 = `q_v13_sources1`
  (cascade réutilisée, pas rejouée).
- **`score-labuse --run q_v15 --signal-run q_v15`** sur l'île : **431 663 lignes, ~5,5 min**.
  **Complétude au timestamp : 431 663 frais, 0 manquant** (contrôle identique au run 5). Versions
  `labuse_v1+cd2220e3` / `signal_v2+q_v15`. Aucun quota, aucun rang, aucun percentile.

Répartition des **bandes** île : **0** 271 502 (62,9 %) · D 74 291 (17,2 %) · C 39 222 (9,1 %) · B 26 837
(6,2 %) · NC 14 731 (3,4 %) · **A 5 080 (1,2 %)**. NC = zone non résolue 14 707 + règle PLU non validée 24.

---

## 5. Comparaison contre le servi (lecture seule) — `reports/scoring-7/`

### 5.1 Répartition (voir §4 pour les bandes) — niveaux de Signal île
fort 150 · moyen 703 · **faible 430 810**. (Signal absolu PALIERS-1 : fort ≥0,20, moyen 0,10-0,20.)

### 5.2 Ancien palier q_v11 × nouvelle bande q_v15 — où partent les « Priorité »
| ancien palier | A | B | C | D | 0 | NC | total |
|---|---|---|---|---|---|---|---|
| **Priorité** | 0 | 10 | 54 | 44 | 3 | 0 | **111** |
| À suivre | 65 | 268 | 367 | 571 | 95 | 1 | 1 367 |
| Sans signal | 4 265 | 24 972 | 37 335 | 70 215 | 144 080 | 3 436 | 284 303 |
| Écartée | 750 | 1 587 | 1 466 | 3 461 | 127 324 | 11 294 | 145 882 |

**Les 111 anciennes « Priorité » se répartissent C 54 · D 44 · B 10 · 0 3 — aucune en A.** C'est attendu :
l'ancien palier est un rang de **Signal** (probabilité de mutation), la nouvelle bande est un **Score** de
constructibilité — deux axes distincts. Un fort signal de vente n'implique pas une forte capacité. Le
croisement le dit sans les confondre (c'est au client de lire bande × signal, cf. §6).

### 5.3 20 montées / 20 descendues (delta du Signal p_raw → signal_p) — `montees_descentes.csv`
Têtes : montées jusqu'à **+0,60** (`97411000AL0497` 0,111→0,714, passe niveau fort) ; descentes jusqu'à
**−0,67** — surtout d'anciennes p=1,000 **surconfiantes** ramenées à 0,33-0,39 (`97408000AP1609/1610/1647`
La Possession), calibration isotonique par segment plus sobre. Cause par ligne dans le CSV.

### 5.4 30 témoins — bande, signal, contributions FR (`temoins_q_v15.json`)
Les 30 résolvent. « bonnes » → A (sauf AB0798 = B) ; « mauvaises » → 0/D ; « limites » variées.
Témoin-école résiduel **`97402000AB1117` → bande C** (81 m² de droits — le fix d'assiette du run 5 remonte
jusqu'au Score). Signal faible sur les 30 (choisis pour le Score, pas le Signal). Contributions en français
(« 4 932 m² de droits à construire restants », « bâti existant… démolition à prévoir »).

### 5.5 Temps total réel
Cache enrichi (une fois) 40 min · fit+gel 7 min · p-run Signal île 7 min · score-labuse île 5,5 min ·
comparaison 1 min. **≈ 60 min** (dont 40 min de construction du dataset, réutilisable).

---

## 6. Bloquants avant bascule
1. **La bande « 0 » pèse 62,9 % de l'île** (271 502 « Sans potentiel constructible »). C'est correct au sens
   du moteur (SDP résiduelle nulle), mais c'est une décision de présentation majeure : Vic doit valider que
   « 0 » se sert bien comme catégorie distincte (et non repliée sur D ou NC) côté client.
2. **Score et Signal sont orthogonaux** : les anciennes « Priorité » (fort signal) tombent en C/D. La bascule
   suppose que le client lise **bande × niveau de Signal** ensemble (l'UI est HORS mandat — mandat séparé).
   Sans cette lecture combinée, un pro pourrait lire « C/D » comme un déclassement des têtes de mutation.
3. **`score_version` change** (`cd2220e3`) : toute bascule re-sert une version de barème ; les runs antérieurs
   (dryrun_r3/r5) portent l'ancienne version — normal, mais à noter au journal de bascule.
4. **q_v15 ≈ q_v14** sur K0 (AUC très légèrement inférieure) : le gain est la SIMPLICITÉ (2 variables mortes
   retirées), pas la performance. Si Vic attend un saut de performance, q_v15 n'en est pas un.

## 7. Ce qui reste à Vic (décisions réservées)
- **Go/no-go bascule** du Signal q_v15 (`golden promote q_v15`) et/ou du barème gravé — après lecture.
- **Merge** de `feat/scoring-6`.
- **Déploiement / sync VPS.**
- **UI** « Analyser avec LABUSE » + badges bande/signal (mandat séparé) : c'est là que se règle le bloquant 2.
- **Recalibrage des seuils de bande** : hors mandat, non touché ici (seuils inchangés).

Rien n'est servi, promu, mergé ou synchronisé. Artefacts gelés + tables candidates (`score_labuse` q_v15,
`parcel_p_score_v2` q_v15) prêts à être lus ou purgés.
