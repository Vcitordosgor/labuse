# M127 — L'EXAMEN : RAPPORT (STOP)

*Branche `exp/m127-reentrainement`. Protocole M36 exact (train ≤ N-2, binning sur train seul,
calibration isotonique N-1, test N). Métrique de promotion : **RR@1158 hors copro, fold 2025**.
Référence à battre : **6,73** (artefact m36-l2f-2026). Sorties chiffrées : `reports/m127/`.
Rien de servi n'a bougé.*

---

## PREMIÈRE LIGNE — LE VERDICT

**Aucune variante ne bat la référence sur la métrique de promotion.**
Le modèle complet D fait **5,36 (−20 %)** ; la meilleure variante (A, nettoyage seul) fait
**6,67 (−0,9 %, ICs largement chevauchants — statistiquement neutre)**.
**Recommandation : NE PAS PROMOUVOIR (M128 sans objet en l'état).** Détail et enseignements
ci-dessous — l'examen dit ce qu'il dit.

## 0. Prémisse corrigée avant l'examen

**Le clamp 2021 était DÉJÀ levé** : le dataset d'entraînement (`ext_sql.py`, M3.5/M3.6) est bâti
sur l'union prod+histo (`EXT_DVF_START = 2014-01-01`, tenure sans clamp) — vérifié : tenure 2026
connue 17,1 % = la mesure M124. **La référence 6,73 a été entraînée AVEC la profondeur.** La marche
« B = profondeur » de l'échelle est donc un no-op ; l'échelle réelle : **A → C → D**.

## 1. L'ÉCHELLE (walk-forward complet, RR@1158 hors copro)

| Fold | Réf. M36 | A · nettoyage | C · + zéros M125 | D · + candidates | GBM (annexe) |
|---|--:|--:|--:|--:|--:|
| 2020 | 9,41 | 9,74 | 9,47 | **11,36** | 9,74 |
| 2021 | 8,61 | 9,38 | 9,11 | 9,24 | 10,37 |
| 2022 | 8,63 | 8,36 | 8,54 | 9,04 | 10,07 |
| 2023 | 7,30 | 7,40 | 6,43 | 7,51 | 8,28 |
| 2024 | 7,08 | 6,84 | 6,49 | 7,31 | **10,76** |
| **2025 (promotion)** | **6,73** | **6,67** | **6,27** | **5,36** | 5,59 |

Ce que chaque marche apporte (fold 2025) :
- **A (7 mortes sorties)** : −0,06 vs réf — **le nettoyage est GRATUIT** (mêmes performances,
  22 features au lieu de 29). ECE 0,0011.
- **C (zéros M125)** : **−0,40 vs A**. Les vrais zéros remplacent le bin « manquant » — et le
  modèle actuel y perd : le « manquant » d'avant portait une information de composition (quel type
  de parcelle n'avait pas de ligne) que le zéro uniforme efface. La donnée est plus VRAIE, le
  modèle tel quel l'exploite moins bien. À re-tester avec la **cause en catégorie** (la nuance
  M125 existe en colonne) plutôt qu'un zéro muet.
- **D (candidates)** : **+fort sur le passé (2020 : 11,36), effondré sur 2025 (5,36)**. Voir §4 —
  l'ablation attribue la chute aux 4 signaux propriétaire.

## 2. LES SEGMENTS (D, fold 2025, hors copro)

| Segment | n | k proportionnel | RR@k |
|---|--:|--:|--:|
| Terrain nu | 136 537 | 369 | **7,79** |
| **Bâti** | 291 702 | 789 | **3,87** |
| PM connue | 33 432 | 90 | 7,17 |
| Non-PM | 394 807 | 1 068 | 4,51 |

Le RR ne s'effondre pas sur le bâti mais il est **moitié moindre** (3,87 vs 7,79). Le vivier cible
de la dalle (111 371) inclut 181 k bâties : **des features bâti dédiées seront nécessaires**
(anticipé dalle §5.5) — le modèle actuel juge surtout le nu.

## 3. LA PONDÉRATION DES ANNÉES RÉCENTES (justifiée par walk-forward)

| Variante | 2022 | 2023 | 2024 (validation) | 2025 (test) |
|---|--:|--:|--:|--:|
| D sans poids | 9,04 | 7,51 | 7,31 | 5,36 |
| D demi-vie 5 ans | 9,13 | 7,61 | **8,01** | 5,36 |
| D demi-vie 3 ans | 9,22 | 7,56 | 7,72 | 5,36 |

La demi-vie 5 ans gagne la validation (moyenne 8,25 vs 7,95) — **et ne change RIEN au fold de
test**. La pondération n'est pas le levier. *(Si retenue un jour : hl=5, choisie sur 2022-2024,
jamais sur le test.)*

## 4. LES ABLATIONS — QUI COULE LE FOLD 2025 ?

