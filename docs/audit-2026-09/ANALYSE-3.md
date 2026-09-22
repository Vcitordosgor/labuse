# ANALYSE-3 — Densifier l'écran Analyse (en-tête, filtres, ligne de résultats)

Branche `feat/analyse-1` (à la suite de `f0caef87`, worktree `labuse-analyse`, ports 8145/5345). Non mergé. Aucun changement de moteur, de score ni de données.

Objectif unique : **le même écran, beaucoup moins haut** (colonne qui bouffait trop d'espace avant la première carte). Règle de preuve : un point n'est corrigé qu'après constat à l'écran. Captures : `captures/analyse3/`.

## 0. Étape 0 — VERTE
`pwd` = worktree `labuse-analyse`, branche `feat/analyse-1`, HEAD `f0caef87`, arbre propre (hors `circuit-sources1` non lié).

---

## 5. Mesure (donnée en premier, c'est le but)
Hauteur du **haut du bandeau à la première carte**, à **largeur de colonne identique** (viewport 1280×900 → colonne **307 px**) :

| | Hauteur en-tête→1re carte |
|---|---:|
| **AVANT** (`00-avant.png`) | **473 px** |
| **APRÈS** (`02-apres-puces.png`) | **254 px** |
| **Gagné** | **219 px** ✓ (objectif ≥ 200) |

Le bandeau lui-même passe de ~150 px à **35 px** (une ligne).

---

## 1. En-tête — une seule ligne — FAIT (`02-apres-puces.png`)
`LeftPanel.tsx` : le bandeau tient sur **une ligne** (~35 px), bloc arrondi teinté :
`✓ Analyse LABUSE` (à gauche) · bouton **Comprendre** avec l'icône **i** · bouton **Retour** (à droite).
- Le nom de la commune (`analyseRecap`) est **retiré** (doublon des filtres globaux + des cartes).
- Le mot « **affichée** » est retiré (« ✓ Analyse LABUSE » seul).
- Le bouton passe de « Comprendre l'analyse » (pleine largeur) à **Comprendre** (pastille en ligne, icône i). Le panneau qu'il ouvre est **inchangé** (hors mandat).
- Le titre de section « **RÉSULTATS** » est **retiré** en mode analyse (`ResultsSection.tsx`) — vérifié : `hasResultsTitle = false`.

---

## 2. Les deux filtres — un bloc, deux lignes serrées — FAIT (`02-apres-puces.png`, `03-filtres-excellente.png`)
Un seul bloc `surface-1`, deux lignes :
- Ligne 1 : libellé **Classement** à gauche (largeur fixe, 11 px, `text-secondary`) puis les 5 puces : Excellente · Bonne · À étudier · Faible · **Tous**.
- Ligne 2 : libellé **Signal** à gauche, puis Fort · Moyen · Faible · **Tous**.

Règles respectées : puces de largeur égale (`flex-1`), **« Tous » plus étroite et toujours en dernier**, **le compteur est DANS la puce**, la rangée ne wrappe **jamais** (une seule ligne par groupe), actif = **vert opaque**, survol = opaque de sa couleur. Les titres en capitales « CLASSEMENT LABUSE » et « SIGNAL DE MUTATION » sont retirés. Les compteurs viennent du **crosstab déjà en place** (`bandes_signal`) : Saint-Paul → Classement 615 / 4 366 / 6 404 / 11 245 (Σ = 22 630) ; Signal 9 / 55 / 22 566 (Σ = 22 630). Mêmes chiffres qu'avant, déplacés.

**Bonus vérifié** : les compteurs de puce sont **cross-filtrés** — sélectionner Classement = Excellente met à jour les puces Signal (Fort 2 · Moyen 5 · Faible 608 = 615). Sur l'état par défaut (Tous/Tous), les puces Classement affichent bien les totaux de bande (les « chiffres d'aujourd'hui » déplacés).

**Décision de rendu (à valider Vic)** : « une seule ligne par groupe » a été lu comme « la **rangée** ne wrappe pas » ; à 307 px de colonne, « Excellente 615 » **en une ligne inline** ne rentre pas (5 puces + libellé de gauche) et se tronquait en « E… ». Les puces sont donc **sur 2 lignes internes** (libellé au-dessus, compteur en dessous) pour garder le **compteur lisible à toute largeur**. Le libellé se tronque encore (« Ex… », « À é… ») aux colonnes étroites (307 px) ; il est lisible en entier au survol (title) et identifié par la couleur/position. Options si Vic préfère : libellés courts dans les puces (« Excel. », « À étud. »), ou retirer le libellé de gauche pour élargir les puces.

---

## 3. Encart de synthèse — allégé — FAIT (`02-apres-puces.png`)
L'encart ne garde que la **phrase** « LABUSE a analysé les N parcelles de votre sélection » et la **barre colorée** (5 segments = 4 bandes + Non retenue, teintes `BANDE_META`). Les **5 pastilles chiffrées sont retirées** (elles sont passées dans les puces du filtre Classement). La barre porte le détail au survol (Tip par segment).

---

## 4. Ligne de résultats — FAIT (`02-apres-puces.png`)
« **Trier par potentiel** » est **retiré** (l'ordre est fixe, le libellé ne servait à rien et débordait sur deux lignes). La ligne garde uniquement « **N parcelles correspondent à vos filtres** », sur une seule ligne (`truncate`).

---

## Portes
- `tsc -b` : **vert**.
- `vitest run` : 177 passés, **3 échecs PRÉ-EXISTANTS** (`admin/circuit/Detail.test.tsx` ×2, `admin/Donnees.test.tsx` snapshot), 0 nouveau.
- Aucun test back touché (front pur, layout ; le crosstab `bandes_signal` était déjà servi).
- Navigateur : structure, mesure avant/après, filtres fonctionnels + cross-filtrés — vérifiés à l'écran.

## Hors mandat (non touché)
Le contenu du panneau « Comprendre » · le moteur, les bandes, les compteurs eux-mêmes · les cartes parcelle · les filtres globaux · merge · bascule.

## Reste à trancher Vic
1. **Rendu des puces à 2 lignes** vs « Excellente 615 » inline (impossible à 307 px sans troncature) — cf. §2. Choisir : 2 lignes (actuel), libellés courts, ou colonne élargie.
2. Troncature des libellés de bande aux colonnes étroites — acceptée (compteur + couleur + survol), à confirmer.
