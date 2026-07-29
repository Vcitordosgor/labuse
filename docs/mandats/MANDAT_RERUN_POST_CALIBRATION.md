# MANDAT « RE-RUN POST-CALIBRATION » — SPEC

> **Statut : SPEC SEULEMENT — rien n'est implémenté ni exécuté sans le GO de Vic sur la
> mesure d'ampleur (phase 1).** Rédigé le 29/07/2026.
>
> **CONTEXTE — le repli non optimiste est SUSPENDU, pas abandonné.** La phase A du mandat
> repli (`REPLI_NON_OPTIMISTE_PHASE_A_MESURE.md`) a révélé que le vrai sujet n'est pas le
> correctif gel mais le **décalage de base** : le run servi précède la calibration. Toute
> mesure de delta de correctif sur cette base mélange deux effets. Le repli reprendra sur la
> base fraîche, une fois ce re-run passé — sa population sera alors mesurée sur un état
> cohérent. Ce mandat est le préalable à tous les autres qui touchent la chaîne
> `parcel_residuel → residuel_socle → scoring servi → tiers`.

---

## 0. Le fait générateur

- **Run servi `q_v7_defisc` : calculé le 15/07/2026** (`parcel_p_score_v2.computed_at`,
  `p_score_v2_runs`).
- **Calibration PLU (phase 4) : 27-28/07/2026** — les YAML de ~17-21 communes ont reçu leurs
  hauteurs, `habitat` sourcés et `zones_au_st`. **Le scoring servi n'a jamais vu ce travail.**
- **Symptôme mesuré (phase A repli)** : 412 parcelles sont servies à ≥ 90 % de recouvrement
  dans des zones `habitat: interdit` AVEC hauteur, que M6 2b (`phase1.py:277-294`, code déjà
  en production) DEVRAIT exclure. Elles ne le sont pas → preuve que le run précède les YAML.
  C'est un symptôme, pas la cause : la cause est le décalage de dates.

**Constat produit** : le produit sert aujourd'hui, pour ~17-21 communes, des tiers calculés
sur des règles GÉNÉRIQUES alors que les règles CALIBRÉES existent depuis le 28/07. Les tiers
servis ne sont pas « justes en attente d'un correctif » — ils sont **déjà faux**. Le
mouvement des tiers n'est donc plus une condition d'arrêt : c'est un **constat**.

---

## 0bis. Barème `residuel_socle` DÉCALIBRÉ — préalable CONFIRMÉ (mesuré 29/07)

Le barème `residuel_socle` (`etage0_ext.py:31`, bornes SDP 5000/2000/800/300/100 → bonus
+30/+25/+15/+5/−10/−25) a été extrait des **32 448 verdicts Saint-Paul**. La consolidation
SP de la nuit a relevé la **pleine terre de 20 % à 40 %** sur U3c/U6c (`pleine_terre_pct: 40`
au YAML courant). **Mesure (recalcul des 31 991 résiduels SP sur YAML courants, table de
travail `repli_sp_residuel`, lecture seule)** :

- **Direction monotone** : 6 577 SP en baisse, **0 en hausse**, 25 380 stables. La calibration
  ne fait que RÉDUIRE (pleine terre ↑ → emprise ↓ → SDP ↓). SDP moyenne 488 → 424 (**−13 %**).
- **Pools ciblés** : U3c −14 % (5 842 parc.), U6c −13 % (4 854), U3b −7 %, U6b −3 %.
- **Transitions de palier** : **1 633 SP (5,1 %) changent de palier, TOUTES vers le bas** —
  dont **74 quittent le palier +30** (belle/majeure opération), 163 quittent +25.

**Verdict : le barème est décalibré.** Ses bornes ont été ajustées sur des résiduels gonflés
par l'ancienne pleine terre ; appliquées aux résiduels recalculés, elles sur-bornent et
sous-récompensent d'un palier ~5 % des parcelles — systématiquement, sur les plus gros pools.
**Préalable confirmé : re-dériver les bornes du barème sur les verdicts SP recalculés AVANT le
re-run de l'île** — sinon on propage un barème périmé sur les 24 communes. Le re-run seul ne
suffit pas. (La re-dérivation ~translate les bornes de ~−13 %, restaurant l'alignement
palier↔verdict ; mesure de re-dérivation à ouvrir en préalable.)

