# PLU-CALIBRAGE-2 — Sondage, puis brancher le calcul

Branche `feat/plu-calibrage-1`, départ `1f0b05f4`. Un commit par lot, aucun merge.

## Lot 0 — le sondage (`49d1f0da`)

`qa/plu_calibrage2_sondage.py` tire 10 règles au hasard (graine reproductible) parmi les
validées de Saint-Denis et sort, dans UN fichier que Vic lit à la place du PDF
(`captures/plu-calibrage2/sondage_10_regles.txt`) : zone, rubrique, valeur, citation, et
l'extrait de la page autour de la citation (5 lignes avant/après).

## Lot 0bis — le contrôle qui a sauvé le calibrage (`3febed10`)

Le sondage v1 (citation-sur-la-page) disait « calibrage sûr », mais le **branchement du calcul
a révélé une misattribution** : des valeurs de SECTEUR étaient gravées sur la zone de BASE (Ud
faîtage/niveaux = Udop « R+5/18m » ; Up emprise = Upi ; Uv faîtage = Uva), alors que le
règlement (Ud.10 p.44) réserve la base au **prospect L≥H**. Branché tel quel, Ud passait de R+1
(prospect) à R+5 (~14→54 logts). **Sur consigne (le mandat ne continue pas sur un calibrage
douteux), arrêt, correction, re-sonde.**

- **Contrôle d'ATTRIBUTION permanent** ajouté au sondage (vaut pour les 22 autres communes) :
  une citation doit apparaître, sur sa page, sous un marqueur (« En secteur X », « Article X.n »,
  marqueur joint « Udop, Udp ») **compatible** avec la zone (== zone, ou secteur sous l'article
  de sa base). Robuste au texte quasi identique entre secteurs frères ; attrape une base portant
  une valeur de secteur (prouvé : `sondage_attribution_a_capte_avant_correction.txt`).
- **Correction** (`qa/plu_calibrage2_corriger.py`, re-lecture par coordonnées p.33-34/43-44/84) :
  base Ud/Up = prospect/**plage** (feuille `plage`, sans valeur unique → l'étape reste ESTIMÉ) ;
  secteurs **Udop/Udp** (18 m/R+5, 70 %), **Upi** (11 m/hé 6,5 m/80 %), **Upr** (16 m/hé 12 m/
  R+3/70 %), **Uva** (4 m), **Uvac/Uvl** (10 m) — citations verbatim, article + page.
- Re-sonde : **76 feuilles validées, 0 misattribution, « Calibrage sûr »**.

## Lot 1 — brancher le calcul (`8385afb0`)

`resolve_zone` est enrichi en UN point (`_appliquer_calibrage`) des règles validées lues par
`destinations.regles_zone` :

- **règle `valide`** → sa valeur est utilisée ET l'étape passe **SOURCÉ** (article + page,
  stampé « (PLU, calibrage validé) ») ;
- **règle `absent`** (silence prouvé) → « **pas de règle dans le PLU** » (nouveau prov `absent`,
  badge « Pas de règle PLU ») ;
- **`propose` / commune non calibrée** → overlay `None`, **IDENTITÉ stricte** (rien ne change).

`niveaux_max` (nouveau champ) : un R+n LU au règlement est utilisé tel quel, jamais dérivé d'une
hauteur. Aucune autre modification au calcul ; formules évaluées telles quelles.

> **NB honnête** : Saint-Denis est **déjà calibrée** par `config/plu_saint_denis.yaml` (l'autre
> système, valeurs concordantes). Sur cette commune, le branchement **re-source** vers les
> citations auditées (sondage + attribution + V6a) et garde correctement le **prospect** en base
> (plus de R+5 fautif) ; la bascule ESTIMÉ→SOURCÉ **pleine** se verra sur les 22 communes sans
> `plu_<slug>.yaml` (mandat 3). Preuve `calc_saint_denis_Ud_avant_apres.txt` : parcelle Ud —
> emprise/reculs re-sourcées, niveaux R+1 prospect conservé ; **Saint-Pierre IDENTIQUE** (overlay
> = identité sur une commune non calibrée).

## Lot 2 — la zone Up par secteur (`156514a0`)

Le zonage GPU sert les secteurs comme **codes de zone distincts** (« Upi : … », « Upr : … » →
`zone_dominante` donne `Upi`/`Upr`). Donc une parcelle **qui porte le secteur** utilise déjà sa
valeur via le lot 1 → étapes SOURCÉES. Preuve `calc_saint_denis_Up_secteur.txt` : parcelle Upi,
emprise Art. Up.9 + niveaux Art. Up.10 **SOURCÉES**.

Sinon (base Up nue) : `ZoneRules.hauteur_plage`/`emprise_plage` → le moteur **affiche la plage**
(« hauteur par secteur 11–16 m : Upi 11 m ; Upr 16 m », « emprise 70–80 % : Upi 80 ; Upr 70 »)
en **restant ESTIMÉ** — jamais simplifié en silence (unit-testé ; aucune parcelle base Up nue :
le zonage ne sert que Upi/Upr).

## Preuves & checks

`captures/plu-calibrage2/` : `sondage_10_regles.txt`, `sondage_attribution_a_capte_avant_correction.txt`,
`calc_saint_denis_Ud_avant_apres.txt`, `calc_saint_denis_Up_secteur.txt`, `verrous_wG8.txt`.
`tsc -b` vert ; `labuse circuit verrous -w G8` vert (V6a « 76 règles validées »).
Tests : `test_plu_calibrage2_branchement` (9), `test_faisabilite` (19), `test_lot6a` (V6a), sondage/attribution.
