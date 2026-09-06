# MANDAT RETOURS-20 — fiche parcelle : refonte visuelle des accordéons

**Branche** : `fix/retours-12`. Un commit (front seul). Étape 0 : `pwd`, branche, arbre propre — sinon arrêt. Aucun sous-agent sur git, aucun `git add -A`, aucun merge.
**Origine** : Vic, 06/09 — « l'alignement est mauvais, les titres, le gras, les espacements, les types de sections. Refais visuellement tout ce qu'il y a dans les accordéons. Change rien à la donnée. »
**Référence** : `docs/audit-2026-09/RETOURS-20/maquette-fiche-parcelle-accordeons.html` — les 9 accordéons redessinés avec la donnée réelle d'une parcelle (601 m², U6c, Saint-Paul), et une colonne « grammaire » qui décrit les six blocs. Ouvrir dans un navigateur avant d'écrire une ligne.

## Ce que la maquette fixe, et ce qu'elle ne fixe pas
- **Elle fixe** : la structure, les six blocs, les espacements (padding 14 px, filets, gaps), la hiérarchie de texte (14 / 13 / 12,5 / 11,5 / 10,5 mono), l'alignement des valeurs à droite, la place des sources, la taille unique des badges, la position des actions en bas de section.
- **Elle ne fixe pas** : les couleurs ni les polices. Ses hex sont des approximations à l'œil. Le code utilise **les variables déjà en place** (`--mint`, mauve IA, ambre, gris de l'app, police de l'app). Aucune valeur de couleur recopiée depuis le fichier.
- **La donnée ne bouge pas** : mêmes chiffres, mêmes libellés, mêmes sources, mêmes CTA. Si un texte de la maquette diffère du texte servi (raccourci pour la place), c'est le texte servi qui reste.

## Z1 — Six blocs, un seul composant chacun
Construire (ou aligner s'ils existent) six composants partagés, utilisés par **tous** les accordéons de la fiche :
1. **En-tête** : icône 30 px · titre 14/500 · sous-titre 12 secondaire · à droite **un seul objet** (chiffre clé en mono, ou chip d'état) · chevron.
2. **Kicker** : ligne mono 10,5 px capitales, filet au-dessus (sauf le premier). C'est **le seul séparateur** de sous-section — plus de boîte dans la boîte.
3. **Ligne de fait** : libellé à gauche en secondaire · valeur à droite en mono, chiffres tabulaires, unité en petit · source sur la ligne du dessous en 11,5 px avec son badge. Filet entre les lignes. Une valeur absente ou inconnue s'affiche en gris atténué (« inconnu », « non renseigné »), une valeur qui appelle une vérification en ambre.
4. **Badges** : trois seulement — Sourcé, Estimé, Dérivé — même taille partout (mono 10 px, contour). Les renvois d'article sont des liens mono avec ↗.
5. **Vigilance** (filet ambre à gauche, pas de boîte) et **rappel** (fond un cran plus clair, sans bordure).
6. **Action** : icône carrée 32 px · titre 13/500 · description 11,5 · flèche ; empilées en bas de section avec 6 px d'écart ; survol vert opaque (ambre pour Projet, mauve pour l'IA — règle Y2).

## Z2 — Deux sections d'abord, puis STOP
**Ne pas refaire les neuf accordéons dans cette session.** Passer sur les nouveaux blocs **deux sections seulement** :
1. **Règlement et zonage** — la plus dense en lignes de fait, elle valide la ligne de fait, les badges et les renvois d'article.
2. **Réseaux et accès** — la plus dense en paragraphes, elle valide les notes 11,5 px, les rappels et le passage des phrases en lignes.

Puis **s'arrêter, commiter, et rendre les captures avant/après de ces deux sections**. Vic regarde et décide si les sept restantes suivent. Les sept autres feront l'objet d'un mandat de suite (RETOURS-21) — ne pas les anticiper, ne pas les « préparer ».

Pour les deux sections traitées, suivre la maquette section par section. Points particuliers pour la suite (à ne pas traiter maintenant, ils décrivent les sept autres) :
- **Constructibilité** : la capacité en quatre tuiles (gabarit, SDP, logements, SHAB) ; le calcul en liste numérotée sobre, badge sur chaque ligne, sans tableau.
- **Autour de cette parcelle** : les quatre distances en tuiles ; les permis en lignes mono à quatre colonnes (type · date · logements · distance), distances < 100 m en vert.
- **Données et méthode** : les 27 sources en trois colonnes (nom · producteur · état), une ligne par source, sans boîte.
- Les paragraphes de méthode passent en **note 11,5 px** sous la ligne concernée ; ils ne sont plus des paragraphes pleins.

## Z4 — Deux reports de RETOURS-19 (à traiter dans cette session)
- **Barre de défilement de la Veille** : la règle Y4 (pouce vert au survol) n'a pas été appliquée au panneau Veille. L'appliquer, et vérifier qu'aucun autre panneau n'a été oublié.
- **Icônes des accordéons de la fiche parcelle** : au survol, même traitement que les quatre icônes de l'accueil — **contour noir, fond vert, glyphe noir**. Aujourd'hui les tuiles de la fiche gardent leur fond sombre sur la barre verte. Ce traitement devient celui du bloc « en-tête » de Z1, donc il vaut pour les neuf accordéons, pas seulement les deux traités.

## Z3 — Ce qui disparaît (dans les deux sections traitées)
Boîtes imbriquées à bordures différentes · plus de quatre tailles de texte dans une section · sources collées en fin de phrase · valeurs en milieu de ligne · chips de tailles différentes pour la même information.

## Livraison
Captures avant/après des DEUX sections traitées, à la largeur réelle du panneau. `docs/audit-2026-09/RETOURS-20/COMPTE-RENDU.md` : les six composants (fichier), les endroits où le texte servi diffère de la maquette et ce qui a été gardé.

- [ ] Z1 — six composants partagés, un par bloc
- [ ] Z2 — DEUX sections passées dessus (Règlement et zonage · Réseaux et accès), donnée inchangée, arrêt ensuite
- [ ] Z3 — boîtes imbriquées et tailles de texte surnuméraires retirées
- [ ] Z4 — scrollbar de la Veille au vert ; icônes d'accordéon en fond vert / contour et glyphe noirs au survol

## Prompt de lancement (depuis `~/Desktop/labuse`)
> Étape 0 : `pwd`, branche `fix/retours-12`, arbre propre. Sinon arrête-toi sans rien écrire.
> Lis `docs/audit-2026-09/RETOURS-20/MANDAT-RETOURS-20.md` et ouvre la maquette HTML qu'il référence. La maquette fixe la structure et les espacements ; les couleurs et polices viennent des variables existantes de l'app, aucun hex recopié. La donnée ne change pas. Z4 d'abord (scrollbar Veille, icônes d'accordéon), puis Z1, puis Z2 sur DEUX sections seulement (Règlement et zonage, Réseaux et accès), puis Z3 sur ces deux-là. Arrête-toi ensuite : les sept autres sections attendent la validation de Vic. Un commit. Captures avant/après des deux sections. Aucun sous-agent sur git, aucun `git add -A`, aucun merge.
