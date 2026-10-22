# ÉTUDE V6 — Lot E : document depuis la même étude + bilan surfacique clos

## PDF depuis la même étude (même study_id, mêmes chiffres, prouvé par garde)
- **study_id stable** : `_study_id(entree)` = empreinte SHA-1 de la configuration (idus + type + programme
  + hypothèses). Même config → **même `study_id`** (`EF-xxxxxxxxxxxx`), servi dans le payload et affiché à
  l'écran ; le PDF part de la même config → le même document. Config différente → id différent.
- **PDF = écran, prouvé par garde** : le verrou `nombres_hors_payload(payload, html)` renvoie **[]** sur le
  PDF collectif V6 — tout nombre imprimé est un nombre du payload (donc de l'écran), aucune 2ᵉ source.
- **PDF collectif** : le document 9 pages (IMPLANTATION-3) fonctionne tel quel sur le payload V6 (synthèse,
  scénario, contrôles, règles citées, hypothèses). Preuve : `pdf/etude-collectif-etang-sale.pdf` (102 Ko).
- **PDF lotissement (nouveau)** : `rendu_lotissement` — même payload, numéro = `study_id` ; tableau des
  lots, voirie, pleine terre (contrôle), **bilan surfacique clos**, stationnement, raccordements, régime.
  La route `/modules/etude/pdf` branche sur `payload["lotissement"]`. Preuve :
  `pdf/lotissement-saint-leu-ac264.pdf` (9,6 Ko). (Le verrou `nombres_hors_payload` est pour l'instant la
  forme collectif ; la version lotissement est un suivi.)
- **Bouton « Générer le PDF ↓ »** sur les deux résultats (collectif + lotissement), via `useOuvrirDocument`
  (blob + erreurs FR), avec la même config que l'écran. `study_id` affiché sous le résultat.

## Bilan surfacique clos (aucune double comptabilisation)
- **Lotissement** : **assiette = lots + voirie + espaces communs + PPR rouge + hors-zone (A/N, marges)**,
  à la tolérance 2 % près. Clos par construction (communs = net − lots − voirie ; hors-zone = assiette −
  net − PPR − EBC). AC0261 : 11 330 = 5 806 + 1 323 + 1 916 + 2 130 + 154 (**écart 0,0**). AC0264 :
  9 578 = 5 839 + 700 + 1 758 + 0 + 1 281 (**écart 0,0**). Affiché (badge « clos ») + dans le PDF.
- **Collectif** : pas de somme fallacieuse des 4 grandeurs (volontairement séparées). Deux garanties
  DISTINCTES : (1) **décomposition du terrain close** — contenance = zone constructible + hors-zone
  (A/N, reculs, PPR) ; (2) **plan sans chevauchement** (contrôles géométriques verts). `clos = (1) ∧ (2)`.
  Étang-Salé : contenance 1 746 = zone 1 155 + hors-zone 591 ; plan sans chevauchement → **clos**.

## Carte Docs / hypothèses / règles
- **Carte Docs** : l'Étude est déjà la 9ᵉ carte Docs (IMPLANTATION-4) ; le wizard V6 y vit (les 4 types,
  dont le lotissement, passent par la même carte). Pas de nouvelle carte à ajouter.
- **Règles et sources conservées** : chaque contrôle porte sa citation (article/page), l'étape 2 affiche la
  règle de stationnement (article + millésime), l'étape 1 les sources + millésimes. Le lotissement cite UD
  9/12/13 + L'ALUR pour l'absence de min-lot.
- **Hypothèses modifiables** : le programme T1–T4 (surfaces hypothèses) est éditable à l'étape 3 (« Modifier
  le programme »). ⚠ Les hypothèses MOTEUR (profondeur, coef plancher) ne sont pas ré-exposées en éditeur
  dans EtudeV6 comme dans l'ancien M22 — suivi éventuel.

## Vérifié
- **tsc 0 · vitest 287/287** (EtudeV6 : bilan + bouton PDF). **pytest** : `test_etude_v6_bilan` **4/4**
  (study_id stable, PDF=écran garde [], bilan collectif clos, bilan lotissement clos + PDF) +
  `test_etude_v6_lotissement` 3/3 (+ reste implantation, 1 échec `test_route_etude_*` **pré-existant**).
- **chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.**
- **Preuves** : `pdf/etude-collectif-etang-sale.pdf`, `pdf/lotissement-saint-leu-ac264.pdf` ;
  capture `captures/lotE-lotissement-bilan-pdf.png` (bilan clos + bouton PDF + study_id).

## Bilan des 5 lots
A (parcours 3 étapes) · B (résultat qui explique : 3 variantes, 4 grandeurs, 5 états, verdict) · C
(stationnement par type : règle PLU + plafond L151-35 à confirmer) · D (lotissement = division-or à la
demande, réseau en peigne) · E (PDF même study_id + bilan surfacique clos). Branche `feat/etude-v6`,
non mergée.
