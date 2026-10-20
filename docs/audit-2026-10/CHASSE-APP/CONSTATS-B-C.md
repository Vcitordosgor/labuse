# CHASSE-APP-FIX-1 — constats B et C (non corrigés, avec justification)

## B — « Une commune tapée sert de filtre, pas de texte à chercher » → NON TRAITÉ (décision Vic)

Reproduit : dans la barre de recherche (en-tête, grammaires `adresse,cadastre,proprietaire,siren,lieu_dit`),
taper « saint-leu » fait remonter des adresses quelconques de la commune
(`7 Stella`, `11 Stella`, `127 L'Etang`…), parce que `_sugg_adresse` (`src/labuse/api/recherche.py`)
matche chaque jeton contre une colonne qui **inclut la commune** (numéro+rep+voie+CP+commune).

Nuances relevées avant toute correction :
- Dans l'en-tête, la grammaire « commune » a **déjà** été retirée (décision Vic RECETTE-2 S5,
  `Header.tsx:166`) : le cadrage commune passe par le sélecteur « Toute l'île ».
- Faire de la commune un **filtre** dans `_sugg_adresse` toucherait une mécanique **déjà décidée**
  (RECHERCHE-2 Lot 3a : « 27 chemin vidot saint denis » utilise « saint/denis » pour cadrer).

**Décision Vic (20/10)** : laisser tel quel — la commune reste un mot de recherche. B vise
probablement un autre écran que la barre de recherche. **Aucune modification.**

## C — « Sur /flash, la liste de suggestions s'affiche sous le champ » → DÉJÀ RÉGLÉ EN CODE

La page `/flash` est rendue côté serveur (`src/labuse/api/onboarding.py`). Le menu de suggestions
`#q-sugg` est positionné `position:absolute; left:0; right:0; top:calc(100% + 4px)` dans un `.field`
en `position:relative` → il s'affiche **sous le champ**.

Vérifié en local (capture `captures/C-flash-sugg-etat.png`) : en tapant « chemin dubuisson »,
les suggestions apparaissent bien directement sous le champ.

Ce positionnement a été introduit le **9 oct** (commit `2216879d`, CORRECTIFS-1 Lot A), soit **avant**
la chasse du 19/10. Le constat de la chasse s'explique donc très probablement par une **prod pas
encore à jour de ce build** (le déploiement est un geste de Vic). **Aucune correction au hasard.**
