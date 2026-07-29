# BARÈME `residuel_socle` — MESURE (lecture seule)

> **Statut : MESURE TERMINÉE — POINT D'ARRÊT. Rien appliqué.** Mesuré le 29/07/2026 sur la base
> à jour (9 399 déclassées identifiées, YAML courants).
>
> **CONCLUSION QUI CORRIGE MON ALERTE DE PHASE 1 : le barème n'a PAS besoin d'être re-dérivé.**
> Le « préalable barème » que j'avais gravé (§0bis du MANDAT_RERUN) était PRÉMATURÉ — j'ai conclu
> à une décalibration sur « 5,1 % de franchissements de palier » sans vérifier si les bornes
> étaient STATISTIQUES ou PHYSIQUES. Elles sont physiques. Principe #3, troisième instance
> (gate no-op, coût par taille, et maintenant le barème).

---

## 1. Les bornes sont des seuils PHYSIQUES, pas une dérivation statistique

Barème (`etage0_ext.py:31`) : SDP m² → bonus. Bornes **100 / 300 / 800 / 2 000 / 5 000**, labellisées
maison / petit collectif / opération viable / belle opération / opération majeure.

**Preuve qu'elles ne sont pas dérivées d'une distribution** :
- **≠ quantiles SP** : les percentiles réels de la SDP résiduelle SP (>0) sont 201 / 364 (p70) /
  993 (p90) / 1 857 (p95) / 4 249 (p98) — ils ne coïncident avec AUCUNE borne. Un barème
  quantile-dérivé aurait des bornes = ces percentiles.
- **≠ `opportunity_score`** : l'`opportunity_score` moyen par palier est PLAT-INVERSE
  (51,9 → 52,3 → 50,2 → 46,5 → 45,1 → **39,2**) — il DÉCROÎT quand le bonus CROÎT. Les bornes ne
  sont donc pas calées sur le verdict d'opportunité (le residuel_socle récompense la CAPACITÉ
  constructible, pas la probabilité de mutation — séparation d'architecture assumée, cohérente
  avec le WoE décroissant du modèle P).
- Nombres **ronds d'échelle d'opération** (100/300/800/2000/5000), pas des valeurs empiriques.

« Extraites des 32 448 verdicts SP » (commentaire) = **validées/labellisées** contre les verdicts
(confirmer qu'une parcelle ≥ 5 000 m² SDP est bien une « opération majeure »), PAS statistiquement
dérivées.

## 2. Saint-Paul n'est PAS un référentiel biaisant (question de méthode, Vic)

La distribution SDP de **l'île calibrée (21 communes hors dépubliées)** est quasi identique à celle
de SP :

| | p50 | p90 | p98 |
|---|---:|---:|---:|
| Saint-Paul | 201 | 993 | 4 249 |
| Île (21 communes) | 212 | 1 120 | 4 398 |

Une **dérivation multi-communes donnerait ~les mêmes bornes** que SP (distributions superposables) —
et de toute façon les bornes sont physiques, donc indépendantes de la commune de référence. Le
souci « barème d'une seule commune appliqué à l'île » ne se matérialise pas dans les chiffres.

## 3. Les déclassées n'affectent pas la dérivation (Vic)

Sur les **1 633 franchisseurs de palier SP** (servi → recalcul) : **0 déclassée, 1 633
constructibles** re-classés. Les inconstructibles (SDP → 0) tombent en « rien à construire » (−25),
ce qui est CORRECT, et ne polluent pas le re-bucketing des constructibles. Une dérivation statistique
devrait certes les exclure (leur SDP servie était fictive) — mais comme les bornes sont physiques,
la question est sans effet sur les bornes.

## 4. Le −13 % SP est un input plus JUSTE, pas une décalibration

Les 1 633 franchissements (tous vers le bas) sont le re-classement CORRECT de parcelles dont la SDP
calibrée (pleine terre 20 → 40 sur U3c/U6c) est plus faible et plus juste : 388 m² au lieu de 451
EST une opération plus petite, qui mérite un socle plus bas. Le barème (bornes physiques inchangées)
fait exactement son travail. **L'effet de ce re-classement sur les scores de cascade est réel et
appartient à l'étape (3) canal cascade du re-run** — il n'exige aucune re-dérivation du barème.

---

## Recommandation (Vic tranche)

**Retirer la re-dérivation du barème de la séquence de préalables.** Le barème est sain (bornes
physiques d'échelle d'opération). Ordre restant simplifié : **~~barème~~ → canal cascade → re-run
complet.** Ce que la calibration a changé (SDP plus juste) est déjà porté par la mesure du canal
cascade. Si un jour on veut FONDER les bornes statistiquement (autre décision produit), le faire
multi-communes et hors déclassées — mais rien ne l'impose aujourd'hui.

*Artefacts (lecture seule) : `repli_sp_residuel`, `parcel_residuel`, `backup_sp_evals_20260630`,
`parcel_constructibilite`. Aucune donnée modifiée ; `q_v7_defisc` intouché.*
