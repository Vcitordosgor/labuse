# SPEC — FILTRE CLIENT BÂTI (dette #4-connues) — RÉDACTION SEULE, Vic lit avant tout code

## Principe acté (note d'architecture, prouvée par la mesure piscine)
« Le modèle prédit la mutation, il ne juge pas l'état de la parcelle. Tout ce qui relève de
l'état (bâti, zone, statut) est une règle explicite, jamais un poids. » Le filtre est donc une
RÈGLE PRODUIT à trois étages, jamais un signal du modèle.

## La hiérarchie (dans l'ordre d'évaluation)
1. **Ratio bâti/surface** (emprise max(BD TOPO, CoSIA) / surface parcelle) :
   - < 15 % → « bâti marginal » : SERVIE sans restriction (annexe/abri sur grand terrain) ;
   - 15-40 % → étage 2 (l'année et la divisibilité tranchent) ;
   - > 40 % → « bâtie saturée » : hors tête par défaut (tier dédié ou badge, à arbitrer).
2. **Année de construction** (DPE/BDNB quand dispo — étiquette Sourcé ; sinon Absent, jamais
   inventée) : bâti < 10 ans → durcit (peu de chance de démolition/mutation du bâti) ;
   bâti ancien/passoire (DPE F-G) → assouplit (potentiel de renouvellement, lien segment).
3. **Divisibilité** (lien O12) : surface libre = surface − emprise×coeff_recul ; si la partie
   libre passe seule le plancher local (≥ 600 m² U/AU ou SDP résiduelle recalculée > 0) →
   « divisible » : SERVIE avec badge « division possible » au lieu d'être filtrée.

## Où le client agit
Option « inclure le bâti » (3 états : masquer / badge / tout voir). **Défaut à arbitrer** —
proposition : badge visible, pas de masquage (doctrine « tout montrer, motiver »).

## Ce que la fiche affiche pour une bâtie servie
Badge « bâtie — ratio N % (source, date) » + la ligne divisibilité si applicable + la SDP
avec sa mention (terrain nu théorique tant que le recalcul train 6 n'est pas passé).

## Cas de calibrage (mesurés, sessions 04/08)
AR1511 24,6 % (le max brûlante — étage 2, sort ou badge selon année) · les 8 brûlantes
connues (7,6-24,6 %) · les 432 chaudes (41 % de la tête). Toute implémentation commence par
une mesure à blanc sur ces trois populations + cartes des mouvements en tête.

## Non-buts
Pas de déclassement aveugle ; pas de poids modèle ; pas d'application avant arbitrage de la
spec puis mesure à blanc + point d'arrêt.
