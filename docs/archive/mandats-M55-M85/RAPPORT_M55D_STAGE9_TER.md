# RAPPORT M55-D stage 9 ter — texte d'accueil final + fiches commune au menu

Branche `feat/m55-d-stage9-ter` (base `main` dd3dfd34, **blocs 3+4 mergés — précondition
vérifiée**). Un commit par point. tsc 0, build vert.

## 1 · Le texte d'accueil final (figé Vic, 10/08) — commit 164a9742
La page = **deux blocs et le lien, rien d'autre** :
- « **LABUSE, c'est tout le foncier de La Réunion. Au même endroit.** » — 431 663 parcelles ·
  24 communes · 52 sources publiques branchées — cadastre, PLU, permis, ventes, risques,
  procédures BODACC. Chaque donnée porte sa date — toujours la plus fraîche disponible.
- « **Et c'est un copilote IA qui mâche le travail.** » — Il répond, explique chaque parcelle
  et vous accompagne partout dans l'app — chiffres sourcés à l'appui.
- [Commencer →]

Règles tenues : textes dans `strings.ts` (zéro chaîne en dur au JSX) · les 3 chiffres restent
**servis par `/accueil/chiffres`** (dynamiques, « i » sourcé chacun, null = masqué) · anciens
blocs/intro/doctrine **retirés** avec leurs chaînes (le bloc `CLIENT.accueil` est réécrit ;
`accrocheOn/Off` orphelines du stage 4 nettoyées au passage) · « Commencer → » inchangé
(ouvre Filtres, **accordéon stage 9 respecté — prouvé** : filtres ouvrent, couches ferment) ·
l'endpoint garde ses 12 mesures.

**Validation** : titres figés 2/2 ✓ · chiffres affichés == endpoint (3/3) ✓ · anciens blocs
absents ✓ · l'accueil disparaît après « Commencer » ✓ · mobile ✓. Captures `ter_accueil`,
`ter_accueil_mobile`.

## 2 · Le menu périmètre retrouve ses fiches commune — commit 712385d2
Chaque ligne du menu déroulant porte à droite un **« ⓘ »** (zone de clic 28 px,
`stopPropagation`) : le **nom** sélectionne (zoom + pré-coche, bloc 3 inchangé) ; le **ⓘ**
ouvre la fiche de cette commune **sans changer le périmètre**. « Contexte » conservé tel quel.

**Validation prouvée** : clic ⓘ Saint-Leu → fiche ouverte, périmètre resté « Toute l'île » ·
clic nom Saint-Leu → zoom 11,9 + périmètre « Saint-Leu », fiche NON ouverte · capture
`ter_menu_i`.

## Ajustements Vic (sur captures) — commits suivants
- **Accueil** : « Commencer → » en PLEIN/mint/gros (style « Analyser les parcelles »), placé en
  premier — LE geste de la page ; bloc copilote IA RETIRÉ entier (chaînes 0-caller) ; texte
  restant en soutien (titre sobre, chiffres+« i » en corps réduit, phrase descriptive discrète).
  Captures `ter_accueil` (avant) / `ter_accueil_apres`.
- **Menu périmètre** : le « ⓘ » corrigé en **lien texte d'origine** (pattern M55-C) « voir la
  fiche → » — nom = sélection (zoom + pré-coche) ; lien = fiche SANS changer le périmètre
  (prouvé : fiche + « Toute l'île » inchangé ; 24 liens, 0 ⓘ). Capture `ter_menu_lien`.
- **Chevrons de section** : composant UNIQUE `ChevronSection` calibré sur la croix ✕ (même boîte
  h-7 w-7 rounded-md, même colonne, hover fond léger, glyphe 17 px centré optiquement, rotation
  douce) — appliqué à Couches, Filtres, tiroirs internes (variante `petit`) et légende Verdict ;
  la croix desktop boxée pareil. Plus aucun chevron « nu » (seul le « pourquoi ? ⌄ » inline de la
  liste reste tel quel : dépliant dans une phrase, pas un chevron de section). Captures
  `chevrons_avant` / `chevrons_apres(+hover)`.

CC ne merge jamais.
