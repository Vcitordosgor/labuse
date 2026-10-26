# ÉTUDE V6 — Lot B : le résultat qui explique

Remplace la « ligne rouge » par un résultat qui explique, dans l'ordre du mandat.

## Livré
- **Moteur (`moteur.py`)** `etudier_complet` : UN SEUL passage de recherche → deux vues sans 2ᵉ run
  (budget 30 s tenu). `scenarios` = vue historique (Pareto des couvrants, [] si la demande ne tient pas,
  pour M22 + tests) ; `variantes` = **3 rôles mandat** choisis dans le même jeu (`_roles`) :
  **Votre programme** (le plus serré qui tient la demande), **Optimisation** (max logements, même type),
  **Alternative** (autre forme). `_depassement` = combien tiennent / lesquels manquent (jamais
  « impossible » sans ce chiffre).
- **Contrôles (`controles.py`)** : 5ᵉ état **« À confirmer »** (ambiguïté donnée/texte) appliqué à
  PPR rouge/bleue, prospect non chiffrable, servitudes, barème manquant — distinct de « Non effectué »
  (non calculé) et « Non applicable » (absent). Nouveau **`verdict_global`** (3 libellés : *Exploitable
  sous hypothèses / À compléter / Impossible pour cause établie*) avec la règle dure du mandat : un PPR,
  un accès ou un stationnement **À confirmer** interdit « Exploitable ». `statut_etude` historique intact.
- **Service (`service.py`)** : payload enrichi — `verdict`, `variantes[]` (chacune : résumé, contrôles
  5 états, **4 grandeurs**, écart chiffré, limite, plan masse), `depassement`. Les **4 grandeurs** jamais
  confondues : *sol restant* (mesuré) · *emprise mobilisable* (dérivé CES) · *SDP autorisée* (dérivé
  plafond) · *programme envisageable* (mesuré SDP dessinée).
- **Frontend (`EtudeV6.tsx`)** : résultat restructuré — bandeau **verdict** + onglets **3 variantes** ;
  4 grandeurs (cartes avec statut) ; plan masse de la variante active ; contrôles 5 états ; **récit**
  Votre demande → Ce que le terrain accueille → L'écart (réserve *prouvée*, pas une règle de trois) →
  Ce qui limite → Alternative ; bannière **dépassement** (combien tiennent, par quoi commencer).
  **Pont Bilan** = le bouton existant « Bilan de ce scénario » qui transmet le programme de la variante
  au Bilan existant (`EtudeEcran` → `BilanEcran depuisEtude`), **sans refonte du Bilan**.

## Vérifié
- **tsc 0 · vitest 284/284** (EtudeV6 6, dont bascule de variante + récit ; EtudeDocs recâblé).
- **pytest** : implantation1/2/pareto/distance + assiette — **134 passed**, 1 échec `test_route_etude_*`
  = **pré-existant** (DB `labuse_test` vide). Tests d'état mis à jour 4→5 (`test_cinq_etats_seulement`,
  prospect → À confirmer, `test_controles_cinq_etats`).
- **chasse_docs 20 OK · 0 ECART** (E-18/19/20). **chasse_donnees 21 OK · 2 ECART PRÉ-EXISTANTS** (cloche
  q_v20 ≠ servi q_v19, cf. ci-dessous) · 2 SKIP. Rien lié au Lot B.
- **Captures** (`captures/lotB-*`) : 3 variantes **Étang-Salé** (Exploitable sous hypothèses : votre
  programme 20 logts réserve +8 / optimisation 28 / alternative 27) et 3 variantes **Saint-Denis PPR**
  (verdict **À compléter** — PPR rouge+bleue + prospect **À confirmer** ; plan masse PPR hachuré) +
  `lotB-pont-bilan` (« depuis l'Étude · scénario Alternative », Bilan pré-rempli).

## Cloche (réponse à la précision 1)
Les 2 ECART `cloche-fraicheur`/`digest-vs-cloche` = **état de la base**, pas la branche : le run servi de
la branche est **q_v19** (`served_run.txt`/`served_manifest.json` figés au commit de base) ; la cloche du
base local partagé est à **q_v20** (events `detect_events` du 21/10 posés par un autre travail). Or
`q_v20_sources`/`q_v20` **n'existent pas** dans cette base → impossible d'aligner en servant q_v20, et
rejouer `detect_events` pour q_v19 = geste PROD (mail) proscrit. Quand chasse_donnees était à 23 OK·0
ECART, le servi ÉTAIT q_v20 (aligné). La branche ne touche ni `served_run.txt`, ni la cloche, ni la
bascule. → continué sans correction.

## Acceptation mandat (Lot B)
Demande→accueil→écart→limite→alternative ✓ · 4 grandeurs séparées ✓ · 3 variantes mêmes chiffres ✓ ·
5 états + verdict ✓ · PPR/accès/stationnement indéterminé interdit Exploitable (Saint-Denis → À compléter)
✓ · écart chiffré seulement depuis une variante dessinée ✓ · dépassement = combien tiennent, jamais
« impossible » sans cause ✓ · pont Bilan limité au bouton existant ✓.

## Reste (lots suivants)
- **Lot C** : règle de stationnement réelle par type de projet (article/version/unité/exceptions/état) ;
  aujourd'hui l'étape 2 affiche la note « à vérifier » et le barème zone sert le contrôle.
- **Lot D** : lotissement = division-or sur l'assiette (les 4 types mappent encore collectif).
- **Lot E** : PDF depuis le même study_id (verrou chiffres), carte Docs, bilan surfacique clos.
