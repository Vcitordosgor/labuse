# AUDIT — LE CALCUL DU SCORE, DÉCORTIQUÉ

*Audit pur, aucune correction. Le score est le JUGE : `parcel_p_score_v2`, produit par le modèle épinglé
**`reports/m36-foncier/artifacts-m36-scoring2026.joblib`** (`p_v2/__init__.py:19` `MODEL_ARTIFACT`,
`model_version = m36-l2f-2026`, SHA gelé `FREEZE-scoring2026.json`). Chaque poids porte sa mesure.*

---

## RÉSUMÉ EN UNE PAGE

Le score est une **régression logistique L2 sur features encodées en WoE**, produisant un **log-hazard
additif** `z = intercept + Σ coef×WoE(bin) + interactions`, converti en **probabilité de vente sous
12 mois** par une **calibration isotonique**. 29 features (24 actives + 5 gelées), 5 croisements, effets
d'année. Entraîné 2017-2024, calibré 2025, sert 2026. Performance : **RR@1158 = 6,73** (top ~1150 vend
6,7× plus que la moyenne). Présenté au client **par rang/tier**, pas par le pourcentage brut.

---

## 1. L'ENTRAÎNEMENT

**La cible** (`p_model/sql.py:6,32`) : `label` = la parcelle connaît une **mutation L2** dans l'année
civile `[01/01/Y, 31/12/Y]`. L2 = natures DVF `('Vente', 'Vente terrain à bâtir')` — ventes fermes, hors
VEFA/échange/adjudication. **Fenêtre = 12 mois calendaires** (pas « N mois » glissants). Le modèle servi
utilise la variante **L2-F (foncier, hors copropriétés)** — cf. le point copro ci-dessous.

**Convention as-of** (anti-fuite) : pour l'année Y, chaque feature n'utilise que des événements
**strictement antérieurs au 01/01/Y** ; fenêtres clampées au 01/01/2021 (millésimes DVF antérieurs
retirés par la DGFiP).

**Volumétrie** (`meta` de l'artefact + `walk-forward.csv`) : **n_train = 3 453 304** lignes
(parcelle × année, 2017-2024). Taux d'événement de base **~1,5-2,0 %/an** (≈ 55 000 exemples positifs au
total, ~3,4 M négatifs) — problème **très déséquilibré**, d'où le RR comme métrique (pas l'accuracy).

**Le walk-forward** (`walk-forward.csv`) — fenêtre **expansive** : train `[2017 … Y-1]` → test `Y`, pour
Y = 2020…2025. Le modèle servi = train 2017-2024, **calibration isotonique sur 2025**, scoring 2026
(jamais évalué contre un test — c'est la version produit ; la version *évaluée* est le fold 2025).

| Fold test | n_train | taux base | RR@1158 (île) | RR@1158 hors copro | ECE |
|---|--:|--:|--:|--:|--:|
| 2020 | 863 326 | 1,64 % | 10,96 | 9,41 | 0,0013 |
| 2021 | 1 294 989 | 1,96 % | 9,74 | 8,61 | 0,0033 |
| 2022 | 1 726 652 | 1,96 % | 9,14 | 8,63 | 0,0024 |
| 2023 | 2 158 315 | 1,72 % | 7,37 | 7,30 | 0,0032 |
| 2024 | 2 589 978 | 1,51 % | 8,12 | 7,08 | 0,0029 |
| **2025** | 3 021 641 | 1,54 % | **6,89** | **6,73** | 0,0014 |

**Le « RR 6,6× » = RR@1158 hors copro, fold 2025 = 6,73** (`SYNTHESE-M36.md:121`, critère de promotion
gelé). Lecture : on prend les **1 158 parcelles les mieux notées** (top ~0,27 %) ; **6,73 % s'y vendent
dans l'année contre 1,54 % en moyenne** → elles vendent **6,73× plus**. Le RR décroît de 2020 (11×) à
2025 (6,7×) — le modèle reste puissant mais se tasse sur les années récentes (dette à surveiller).

**⚠ Le point copropriété (finding M36, `SYNTHESE-M36.md`)** : les 3 424 copros (RNIC + DVF) ont un taux de
mutation de **29 % contre 1,52 % hors copro**. Le modèle M3 originel tirait sa force des copros ; **hors
copro il retombait à RR 2,85, SOUS sa propre ablation Z-seul (5,07)**. Le modèle servi (M3.6 L2-F) a été
ré-entraîné **hors copro** pour un vrai signal foncier (RR 6,73). Les copros sont **classées à part**
(tier assigné hors classement, `rang = NaN`), jamais mélangées au rang foncier.

---

## 2. LES FEATURES, UNE PAR UNE

**29 features dans l'artefact servi** (le `feature_names` de l'artefact les liste toutes). **5 sont
« retirées »** (§5) mais **restent dans le modèle épinglé** avec leur coefficient — le retrait est
physique au prochain ré-entraînement (`features.py:29-32`). Blocs : **Z** (zone/secteur) et **D**
(dormance/parcelle).

