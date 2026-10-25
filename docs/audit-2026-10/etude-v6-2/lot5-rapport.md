# ÉTUDE V6-2 — Lot 5 : écrans

## 1. Étape 1 — champ de recherche vidé après ajout
Le champ `ParcelInput` est **remonté par une clé** (`key={sel.length}`) : à chaque parcelle ajoutée, le
champ repart **vide**, prêt pour la suivante (plus de référence résiduelle à effacer à la main).

## 2. Étape 1 — règles PLU par parcelle (citées)
`valider_parcelles` sert désormais, pour CHAQUE parcelle, le **résumé des règles PLU de sa zone**
(`regles_plu`) : hauteur à l'égout / faîtage, emprise au sol (CES), reculs voie & séparatives, pleine
terre, et — là où calibrés — espaces verts & marge plantée. Chaque règle est **chiffrée et citée**
(article + page), chargée depuis le calibrage (caché par zone, rapide). Affichées en chips sous chaque
parcelle. Seules les règles **validées** apparaissent (jamais « non vérifié » servi comme une valeur).
Étang-Salé UA : Hauteur 12 m (UA 2.5.2) · CES 70 % (UA 2.4) · Recul voie 4 m (UA 2.1) · séparatives 3 m
(UA 2.2) · Pleine terre 30 % (UA 2.6) · Espaces verts 20 % (UA 2.6) · Marge plantée 2 m (UA 2.6).

## 3. Récap — « — » tant que non choisi (jamais 0 ni « Non vérifié »)
Le récapitulatif affiche **« — »** pour toute donnée non encore renseignée (terrain, projet, logements,
surface, stationnement) : un tiret dit « pas encore renseigné », pas « 0 » (qui ferait croire à une
valeur) ni « Non vérifié » (qui ferait croire à un problème). La ligne stationnement affiche la règle PLU
dès que le type est choisi (l'état du régime servi), « — » avant.

## 4. Bandeaux bas de page supprimés (3 étapes)
Le bandeau descriptif en bas de chaque étape (titre + phrase pédagogique) est **supprimé** : il ne reste
que la barre d'action **Retour / Continuer / Analyser**, plus le feedback FONCTIONNEL minimal (raison d'un
blocage, « Calcul en cours, jusqu'à une minute », erreur d'analyse).

## Tests
- `EtudeV6.test.tsx` (Lot 5) : règles PLU par parcelle citées + champ vidé + absence du bandeau ;
  récap « — » (jamais 0 / « Non vérifié »). (Test étape 2 « À choisir » → « — » mis à jour.)
- `tests/test_etude_v6_capacite.py::test_regles_plu_par_parcelle` (reel) : UA sert hauteur/CES/reculs/
  pleine terre + espaces verts/marge, chiffrés et cités.

## Vérifié
tsc 0 · vitest 298/298 (EtudeV6 20/20) · pytest implantation · chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.
Capture `captures/lot5-etape1-regles-plu-recap.png`.