---

## 1. Mesure d'ampleur d'ABORD (préalable bloquant — le chiffre qui dit ce que la calibration a produit)

Avant toute bascule, mesurer — **lecture seule, sur un run de travail isolé, jamais sur le
run servi** — l'écart entre l'état servi (`q_v7_defisc`, générique-15/07) et un re-calcul sur
les YAML courants. Trois grandeurs, **par commune et par tier** :

1. **`parcel_residuel`** — nombre de parcelles dont la SDP résiduelle change (et de combien) :
   `sdp_residuelle_m2`, `pct_potentiel`, `sous_densite`, `taux_emprise_pct`, `capacite_estimee`.
   Attendu : les gelés/interdits calibrés passent d'une SDP optimiste à 0 ou à une valeur
   contrainte. Repère déjà chiffré (phase A repli) : 370 gelés à ≥ 90 % portent 743 352 m² de
   SDP fictive.
2. **Score P** — nombre de parcelles dont `p_raw` / `percentile` / `rang` bougent, distribution
   du delta. Source : `parcel_p_score_v2`.
3. **Tier** — matrice de transition tier_avant × tier_après (`brulante`/`chaude`/
   `reserve_fonciere`/`a_creuser`/`ecartee`), par commune. **C'est LE livrable de la phase 1** :
   il dit ce que la calibration a réellement produit sur le foncier servi.

**Sortie** : un tableau de transition + la liste nominative des parcelles qui QUITTENT un tier
commercialement servi (brûlante/chaude/réserve), avec avant/après et le motif calibré (zone,
article, page). Point d'arrêt et arbitrage Vic sur ce tableau avant la phase 2.

---

## 2. Procédure complète de re-run (exécutée seulement après GO phase 1)

Pipeline strict, chaque étape isolée sur un run de travail versionné (jamais d'écriture sur
le run servi avant la bascule finale) :

1. **Re-calcul de `parcel_residuel`** sur les YAML courants — pour TOUTES les parcelles des
   communes calibrées (pas seulement les gelés : la calibration change aussi hauteurs/emprises
   des zones constructibles). Table de travail `parcel_residuel_rerun`, diff vs production.
2. **Re-passe de la cascade** (`phase1.py` + étages) sur les communes calibrées — M6 2b
   s'allume sur les interdits calibrés, `residuel_socle` relit la SDP recalculée. Run cascade
   de travail, diff des verdicts.
3. **Re-run du champion P** — mêmes hyperparamètres, MÊME artifact (cf. §3), features
   recalculées (`parcel_residuel_rerun`, `zone_plu` courant). Run `p_v2` de travail versionné.