**Importance réelle = |coef × amplitude WoE|** (l'écart de log-hazard entre le meilleur et le pire bin —
le coefficient seul trompe car les WoE n'ont pas la même étendue). Classement, de la plus lourde à la plus
légère. `manquant %` = part de lignes sans la donnée (dataset d'entraînement, le modèle les bin en
« manquant », il ne les jette pas).

| # | Feature | Bloc | coef | amplitude (log-hazard) | manquant % | Ce qu'elle mesure |
|--:|---|:--:|--:|--:|--:|---|
| 1 | **permis_bin** | D | +1,001 | **1,746** | 0 | ancienneté du dernier permis sur la parcelle |
| 2 | **tenure_bin** | D | +0,818 | **0,966** | 0 | ancienneté de la dernière mutation |
| 3 | **zone_plu** | Z | +0,514 | 0,793 | 0 | zone PLU (U/AU/A/N) |
| 4 | **canopee_pct** | D | +0,605 | 0,775 | 1,3 | % de canopée (LiDAR) |
| 5 | **rot_nu** | Z | +0,678 | 0,588 | 0 | rotation foncier nu du secteur |
| 6 | **rot_bati** | Z | +0,478 | 0,523 | 0 | rotation bâti du secteur |
| 7 | **piscine** | D | +0,787 | 0,435 | 0 | piscine détectée (ortho) |
| 8 | surface_m2 | D | +0,283 | 0,328 | 0 | surface de la parcelle |
| 9 | filo_pct_pauv | Z | +0,260 | 0,294 | 10,7 | part de ménages pauvres (Filosofi) |
| 10 | sdp_residuelle_m2 | D | +0,498 | 0,273 | **38,9** | droits à construire résiduels |
| 11 | pct_bati_secteur | Z | −0,329 | 0,255 | 0 | part de parcelles bâties du secteur |
| 12 | nu_constructible | D | +0,666 | 0,247 | 0 | nu ET en zone U/AU |
| 13 | filo_snv_pp | Z | +0,216 | 0,233 | 10,7 | niveau de vie / individu (Filosofi) |
| 14 | dens_bati_secteur | Z | −0,271 | 0,204 | 0 | densité bâtie du secteur |
| 15 | ndvi_moyen | D | +0,114 | 0,159 | 1,3 | vigueur de végétation (IRC) |
| 16 | filo_dens_pop ⛔ | Z | −0,161 | 0,139 | 10,7 | densité de population *(retirée)* |
| 17 | pente_moy_deg | Z | −0,141 | 0,134 | 1,9 | pente moyenne (°) |
| 18 | med_pm2_bati_36m | Z | −0,089 | 0,087 | 4,5 | prix médian bâti du secteur |
| 19 | pv_candidat | D | +0,337 | 0,085 | 0 | candidat photovoltaïque *(signal mort M71)* |
| 20 | tendance_pm2_bati | Z | +0,100 | 0,063 | 11,7 | tendance du prix bâti |
| 21 | sous_densite | D | −0,187 | 0,062 | 38,9 | sous-densité (parcel_residuel) |
| 22 | permis_24m_norm ⛔ | Z | +0,073 | 0,061 | 0 | densité de permis 24 m *(retirée)* |
| 23 | window_coverage ⛔ | Z | +0,492 | 0,052 | 0 | couverture DVF de la fenêtre *(retirée)* |
| 24 | acces_equipements | Z | +0,065 | 0,049 | 0 | accès école/santé/commerce/TCSP (OSM) |
| 25 | med_pm2_terrain_36m | Z | −0,062 | 0,047 | 6,2 | prix médian terrain du secteur |
| 26 | filo_pct_prop | Z | +0,050 | 0,041 | 10,7 | part de propriétaires (Filosofi) |
| 27 | dormance_droits ⛔ | D | −0,093 | 0,039 | 38,9 | droits non consommés *(retirée)* |
| 28 | qpv ⛔ | Z | −0,004 | **0,000** | 0 | quartier prioritaire *(retirée — mort)* |
| 29 | friche | D | +0,000 | **0,000** | 0 | friche Cartofriches *(mort : IV≈0)* |

**Constats** : (a) les **4 features de tête** — permis, tenure (activité récente sur/autour de la
parcelle), zone PLU, canopée — pèsent plus que les 15 dernières réunies. (b) **friche (0,0004) et qpv
(−0,004) sont morts** dans le modèle servi (aucune discrimination). (c) `sdp_residuelle_m2`,
`sous_densite`, `dormance_droits` ont **38,9 % de manquants** (trou `parcel_residuel` 23/24) → binés
« manquant », impact réel dilué.

**Découpage WoE des features de tête** (bornes réelles de l'artefact ; `taux` = taux de mutation observé
du bin, `woe` = log-odds relatif, `lh` = coef×woe = points de log-hazard ajoutés) :

**`permis_bin`** (coef +1,001) — *un permis récent = projet en cours = mutation imminente* :
| bin | effectif | taux | woe | log-hazard |
|---|--:|--:|--:|--:|
| **< 2 ans** | 54 616 | **5,94 %** | +1,294 | **+1,295** |
| 2-5 ans | 69 930 | 1,66 % | −0,026 | −0,026 |
| 5-10 ans | 55 617 | 1,62 % | −0,053 | −0,053 |
| 10 ans+ | 2 607 | 1,07 % | −0,450 | −0,450 |
| jamais | 3 270 534 | 1,64 % | −0,041 | −0,041 |

**`tenure_bin`** (coef +0,818) — *récemment échangée = ré-échangée* :
| bin | effectif | taux | log-hazard |
|---|--:|--:|--:|
| **< 1 an** | 66 560 | **4,90 %** | +0,892 |
| 1-2 ans | 56 903 | 3,14 % | +0,514 |
| 2-3 ans | 51 134 | 2,54 % | +0,336 |
| 3 ans+ | 148 906 | 2,49 % | +0,319 |
| inconnu (rien depuis 2021) | 3 129 801 | 1,56 % | −0,074 |

**`zone_plu`** (coef +0,514) — *constructible = liquide* :
| bin | taux | log-hazard |
|---|--:|--:|
| AU | 3,55 % | +0,388 |
| U | 1,97 % | +0,077 |
| inconnu | 1,40 % | −0,102 |
| N | 0,79 % | −0,396 |
| A | 0,78 % | −0,405 |

**`rot_nu`** (coef +0,678, monotone ↑) — de ≤ 0,0012 (**−0,276**) à > 0,0115 (**+0,312**), 10 tranches.
**`canopee_pct`** (coef +0,605, monotone ↓) — de ≤ 0,4 % (**+0,239**) à > 61,2 % (**−0,460**) : *plus c'est
boisé, moins ça mute*. **`piscine`** true → +0,412 (*terrain résidentiel*). **`nu_constructible`** true →
+0,195. *(Tables complètes des 29 : `reports/m36-foncier` model-card / artefact.)*

**5 croisements** (interactions, coef réels) : `tenure_bin×permis_bin` **−1,884** (le plus fort — corrige
le double-compte des deux signaux d'activité), `tenure_bin×surface_m2` −1,443, `ndvi_moyen×zone_plu`
+0,464, `tenure_bin×rot_nu` −0,652, `surface_m2×permis_bin` +0,418. Plus des **effets d'année** 2017-2023
(+0,14 à +0,37) ; 2024 = référence, **2026 hérite de la référence 2024** (toutes les dummies à 0).

---

## 3. LE CALCUL SUR DEUX PARCELLES RÉELLES

Reconstruit avec l'artefact servi (`m.margin`, `m.contributions`, `m.predict_proba`) sur le dataset
`p_model_ext_dataset` année 2026.

### 3a. Parcelle BIEN classée — `97408000AP1647` (rang **1/431 663**, tier **brûlante**)
```
z = intercept(-4,239) + contrib_Z(+1,064) + contrib_D(+1,724) + interactions(+0,471) + année(0)
  = -0,980  (log-hazard)
sigmoid(-0,980) = 0,273   →   p_raw calibré (isotonique) = 1,0000
```
Ses 5 raisons de tête : **permis < 2 ans (+1,295)**, zone **AU (+0,388)**, rotation nu élevée (+0,312),
canopée ≤ 0,4 % (+0,239), croisement tenure×permis (+0,221). *Lecture client : « permis déposé récemment,
en zone à urbaniser, secteur qui tourne, terrain dégagé » → mutation quasi certaine.*

### 3b. Parcelle MAL classée — `97420000AV0185` (rang **428 239/428 239** hors copro, tier **écartée**)
```
z = intercept(-4,239) + contrib_Z(-0,872) + contrib_D(-1,453) + interactions(+0,148) + année(0)
  = -6,416  (log-hazard)
sigmoid(-6,416) = 0,0016   →   p_raw calibré = 0,0000
```
Ses 5 raisons : **canopée > 61,2 % (−0,460)** (boisée), permis 10 ans+ (−0,450), zone **N (−0,396)**,
rotation bâti faible (−0,341), surface > 12 040 m² (−0,262). *Lecture : grande parcelle boisée en zone
naturelle, aucune activité — ne mutera pas.*

**L'écart de log-hazard entre les deux = 5,44** (de −0,98 à −6,42), soit un rapport de cotes ≈ 230×.

---

## 4. LA CALIBRATION

**Le score EST une vraie probabilité — au milieu.** La calibration isotonique est **excellente** :
**ECE = 0,0014 à 0,0033** selon le fold (l'écart moyen entre probabilité prédite et taux observé est
**~0,2 point de %**). Donc « 3 % » veut bien dire « ~3 % de ces parcelles se vendent ».

**MAIS les extrêmes saturent.** L'isotonique est monotone + clippée `[1e-7, 1−1e-7]` (`model.py:83`) : le
bin de tête est mappé à **1,0** et le bin de queue à **0,0**. Dans l'exemple 3a, un log-hazard de −0,98
(sigmoïde brute 27 %) ressort **p_raw = 1,0** — ce n'est pas « 100 % vendront », c'est « le sommet de la
distribution 2025, où le taux observé du bin isotonique atteignait le plafond ». **À ne pas lire au pied
de la lettre aux extrêmes** ; le classement, lui, n'en souffre pas (monotone).

**Comment le score est présenté aujourd'hui** (`p_v2/statuts.py`, `pipeline.py`) : **PAS par le
pourcentage brut**, mais **par le RANG et le TIER** :
- `p_raw` (proba) × `mult_base` (pénalité AU-sous-plancher, `pipeline.py:289`) → **rang / percentile HORS
  COPRO** (ties départagés par tirage seedé 974).
- **Tiers par rang** (`statuts.py`) : **chaude = top ~1 150** (rang ≤ `n_entree`, calibré pour ≈ 1 150,
  `calibre_n_entree` — c'est le fameux k=1158 du RR) **ET plancher capacité** (SDP > 0 ou surface ≥ 600 m²
  en U/AU) ; **brûlante** = sous-ensemble des chaudes à `contrib_D` élevé + événement < 12 mois ;
  `a_creuser` / `reserve_fonciere` en dessous ; `ecartee` = étage 0. Hystérésis : `n_sortie ≈ 1,4×n_entree`
  (une chaude reste chaude en zone tampon).
- Le client voit **le tier + le rang/percentile + les 5 raisons en français** (`libelles_client.py`
  traduit feature/bin → phrase métier), pas le « 12 % ». Distribution servie (run `q_v8_calibre`) :
  brûlante 118 · chaude 1 038 · a_creuser 29 978 · reserve_fonciere 2 964 · écartée 354 355 · déclassées
  ~43 000.

---

## 5. LES LIMITES CONNUES

**Les 5 features retirées (M35/M36, `features.py:146-151`)** — instables sur les folds (signe non stable,
coefficient quasi nul) : `permis_24m_norm`, `filo_dens_pop`, `qpv`, `window_coverage`, `dormance_droits`.
**Elles restent dans le modèle SERVI** (artefact épinglé) — `qpv` (coef −0,004, IV 0) et `window_coverage`
(IV 0) sont **morts** ; le retrait physique attend le prochain ré-entraînement. `friche` (non listée
retirée) est **morte aussi** (coef +0,0004). **→ 3 features mortes servies inutilement** (qpv, friche,
window_coverage).

**Ce que le modèle NE capte PAS** (constats de l'audit, sans correction) :
1. **La situation du PROPRIÉTAIRE** — aucune feature ne regarde le propriétaire (procédure collective
   BODACC, succession, âge dirigeant, PM en difficulté). `owner_type` est une **méta d'évaluation, jamais
   une feature** (`features.py:144`). Ces signaux vivent dans la cascade (« étage 2 », points/événement),
   **hors du modèle appris** — cf. [[project_audit_sources_score.md]]. Le plus gros gisement inexploité.
2. **La latence DVF ~6 mois** — le label et les rotations accusent le retard de publication DGFiP ; une
   vente de fin 2025 peut manquer au scoring 2026.
3. **Les features « statiques 2026 »** — zone PLU, Filosofi (millésime 2019/2021), pente, canopée sont
   figées à l'ingestion : un reclassement PLU postérieur n'est pas historisé (fuite faible consignée,
   `features.py:96-98`).
4. **La saturation isotonique aux extrêmes** (§4) — p_raw 0/1 ne sont pas littéraux.
5. **La dérive temporelle** — RR de 11× (2020) à 6,7× (2025) ; le modèle vieillit, l'année 2026 est
   scorée sur la référence 2024.
6. **Le trou `parcel_residuel` (38,9 %)** affaiblit tout le bloc « droits résiduels » (sdp, sous_densite,
   dormance) sur une parcelle sur trois.
7. **Les copros sont hors modèle foncier** (taux 29 % — classées à part) : le score foncier ne les juge
   pas, par construction.

---

*Aucun ré-entraînement, aucune modification. Branche `audit/score-calcul`, non mergée.*
