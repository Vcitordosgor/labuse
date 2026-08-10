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

CC ne merge jamais.