4. **Arène OBLIGATOIRE** — challenger (re-run) vs champion servi (`q_v7_defisc`), gate boussole,
   ECE, churn commenté, pas d'exception forward. `labuse arene --challenger <rerun> --champion
   q_v7_defisc`. Le re-run n'est PAS présumé meilleur : il est présumé JUSTE ; l'arène le prouve.
5. **Décision Vic** sur le rapport d'arène + le tableau de transition (§1) + le sens (§4).
6. **Bascule du run servi** — protocole `scripts/a1_bascule_v7.py` (purge cible, copie,
   `computed_at` postérieur, header de run versionné). Nouveau run servi = re-run validé.
7. **Mise à jour du golden** (§5) — commit dédié, distinct de la bascule.

**Séquencement inter-mandats** : ce re-run passe AVANT toute reprise du repli non optimiste,
des hypothèses du bilan et de la phase 4 résiduelle — c'est la base fraîche dont ils dépendent.

---

## 3. Le champion P est INTOUCHÉ — preuve exigée

Le re-run ne ré-entraîne RIEN. Il ré-applique le champion existant à des features recalculées.

- **Artifact figé** : `model_version = m36-l2f-2026`, `model_sha256 =
  00a58008143d5260b9aea192eb73b94bd11693cba6cc4f99fd622da3a4959b64` (colonne `model_sha256` de
  `p_score_v2_runs`). Le même sha porte déjà `q_v6_m8` (champion) ET `q_v7_defisc` (servi) —
  preuve que l'artifact est stable d'un run à l'autre, seule la composante V (fenêtre défisc)
  différait. **Le re-run DOIT reproduire ce sha256** ; un sha différent = ré-entraînement
  interdit, arrêt immédiat.
- **Séparation features/modèle** : le modèle est chargé par `PModel.load` (`model.py:131`,
  `joblib.load`) — un objet sérialisé (encodeur WoE + coefficients figés). Les features sont
  calculées à part (`p_model/features.py`) à partir des tables (`parcel_residuel`, `zone_plu`,
  …). Recalculer les features ne touche NI les coefficients NI les bins NI l'intercept.
- **Contrôle** : `params` (hyperparamètres) et `model_sha256` du run de travail == ceux de
  `q_v7_defisc`, champ à champ. À joindre au rapport d'arène.

---

## 4. Les tiers bougeront — l'enjeu est le SENS, pas le fait

Le mouvement est attendu (les règles changent). Critère de validation, **le seul qui compte** :

> Les parcelles qui PERDENT leur rang doivent être exactement celles dont la SDP était
> SURESTIMÉE par le repli générique (gelés, interdits, hauteurs génériques trop hautes).
> Les parcelles qui GAGNENT du rang doivent être celles que la calibration densifie
> légitimement (hauteurs calibrées supérieures au repli prudent).

Mesure du sens : pour chaque parcelle qui change de tier, corréler le sens du mouvement au
signe du delta `sdp_residuelle_m2` (avant − après). **Un mouvement à contre-sens (gagne du
rang alors que sa SDP calibrée BAISSE, ou inversement) est un bug**, pas un résultat — à
isoler et expliquer avant toute bascule. Échantillons nominatifs avant/après pour lecture Vic,
en priorité sur brûlantes/chaudes qui basculent.

---

## 5. Le golden sera mis à jour — légitime cette fois

La référence `reports/m6-audit/golden/golden-parcelles.json` a été générée le **15/07**, AVANT
la calibration. Elle encode donc un état pré-calibration : certaines ancres classent positives
des parcelles que le règlement calibré interdit désormais.

- **Cas prouvé (phase A repli) : 97407000AV0096 (Le Port)** — ancrée `tier_v2:
  reserve_fonciere`, mais 100 % en zone **Ue**, listée `zones_au_st` du PLU Le Port : *« habitat
  interdit (logement de surveillance/gardiennage uniquement) »*, source *Art. Ue 2 p.80 et Ue 8
  p.82*. La référence encode une parcelle qui n'aurait jamais dû être positive → **défaut de la
  référence**, pas sur-exclusion du re-run.
- **Discipline** : mise à jour du golden en **commit dédié, distinct de la bascule** ; chaque
  ancre modifiée datée et motivée (zone calibrée + article + page) ; on ne corrige PAS le golden
  pour qu'il valide le re-run — on le réaligne sur l'état calibré, motif à l'appui, et le re-run
  se mesure contre le golden réaligné. Re-mesure du golden 116 avant/après attendue.

---

## Artefacts et ancres
- Mesure phase A repli : `REPLI_NON_OPTIMISTE_PHASE_A_MESURE.md` ; tables `repli_pcov`,
  `zone_cat_p`.
- Run servi : `parcel_p_score_v2` / `p_score_v2_runs` run_id `q_v7_defisc`.
- Zones : `spatial_layers kind=plu_gpu_zone` (classe sur `subtype`, interdit/gel sur `name`).
- Bascule : `scripts/a1_bascule_v7.py`. Champion : `model.py` (`PModel.load`).
- Détection de gel : `calibree=True` + famille de zonage, JAMAIS `constructible_neuf` seul
  (cf. leçon gravée).