| Variante (fold 2025) | RR hors copro |
|---|--:|
| D complet | 5,36 |
| D **sans statiques** (succession, pm_nue, permis_etat, pc_jamais) | 4,62 |
| **D sans les 4 PROPRIÉTAIRE** (proc, succession, âge, pm_nue) | **6,61** |
| A (référence interne du nettoyage) | 6,67 |

Deux verdicts nets :
1. **L'hypothèse « fuite des statiques » est RÉFUTÉE au sens strict** : les retirer dégrade encore
   (4,62). Elles apportent du vrai signal.
2. **Les 4 signaux propriétaire sont LE facteur de la chute** : sans eux, 2025 remonte à 6,61
   (≈ A). Ils gagnent les folds anciens (+0,4 à +1,6) et perdent le récent (−1,25). Lecture :
   `age_dirigeant_bin` est devenue la **feature n°1 du modèle** (amplitude 2,51, devant permis_bin
   1,19) — or sa LISTE de dirigeants est l'instantané RNE 2026. Sur les folds anciens, cet
   instantané « connaît » huit ans d'évolutions postérieures aux labels ; sur 2025 il n'a plus
   d'avance. **C'est l'instabilité de l'instantané, pas un signal de vente** — exactement le
   piège que la dalle nommait (« bonus quand présents, JAMAIS la fondation »). Les 3 candidates
   datées non-propriétaire (contagion, vente TAB, permis enrichi) sont, elles, ~neutres (6,61 vs
   6,67).

## 5. LE CHALLENGER GBM (annexe — ne concourt pas)

2020-2024 : **9,74 · 10,37 · 10,07 · 8,28 · 10,76** — domine largement la logistique.
**2025 : 5,59** — la même chute que D. Le GBM n'apporte AUCUNE robustesse là où l'examen se joue,
et coûte l'explicabilité (plus de reason codes additifs). **Non recommandé.** *(Son écart massif
sur 2024 (10,76 vs 7,31) dit tout de même qu'il reste de la structure non capturée par le linéaire
— piste pour plus tard, pas pour cette promotion.)*

## 6. LA CALIBRATION

ECE excellent partout : logistique **0,0011-0,0033** selon fold/variante (identique à la
référence) ; GBM un cran moins bon (0,0023-0,0047). La saturation isotonique aux extrêmes
(connue, audit score) persiste par construction. La calibration n'est pas le sujet — le
classement l'est.

## 7. LES POIDS DU MODÈLE D (fold 2025 — `model-card-D-2025.csv`)

Top amplitudes (coef × étendue WoE) : **age_dirigeant_bin 2,51** · permis_bin 1,19 · zone_plu
0,91 · canopée 0,89 · tenure_bin 0,65 · **permis_etat 0,64** · rot_nu 0,56 · **contagion 0,53** ·
**proc_collective 0,46** · rot_bati 0,43 · piscine 0,40. Les nouvelles apprennent fort — c'est
précisément le problème (§4) : fort ≠ stable.

## 8. RECOMMANDATION (la décision est à Vic — M128)

1. **NE PAS PROMOUVOIR** : aucune variante ne bat 6,73 sur la métrique fixée. L'artefact
   m36-l2f-2026 reste le servi.
2. **Le nettoyage (A) est acquis sans coût** (6,67 ≈ 6,73, 22 features au lieu de 29) — il peut
   entrer au PROCHAIN réentraînement gagnant, il ne justifie pas une promotion seul.
3. **Les signaux propriétaire ne doivent PAS entrer en features d'entraînement tant qu'ils sont
   des instantanés** : il leur faut des sources HISTORISÉES (dates de prise de fonction RNE —
   la colonne existe (`date_prise_fonction`), les millésimes DGFiP successifs…) ou rester ce que
   la dalle prescrit : des BONUS post-scoring (cascade étage 2), jamais la fondation.
4. **Les zéros M125** : la donnée vraie reste (acquis) ; au prochain examen, entrer la **cause en
   catégorie** au lieu du zéro nu (−0,40 à récupérer).
5. **Le bâti** : RR 3,87 vs 7,79 sur le nu — le vivier cible (111 k, 181 k bâties à venir) exige
   des features bâti dédiées avant la refonte cascade M129.
6. GBM : non, pour cette promotion (§5).

---

*Interdits respectés : rien promu, run/écrans intouchés, comparaison sur LA métrique fixée,
pondération justifiée par validation, résultats décevants dits en première ligne. Sorties :
`reports/m127/` (echelle-walk-forward.csv, ponderation.csv, segments-2025.csv,
ablation-statiques.csv, gbm-challenger.csv, model-card-D-2025.csv, manifest-dataset-v2.json,
artifact-m127-D-fold2025.joblib — artefact d'EXAMEN, jamais servi).*
