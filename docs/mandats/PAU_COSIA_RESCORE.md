# PAU-CoSIA — rejeu score-v2 : MESURE + STOP (la bascule est le geste de Vic)

Demande : rejouer score-v2 pour que la nouvelle PAU (2 656 parcelles, 1 146 au plancher)
prenne effet. Consigne : si le rejeu impose une bascule de run, STOP et rendre le plan.

## Q1 — Le rejeu impose-t-il un nouveau run ? OUI → bascule → STOP.

`run_score_v2` (`pipeline.py:240-243`) **REFUSE d'écraser un run_id existant** (« aucun
écrasement silencieux »). On ne peut donc PAS re-scorer `q_v10_m129` en place : tout rejeu
produit un **nouveau run_id**, et le servir = **basculer** `Q_A_RUN_LABEL` / `config/served_run.txt`.
La bascule est le geste de Vic → **je ne bascule pas**.

## Mesure isolée (2 challengers calculés MAINTENANT, non servis, puis supprimés)

Pour séparer l'effet PAU de la dérive de la base, j'ai calculé deux runs au même instant
(`rebuild=False` → mêmes features, seule `parcel_pau` diffère) :
- **A** = PAU NEW (2 656) · **B** = PAU baseline BD TOPO (2 373). Servi (`q_v10_m129`) intact.

| comparaison | Saint-Philippe | 23 autres communes | ce que ça isole |
|-------------|---------------:|-------------------:|-----------------|
| **A vs B** | **0** | **0** | **effet PUR de la PAU** |
| B vs q_v10_m129 | 0 | **220** | dérive pure de la base depuis le 19/08 |

n_entree : q_v10=3890 → A=B=**2358** (identique A/B : la PAU ne le déplace pas).

## Résultat décisif : la nouvelle PAU ne change AUCUN tier — même à Saint-Philippe.

Le plancher (`plancher_c`) rend 1 146 parcelles ÉLIGIBLES, mais l'éligibilité n'est pas la
contrainte qui mord. Pour entrer en tête (`chaude`), il faut **`rang <= n_entree` (2358)** ;
pour la `réserve`, il faut **`sdp_residuelle > 0`**. Or à Saint-Philippe (RNU, littoral,
faible pression) :
- le `rang` des parcelles est **très au-delà de 2358** (proba de mutation faible) → aucune
  n'entre en tête ;
- au RNU il n'y a **pas de SDP résiduelle** (pas de règlement) → aucune voie `réserve`.

Donc les 1 146 « au plancher » restent **`a_creuser` (Neutre)** — exactement là où elles
étaient. La PAU lève une **fausse barrière** (elles PEUVENT désormais entrer en tête si un jour
leur proba monte), mais **aujourd'hui l'effet servi est nul**.

## Les 220 changements ailleurs = DÉRIVE, pas la PAU.

`q_v10_m129` a été gelé le **19/08** ; la base de dev a bougé depuis (autres mandats). Un rejeu
AUJOURD'HUI recalcule les proba/rang sur l'état courant → 220 parcelles d'autres communes
changent de tier + n_entree tombe 3890→2358. **Rien à voir avec la PAU** : une bascule
maintenant embarquerait cette dérive non liée, non mesurée, non voulue.

## Recommandation : NE PAS basculer pour la PAU.

1. La PAU améliorée est un **gain de qualité de donnée réel** (enveloppe 2025 mieux estimée),
   déjà en base (`parcel_pau` 2 656) et étiquetée ESTIMÉ. Elle s'appliquera **automatiquement
   à la prochaine grande passe** de score-v2 que Vic fera (pour d'autres raisons), sans geste
   dédié — avec, à ce jour, **0 effet sur les tiers**.
2. Une bascule dédiée « pour rendre visibles les 1 146 » serait **sans bénéfice** (0 tier
   bouge) et **coûteuse** (embarque 220 dérives d'autres communes + re-ancrage golden).
3. Si un jour une parcelle de Saint-Philippe reçoit un vrai signal (mutation, proba qui monte),
   la PAU aura retiré la barrière d'éligibilité — c'est là que le travail paiera.

## Si Vic veut quand même basculer (runbook, son geste)
Un rejeu propre suppose une base **regelée** (pas la dérive du dev partagé) : re-scorer sur un
état maîtrisé (Mac / grande passe), nouveau run_id, valider le diff attendu (PAU ≈ 0 + dérive
explicitée une à une), puis basculer `served_run.txt` + re-ancrer golden. Tant que ce n'est pas
le cas, la mesure ci-dessus tient : **PAU = 0 tier, 220 = dérive**.

## Vérif (aucune bascule effectuée)
- Runs de mesure (challenger A + baseline B) **supprimés** ; `parcel_pau` restaurée à la PAU
  NEW (2 656) ; run servi **`q_v10_m129` intact** (jamais écrit).
- **golden 119/119**, **GARDE-RUN 431 663/431 663 (q_v10_m129)** — rien n'a bougé (served
  inchangé, pas de bascule).
- Aucune modif de code ce tour (état = commit Phase 2 `87e57b56`) → tsc 0 / build inchangés.
