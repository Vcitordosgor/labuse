# M5.1 lot 3.2 — Tableau lexical : « brûlante », « V », « vendabilité », « à surveiller »

Grep exhaustif des chaînes VISIBLES UTILISATEUR (UI, exports, tooltips), 13/07/2026, branche `feat/m51-unification`.
Règle appliquée : **un seul mot « brûlante » dans l'app = brûlante v2** ; toute mention v1.3 devient « événement »/« signaux vendeur » ou disparaît ; « À surveiller » disparaît de l'UI (l'équivalent v2 est « Réserve foncière ») ; le badge « V nn » disparaît (le dossier propriétaire reste dans la fiche).

## Occurrences traitées (modifiées dans ce mandat)

| Fichier | Avant | Après | Traitement |
|---|---|---|---|
| `panel/ResultsSection.tsx` | Compteur « 🔥 120 brûlantes » (v1.3, chaude∧V≥17) | supprimé | Le tier v2 « Brûlantes v2 (117) » est LE chiffre ; les événements restent en badges datés sur les cartes |
| `panel/ResultsSection.tsx` | Chips « Chaude / À surveiller / À creuser / Écartées » (matrice) | « Tout / Brûlantes v2 / Chaudes / Réserve foncière / À creuser / Écartées » (tiers v2 effectifs) | Bascule pilotage (lot 1.1) |
| `panel/ResultsSection.tsx` | Tri « triés par V (vendabilité) ▾ » (défaut) | « triés par rang P · ×N · surface · commune » (défaut rang P) | Le tri par V disparaît du sélecteur (lot 1.3) |
| `panel/ResultsSection.tsx` | Badge `V nn` (VBadge) sur chaque carte | supprimé (chip tier v2 en premier, rang + ×N) | Lot 1.4 — le dossier propriétaire reste dans la fiche |
| `panel/ResultsSection.tsx` | « N chaudes · M à surveiller · K à creuser » | « N brûlantes v2 · M chaudes · K réserve foncière » | Lot 1.1 |
| `panel/ResultsSection.tsx` | Badge « ● CHAUDE · ÉVÉNEMENT » (statut matrice forcé) | « ● ÉVÉNEMENT · date » | La bascule matrice n'est plus énoncée ; l'événement daté reste |
| `header/Header.tsx` | Popover filtre : section « STATUT (multi) » matrice | « VERDICT · SCORING V2 (multi) » (5 tiers) | Lot 2.2 |
| `header/Header.tsx` | « 🔥 Brûlantes seulement (chaude + V ≥ 50) » + bandes V | supprimés ; « SIGNAUX PROPRIÉTAIRE » (libellés métier) + veille succession + hors copro | Lot 2.2 |
| `map/MapView.tsx` | Pastille carte « V nn » / « 🔥 V nn » (zoom 15+) | pastille « #rang » sur brûlantes/chaudes v2 | Aucun « V nn » à l'écran (lot 5.1) |
| `map/MapView.tsx` | Liseré braise sur brûlantes v1.3 (`brulante`) | liseré braise sur tier v2 `brulante` hors étage 0 | Un seul sens |
| `fiche/Fiche.tsx` | Badge d'en-tête « 🔥 V 45 » | « signaux vendeur 45/100 » (couleur bande) | Le sigle nu disparaît |
| `fiche/Fiche.tsx` | « 🔥 BRÛLANTE — chaude Q×A + signaux vendeur forts (V ≥ 50) » (tooltip + chip bloc V) | supprimé | Mention v1.3 → disparaît |
| `fiche/Fiche.tsx` | Bloc « Vendabilité » (libellé) | « Signaux vendeur » | Lexique client ; le contenu (dossier) est conservé |
| `fiche/ScoreV2Block.tsx` | Contributions « canopée [≤ 0.4] », « croisement ancienneté… × … [] » | phrases client (« parcelle peu boisée », « mutation et permis récents combinés ») — bin exact au survol | Lot 3.3, table versionnée `libelles_client.py` |
| `segments/SegmentsPage.tsx` | « Foncier — parcelles chaudes & Brûlantes 🔥 » + compteurs matrice/v1.3, « triée par vendabilité » | « Foncier — Brûlantes & chaudes » + compteurs tiers v2, « triée par rang » | Lot 2.3 |
| `outils/ModulePanel.tsx`, `moteurs.tsx`, `M22Programme.tsx` | Statut matrice en label principal (`STATUT_META`) | `TierBadge` : tier v2 principal + « (matrice : X) » secondaire discret | Lot 3.1 |
| `App.tsx` (restitution IA) | « #1 · Q 85 » | « #1 · ×34,2 » (×N v2 ; repli Q si pas de run) | Cohérence restitution |
| API `/parcels/export.csv` | colonne `brulante` (v1.3) ; tier_v2 en 4e position | colonne supprimée ; `tier_v2, rang_v2, mult_v2, copro, veille_succession` en tête, `statut_matrice` en secondaire | Le client ne reçoit jamais deux vérités |
| API `/stats` | `chaude/a_surveiller/a_creuser/ecartee` + `brulantes` v1.3 | ventilation `tiers` v2 + `opportunites` ; matrice via `legacy=1` (deprecated) | Lot 2.1 |
| API `/ia/search` (stub + prompt) | « brûlantes » non traduit ; « chaude/surveiller/creuser » → statuts matrice | « brûlantes » → tier `brulante` ; « à surveiller » → `reserve_fonciere` ; champ `tiers` | Lot 2.2 |
| API fiche `score_v.brulante` (flag v1.3) | servi | supprimé du payload | Mention v1.3 disparaît |
| `api/projets.py` (« pourquoi » projet) | « À surveiller · qualité 62/100 » | tier v2 en tête (« Chaude v2 · … »), matrice en repli sans run | Lot 2.3 |
| `shortlist.py` (badges promoteur) | badge « À surveiller » | « À creuser » | Lexique |

## Occurrences conservées (justifiées)

| Fichier | Chaîne | Justification |
|---|---|---|
| `lib/status.ts` `STATUT_META` (« À surveiller », « Chaude »…) | labels matrice | Uniquement : (a) repli si AUCUN run v2 (base vierge), (b) secondaire discret « (matrice : X) » des modules Outils, (c) légende legacy (même condition a). Jamais pilote quand un run v2 existe. |
| `map/Legend.tsx` branche legacy | légende matrice | Ne s'affiche que si `/v2/modele` est indisponible (pas de run v2) — la vignette est synchronisée v2 sinon (vérifié E2E). |
| `fiche/Fiche.tsx` `SCORE_TIP.v` (tooltip) | « V — Vendabilité : signaux publics… » | Explication pédagogique du score du dossier propriétaire, au survol uniquement ; le libellé affiché est « Signaux vendeur ». |
| `api/pdf_premium.py` ligne « Statut matrice (historique) : X » | secondaire | Doctrine M5 : le tier v2 pilote le PDF, la matrice descend en historique 6,5 pt. |
| `outils/ScoringV2.tsx`, `outils/registry.ts` | « Brûlantes v2 » | C'est LE bon vocabulaire (tier v2). |
| `outils/TimeMachine.tsx:64` | filtre données `['chaude','a_surveiller','a_creuser']` | « Remonter le temps » compare des RUNS MATRICE historiques — filtre de données, aucun label affiché. Consigné pour M6 (1.5 audit outils). |

## Restes consignés (hors périmètre M5.1 — bascule d'affichage uniquement)

| Endroit | Constat | Proposition |
|---|---|---|
| `api/events.py` (moteur de notifications) | les bascules détectées comparent `matrice_statut` entre runs ; le détail des notifications peut énoncer « Bascule vers a_surveiller » | Le moteur d'événements est FONCTIONNEL (comparaison de runs), pas un affichage : bascule vers les tiers v2 = mandat séparé (M6 1.6 audite les notifications). Aucune nouvelle notification générée pendant M5.1. |
| Périmètres candidats des modules (WHERE `matrice_statut IN (…)` dans modules.py/moteurs.py) | les pools de candidats des modules restent matrice | Changer un pool change les RÉSULTATS des modules (pas leur affichage) — décision produit à instruire en M6 (1.5). |
| `dvf`/fiches : lettres Q et A | affichées (scores qualité/accessibilité) | Non visées par le mandat — la matrice reste calculée et documentée dans la fiche (section Qualité). |
