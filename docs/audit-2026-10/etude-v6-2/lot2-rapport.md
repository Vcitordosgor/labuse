# ÉTUDE V6-2 — Lot 2 : capacité stable + facteur limitant juste

## Le défaut constaté
- **Capacité instable** : le maximum « que le terrain accueille » dépendait de la DEMANDE. Deux demandes
  différentes sur Étang-Salé ne donnaient pas le même maximum (le pavage suivait la répartition de la
  demande), et selon la demande l'onglet « Optimisation » apparaissait (32) ou disparaissait.
- **Facteur limitant affirmé sans preuve** : « ce qui limite » était inféré des motifs des candidats
  écartés — une seule ligne, non chiffrée, et « le stationnement n'est pas le facteur limitant » pouvait
  être écrit sans jamais l'avoir vérifié.

## Le correctif

### (a) Capacité maximale STABLE, calculée une fois, la demande confrontée
- `moteur.capacite_maximale(terrain, regles, conv)` calcule le MAXIMUM de logements sous la **répartition
  équilibrée** des conventions (`[T2,T3,T2,T4,T2,T3]`) — **jamais** celle de la demande. C'est une
  propriété du terrain + des règles : **deux demandes différentes → le même maximum**.
- La demande est ensuite **confrontée** à ce maximum (`confrontation` : demande, maximum, tient, réserve),
  jamais un recalcul du maximum.
- Servi dans le payload : `capacite_maximale` + `confrontation`. Affiché dans un récit dédié « Capacité
  maximale du terrain » avec la mention « deux demandes différentes donnent le même maximum ».
- **Preuve Étang-Salé** : demande 10 T2 et demande 40 T2 (mêmes surfaces) → **capacité maximale = 28
  logements R+3, {T2:16, T3:8, T4:4}**, identique ; seule la confrontation change (10 tient, réserve 18 ;
  40 dépasse de 12).

### (b) Facteur limitant JUSTE, classé par impact, le stationnement PROUVÉ
- `moteur.facteurs_limitants(...)` renvoie une liste **classée par impact (logements perdus)** :
  1. **stationnement aérien** — impact **PROUVÉ par contrefactuel « sans places »** : on compare le
     maximum réel au maximum si l'on LÈVE les deux contrôles que le parking consomme (« Stationnement » +
     « Perméabilité (pleine terre) »). À Étang-Salé : **40 logements sans stationnement vs 28 avec → +12**,
     donc limitant. La mesure cite la surface occupée : **612 m² sur 1 746 m² d'assiette**. Vérifié : ce
     contrefactuel LU DANS LA MÊME recherche reproduit EXACTEMENT un 2ᵉ passage « cible = 0 place »
     (44 logts en répartition par défaut) — **sans recherche supplémentaire**.
  2. **hauteur réglementaire** — impact **estimé** (un niveau de plus ≈ 7 logements), R+3 au plafond 12 m ;
     non mesuré car il faudrait dépasser une règle.
  3. **largeur de la zone après reculs** — motif récurrent, **impact non chiffré**, donc **jamais marqué
     « limitant »**.
- Règle d'honnêteté : « le stationnement n'est pas le facteur limitant » n'est écrit **que si** le
  contrefactuel sans places n'ajoute **aucun** logement. Le 2ᵉ passage L151-35 (capacité réduite) ne se
  déclenche que si le stationnement est prouvé limitant.

## Performance (budget 30 s tenu, Saint-Denis inclus)
Le Lot 2 ajoute **UNE SEULE** recherche (la capacité maximale, répartition équilibrée) : le contrefactuel
stationnement est lu dans CETTE recherche (pas de 2ᵉ passage). Deux garde-fous :
- **grille de fractions grossière** (`_FRACTIONS_MAX`, 6 valeurs au lieu de 15) — le maximum est à grande
  fraction, donc résultat **identique** pour ~2× plus rapide ;
- **recherche BORNÉE dans le temps** : on lui passe une `deadline` = budget restant (30 s − écoulé −
  réserve planche 6 s), plafonnée à 9 s, en essayant **les étages hauts d'abord** (`niveaux_desc`) pour
  trouver le maximum avant une éventuelle coupure. En deçà de 3 s de budget → sautée (champ None, l'écran
  l'omet).
- Mesures : **Étang-Salé ≈ 13 s** (capacité calculée), **Saint-Denis + PPR ≈ 25 s** (capacité calculée, la
  recherche se coupe proprement). Avant garde-fous : Saint-Denis renvoyait **503 « étude trop lourde »**.

## Preuve
- Captures `captures/lot2-apres-capacite-facteurs.png` (récit « Capacité maximale » + facteurs classés).
- Deux demandes (10 T2 / 40 T2) → `capacite_maximale` identique (28), confrontation différente
  (10 tient réserve 18 ; 40 dépasse de 12).
- Facteurs classés : stationnement (−12, prouvé) > hauteur (−7, estimé) > largeur (non chiffré).
- **Saint-Denis (recette « rien n'a bougé ») : fonctionne toujours** (pas de 503) — capacité 12 R+3
  calculée en ≈ 25 s.

## Test unitaire
- `tests/test_etude_v6_capacite.py` (reel) : (1) capacité maximale STABLE entre deux demandes ; (2) le
  stationnement n'est limitant qu'après contrefactuel, facteurs classés par impact ; (3) un facteur
  d'impact 0 n'est jamais « limitant ».
- `EtudeV6.test.tsx` (Lot 2) : la capacité maximale stable + confrontation + facteurs classés par impact
  (stationnement en tête, prouvé) sont affichés.

## Vérifié
- **tsc 0 · vitest …/…** (EtudeV6 13/13). **pytest** capacité Lot 2. **chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.**
