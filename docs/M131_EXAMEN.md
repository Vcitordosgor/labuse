# M131 — L'EXAMEN SOUS LA MÉTRIQUE v2

> **Verdict mécanique : C_bati NON PROMU.** La double barre échoue sur le critère (b)
> — C_bati n'est supérieur hors bruit sur **aucun** segment. Le gain bâti pointe dans le
> bon sens (+0,41 de RR, ~+8 %, comme M127-bis/M130) mais son intervalle de confiance
> franchit 0 : à 959 têtes bâties (~15 mutations attendues), le signal ne perce pas le
> bruit. **Statu quo : on ne touche pas au run servi.**

Ce rapport ne contient **aucune note globale** (interdit du mandat) : la métrique v2 note
par segment, et c'est tout. Protocole identique à M130 (walk-forward, train ≤2023 binning-
train-seul, iso 2024, test 2025 ; population = vivier servi q_v10_m129, 285 781). SEULE la
notation change : top 0,4 % de CHAQUE segment sur son propre classement, écart mesuré par
**bootstrap PAIRÉ** (mêmes lignes rééchantillonnées pour les deux modèles → test de « hors
bruit » plus puissant que des IC marginaux). Mesure seule. Sorties :
`reports/m131/{segments_v2,ece_v2,verdict_v2}.csv`.

---

## 1. Le tableau — 2 modèles × (RR nu, RR bâti, ECE), par segment

Population : hors copro ∩ vivier servi. Top 0,4 % du segment (nu : k=171 sur 42 838 ;
bâti : k=959 sur 239 795). RR médian sur 20 tirages d'ex æquo ; IC95 bootstrap 1000.

| Segment | n | base | **actuel** (servi) | **C_bati** | Écart pairé Δ [IC95] |
|---|---|---|---|---|---|
| **nu** | 42 838 | 2,87 % | **4,79** [3,11 – 6,71] | 4,90 [3,27 – 6,84] | **+0,20** [−0,86 , +1,23] |
| **bâti** | 239 795 | 1,52 % | **5,02** [3,95 – 6,27] | 5,44 [4,28 – 6,74] | **+0,41** [−0,27 , +1,07] |

**Calibration (ECE) :**

| Population | actuel | C_bati | dégradée ? |
|---|---|---|---|
| vivier (probabilité servie) | 0,0012 | 0,0012 | non |
| segment nu | 0,0127 | 0,0134 | +0,0007 (négligeable) |
| segment bâti | 0,0012 | 0,0013 | +0,0001 (négligeable) |

Lecture : sur les deux segments, C_bati est **plus haut en estimation ponctuelle** (nu
+0,10 ; bâti +0,41) et **jamais plus bas hors bruit**. Mais les deux écarts pairés
**incluent 0** dans leur IC95 → statistiquement « dans le bruit ». La calibration de la
probabilité servie (vivier) est identique ; les écarts par segment sont négligeables.

---

## 2. Le verdict mécanique de la double barre

La règle (dalle §6, arbitrée 19/08/2026), appliquée sans interprétation :

| Critère | Test | Résultat |
|---|---|---|
| **(a)** inférieur hors bruit sur AUCUN segment | aucun Δ pairé entièrement < 0 | **✓ vrai** (nu et bâti straddlent 0) |
| **(b)** supérieur hors bruit sur AU MOINS UN segment | un Δ pairé entièrement > 0 | **✗ faux** (nu +0,20 [−0,86,+1,23] · bâti +0,41 [−0,27,+1,07] — les deux franchissent 0) |
| **(c)** ECE ne se dégrade pas | ECE vivier candidat ≤ servi | **✓ vrai** (0,0012 = 0,0012) |

**(a) ∧ (b) ∧ (c) = faux → C_bati NON PROMU.** Le critère bloquant est (b) : le gain bâti,
réel en tendance (mesuré +11 % en M127-bis, +9,6 % en M130, +8 % ici), n'atteint jamais la
signification à 95 % parce que la population de notation est petite — le top 0,4 % du bâti
= 959 parcelles, dont ~15 mutations observées attendues (base 1,52 %). À cet effectif,
l'IC de l'écart pairé reste large ([−0,27 , +1,07]) et couvre 0.

---

## 3. Les références v2 gravées (les notes du SERVI, par segment)

Le 6,73 a pris sa retraite. Les références sont désormais les notes du **modèle servi
(actuel) sur le vivier réel q_v10_m129**, par segment — à recalculer et redire à chaque
changement d'univers :

| Segment | **Référence v2 (RR@0,4 %)** | IC95 |
|---|---|---|
| **nu** | **4,79** | [3,11 – 6,71] |
| **bâti** | **5,02** | [3,95 – 6,27] |

(Vivier d'aujourd'hui : nu 42 838 · bâti 239 795, hors copro ; univers servi q_v10_m129,
285 781. Si l'univers bouge, ces deux nombres se recalculent et se redisent — ils ne sont
pas gravés dans le marbre, seulement dans le run servi du jour.)

---

## 4. C_bati n'est pas promu → pas de plan M132 à déclencher

La condition du mandat (« Si C_bati est promu : le plan M132 ») n'est pas remplie. Rien à
exécuter. Ce qu'il faudrait pour trancher un jour la question bâti — SANS rien promettre :

1. **Plus de puissance, pas un autre modèle.** Le signal bâti est stable et positif sur
   trois examens ; ce qui manque, c'est la puissance statistique. Deux leviers honnêtes :
   - agréger l'écart pairé sur **plusieurs folds** (2023 + 2024 + 2025) au lieu du seul
     2025 → ~3× l'effectif de mutations, IC resserré ;
   - ou noter le bâti sur un **top plus large** (le top 0,4 % est un choix ; un top 1 %
     bâti = ~2 400 têtes, IC plus étroit) — mais ce serait rouvrir l'arbitrage de la
     métrique, ta décision.
2. **Si, sous plus de puissance, le Δ bâti pairé passe entièrement > 0** et que nu ne
   régresse pas hors bruit et que l'ECE tient → C_bati franchit la double barre, et M132
   devient : re-fit sur toutes les données (2017-2025), calibration, run unique, bascule
   par runbook M81 + golden-rejeu. **À n'écrire qu'après un examen qui passe.**

**La promotion reste ta décision, sur ce rapport.** En l'état, la métrique v2 — celle que
tu as arbitrée précisément pour créditer les gains segmentés — dit **non**, et le dit
mécaniquement.

---

## Annexe — Phase 1 (métrique gravée) & Phase 3 (le badge)

- **Phase 1** : la métrique v2 est gravée dans `docs/DALLE-ALGO.md` §6 (« La méthode ») —
  deux notes par segment, top 0,4 %, double barre, 6,73 à la retraite, invisible au client.
- **Phase 3** : le badge d'état du bien est posé sur chaque carte de résultat (liste,
  kanban, shortlist) — « Nu » / « Bâtie — on peut encore construire » / « Bâtie — construite
  au maximum ». **Affichage PUR** : le serveur envoie `etat_bien` (dérivé des colonnes
  existantes de `parcel_residuel` — emprise < 5 % → nu ; sinon SDP résiduelle > 0 → encore,
  = 0 → au maximum), le front n'affiche que ce fait. Mesuré sur le vivier : nu 67 250 ·
  encore 110 053 · au maximum 108 478 = 285 781. Captures : `qa/m131/captures/`.
  Golden 119/119 · tsc 0 · build · tests projet/filtre 117 passed.
