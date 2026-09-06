# RETOURS-23 — COMPTE-RENDU (la fiche entière sur la grammaire)

Branche `fix/retours-22` (Z1 de RETOURS-20 déjà en place). **Un commit, rien mergé, rien poussé.**
Aucune app touchant au schéma de la base n'a été lancée (captures 100 % hors backend, cf. plus bas).
Présentation seulement : **la donnée ne change pas** — mêmes chiffres, libellés, sources, boutons.
Couleurs/police = variables de l'app, **aucun hex recopié de la maquette**.

## Préalable — Urbanisme : le constat (écrit avant de coder)

**Le bloc A BIEN été refondu** en RETOURS-20 : `ReglementPluBlock` (`Fiche.tsx`) rend déjà les règles
en **kicker « Règlement — zone X » + lignes de fait** (`FactRow`, valeur mono à droite, renvoi
d'article ↗). Vérifié dans le code (`Fiche.tsx`, `FactRow` présent).

**L'absence des six lignes (hauteur/emprise/reculs/pleine terre/stationnement) vient de la PARCELLE,
pas du code.** Cause précise : `src/labuse/plu_reglement.py:128` — `regles_valeurs` n'est peuplé que
`if (rules and rules.calibree)`. Les zones **A/N et les zonages non indexés (le Ub + ACU de la
recette)** n'ont pas d'articles indexés dans le corpus PLU → `regles_valeurs = []` → aucune ligne à
afficher (le code rend alors le repli « règlement non indexé », honnête). **Preuve que le chemin
fonctionne quand la zone est calibrée** : `config/plu_saint_paul.yaml` porte des zones U calibrées
(U1a : 16 m faîtage / 12 m égout / pleine terre 10 % ; U1b : 16/12 / 30 % ; U1c : 19/15 / 30 %…) →
sur une parcelle Saint-Paul en U, les six `FactRow` s'affichent, valeurs alignées à droite.

**Ce que Vic voyait « encore en paragraphes »** = les lignes de CASCADE du tiroir (Zonage, SDP
résiduelle, Surface, Parc national), rendues par la primitive `Line` (gauche, avec détail). RETOURS-23
les range sous un kicker **« Situation »** ; `Line` reste la forme « fait + détail » (le détail servi
est une phrase, pas un couple libellé/valeur — le réduire de force casserait la donnée).

## Les neuf sections sur les six composants (une ligne chacune)

1. **Règlement et zonage** — six règles en `FactRow` (déjà RETOURS-20) ; ajout du kicker « Situation »
   pour les faits de cascade ; `plu_fraicheur`/`aper`/`radar_procedure` dé-boxés (filet gauche).
2. **Constructibilité** — `TransformationBlock`/`BilanTab`/`RtaaBlock` dé-boxés (kickers + `FactRow` :
   SDP %, résiduelle m², TVA, QPV…) ; les 4 tuiles capacité gardées (maquette) ; **le calcul étape par
   étape** : boîte striée `card-elev` → filets, valeur mono à droite, badge `.b` sous la ligne.
3. **Risques et protections** — sous-titres → kickers ; pavé « ligne HT » → `Rappel` (sans bordure) ;
   les deux vigilances gardent la primitive `Line` (elles portent un `Trace`/drawer — donnée).
4. **Marché et secteur** — Terrain/Bâti/Dynamique en kickers ; chaque €/m², %, compte, VEFA, SITADEL,
   score en `FactRow` (même colonne droite) ; CTA sur `porte-outil` ; sparkline gardé.
5. **Réseaux et accès** — corrections : **Pente sous kicker « Terrain » + valeur à droite** ; en-tête
   ne répète plus l'opérateur (sous-titre = « eau · assainissement · élec ») ; **Axes et TCSP dé-cadrés**
   (fait à plat + note) ; gestionnaires/viabilisation déjà dé-boxés en RETOURS-20, pastilles standard.
6. **Autour de cette parcelle** — kickers ; revenu médian, parc social, habitants/ménages/% en
   `FactRow` ; 4 tuiles distances gardées ; tableau permis gardé (mono, < 100 m en vert) sans boîte.
7. **Dispositifs territoriaux** — boîtes (périmètre QPV mint, avertissement) supprimées ; chaque
   dispositif à plat (titre · détail · source en note) ; le périmètre fin garde un **filet gauche**
   mint (marqueur, pas un cadre).
8. **Propriétaire** — trois `card-elev` (PM DGFiP, personne physique, Radar bien) dé-boxés en
   kickers/notes ; `ProprietaireHistorique` et `CoproprietesBlock` dé-boxés (kicker + note).
9. **Données et méthode** — « Sources utilisées » → kicker ; les lignes source étaient déjà à plat.

## Ce qui a été gardé du SERVI contre la maquette
- **Pas de badge « Sourcé » fabriqué sur les règles PLU** (déjà tranché RETOURS-20) : le renvoi
  d'article ↗ EST la source ; `regles_valeurs` ne porte pas de champ de provenance.
- **Les vigilances Risques restent `Line`** (pas le composant `Vigilance` texte) : elles portent un
  `Trace`/drawer de couche — comportement = donnée, non retirable.
- **Les faits « Situation » d'Urbanisme restent `Line`** : leur `detail` servi est une phrase, pas un
  couple libellé/valeur ; « un contenu purement textuel reste une note ».
- **Transport public (arrêt/pôle/téléphérique), axe des deux faces, permis riches** : la maquette les
  raccourcit, le servi les garde en entier, re-dressés dans la grammaire.
- **La `Calculette foncière` (outil via `porte-outil`) n'est pas touchée** : c'est un module d'outil
  séparé, pas une section de la fiche.
- Parcelle de démonstration = **zone U calibrée** (règlement complet, six lignes visibles), U1b/601 m².

## Captures — neuf sections dépliées, 400 px, SANS backend
Harness statique `frontend/qa/retours23_harness.html` + CSS **réel compilé** de l'app
(`dist/assets/index-*.css` → tokens + `.fiche-v6`), rendu par `frontend/qa/retours23_shots.mjs`
(Playwright, Chrome système, `file://`, 400 px, ×2). Sortie :
`docs/audit-2026-09/RETOURS-23/captures/00-panneau-complet.png` + `01-reglement…09-donnees.png`.

## Vérification
`npx tsc -b` : **0 erreur**. `npx vite build` : **OK**. Refactor mené en partie par sous-agents
(un par fichier de section indépendant, consigne stricte « présentation seulement ») ; intégration,
revue de fidélité-donnée (chaque expression `f.*` retirée est ré-exprimée), build et git faits ici.
Aucun backend, aucune base touchée.

## Fichiers
- Sections : `constructibilite.tsx`, `risques.tsx`, `marche.tsx`, `MarcheSecteurBlock.tsx`,
  `autour.tsx`, `AutourZoneBlock.tsx`, `PermitsProximityBlock.tsx`, `DepotsBlock.tsx`, `reseaux.tsx`.
- Sous-blocs : `GestionnairesBlock.tsx` / `ViabilisationBlock.tsx` (compléments), `CoproprietesBlock.tsx`,
  `ProprietaireHistorique.tsx`.
- `Fiche.tsx` — drawers Urbanisme (kicker Situation), Dispositifs, Propriétaire, Données dé-boxés.
- `frontend/qa/retours23_harness.html`, `frontend/qa/retours23_shots.mjs` + captures.

## Arrêt
Les neuf sections sont sur la grammaire. Rien mergé, rien poussé.
