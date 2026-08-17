# AUDIT M105-B — les contrastes de la vue claire : mesures, STOP

Mesuré le 2026-08-17 (luminance relative WCAG ; composite alpha exact de chaque aplat sur
chaque fond réel). **Aucune correction — Vic arbitre les valeurs cibles, la DA se valide à
l'œil sur captures en Phase 2.**

## 1. Le fond clair réel (sur quoi les couches se posent)

Le mode clair M65 est une inversion figure/fond, PAS un fond de tuiles : trois teintes
seulement (MapView `applyClairMode` + effet palette :853-856) :

| fond | teinte | où |
|---|---|---|
| terre parcellisée | `#F4F2EC` (blanc cassé, opaque) | tout le littoral urbanisé — LE fond dominant sous les couches |
| masse île non parcellisée | `#C9C4B8` (gris) | cirques, forêt, volcan |
| mer | `#060A08` (noir — ne bouge jamais) | hors terre ; aucune couche d'information ne s'y pose |

Pas de bâti ni de routes en teintes propres : les couches se jouent sur DEUX fonds clairs
de luminance voisine (L≈0,88 et 0,58). Une valeur qui passe sur la terre passe presque
toujours sur la masse — le couple à viser est la terre (`#F4F2EC`), la masse en contrôle.

## 2. Le contraste chiffré (état actuel)

**Critère proposé (chiffré et assumé, à arbitrer)** : un APLAT d'information est
« distinguable » à ratio composite/fond **≥ 1,25:1** ET porte un CONTOUR de sa teinte à
**≥ 3:1** (le seuil non-texte WCAG s'applique au trait, pas à l'aplat — c'est le contour
qui garantit la lecture, l'aplat qui colore sans masquer le fond). Un TRAIT seul vise
**≥ 3:1**.

| élément | valeur actuelle | composite sur terre | ratio terre | ratio masse | verdict |
|---|---|---|---|---|---|
| zonage U (la couche la plus consultée) | `#5CE6A1` @ 0,10 | `#E5F1E4` | **1,04** | 1,00 | invisible au sens strict |
| zonage non-U | `#8A6B3F` @ 0,10 | `#E9E4DB` | 1,13 | 1,10 | insuffisant |
| PPR | `#E8695A` @ 0,14 | `#F2DFD8` | 1,15 | 1,10 | insuffisant |
| ANRU | `#C6E82E` @ 0,30 | `#E6EFB3` | 1,08 | 1,06 | insuffisant (calibrée fond sombre) |
| Parc | `#8B5A2B` @ 0,22 | `#DDD1C2` | 1,34 | 1,26 | **OK** (confirme M105) |
| tier brûlante (aplat 0,95) | `#E8695A` | — | 2,70 | 1,79 | OK terre, moyen masse |
| tier chaude (0,90) | `#E8B44C` | — | 1,61 | **1,08** | insuffisant |
| tier réserve (0,55) | `#6FA8DC` | — | 1,54 | 1,23 | limite |
| tier à creuser (0,45) | `#8FA69A` | — | 1,41 | 1,20 | limite |
| contour tier brûlante 0,6 px | `#E8695A` | — | 2,84 | 1,83 | sous 3:1 |
| contour tier chaude 0,6 px | `#E8B44C` | — | **1,70** | 1,09 | insuffisant |
| trait de côte 2,2 px | `#4ADE80` | — | 1,56 | **1,00** | invisible sur la masse — son fond principal |
| limites parcelles (noir M105) | `#000000` | — | 18,8 | 12,1 | OK |
| limites communes | `#2E7D52` | — | 4,50 | 2,89 | OK terre, limite masse |

## 3. Ce qui doit rester distinguable ENTRE couches

Mesure décisive : sur la terre claire, les composites d'aplats sont tous dans la même
bande de luminance — **zonage U vs PPR 1,10 · zonage U vs ANRU 1,04 · PPR vs ANRU 1,06**.
Même en corrigeant les opacités (candidats §5), la différenciation inter-couches par
l'APLAT reste ≈ 1,1 : **c'est le CONTOUR (teinte identitaire saturée) et la TRAME qui
doivent différencier les couches actives ensemble, pas l'aplat.** Combinaisons
fréquentes à garantir : zonage + PPR (instruire un terrain), zonage + tiers (la carte par
défaut filtrée), PPR + 50 pas (littoral).

## 4. Daltonisme (où une seconde variable est nécessaire)

- **zonage U (vert) vs ANRU (chartreuse)** : quasi confondus en deutéranopie — l'ANRU
  devrait porter une TRAME (hachures) en plus de sa teinte.
- **PPR (rouge) vs Parc (brun) vs tier brûlante (rouge)** : proches en protanopie — le
  PPR, réglementaire, mérite le contour le plus fort et/ou une trame ; le Parc garde son
  aplat plein (jamais superposé au PPR en pratique — bordure Parc déjà distincte).
- **tiers chaude (ambre) vs à creuser (gris-vert)** : distinguables par luminance ✓.
- Règle générale proposée : toute couche RÉGLEMENTAIRE superposable (PPR, 50 pas, SUP)
  porte trame + contour ; les couches d'ambiance (zonage, potentiel) restent aplat+contour.

## 5. Candidats chiffrés pour l'arbitrage (teintes identitaires conservées)

Le mint CANON de la DA (`#1E9E58`, M73-G) atteint 3,08:1 sur la terre claire — il peut
porter contours et trait de côte SANS sortir de la marque.

| élément | candidat | composite terre | ratio aplat | ratio contour/trait |
|---|---|---|---|---|
| zonage U | `#1E9E58` @ 0,22 + contour `#1E9E58` 1 px | `#C5E0CB` | 1,26 ✓ | 3,08 ✓ |
| PPR | `#D14432` @ 0,20 + contour + trame | `#EDCFC7` | 1,31 ✓ | 4,09 ✓ |
| ANRU | `#8FA818` @ 0,30 + trame | `#D6DCAC` | 1,28 ✓ | 2,41 (trame compense) |
| trait de côte | `#1E9E58` 2,2 px | — | — | 3,08 terre / 1,98 masse (épaissir à 3 px ou liseré blanc) |
| contour tier chaude | ambre foncé `#C68A1B` | — | — | 2,66 (à pousser ou doubler d'un liseré) |

Ces candidats respectent les interdits : teintes identitaires conservées (vert reste
vert, rouge reste rouge, chartreuse reste chartreuse), mauve intact (IA), `#F5C518`
intact (Pages Jaunes), vue sombre intouchée. La Phase 2 posera les valeurs ARBITRÉES
dans un jeu de tokens par thème (un thème, un jeu de valeurs — pas de conditions
éparpillées), zonage U en premier.

**STOP — Vic arbitre les valeurs cibles sur ces mesures ; validation à l'œil sur
captures en Phase 2.** *(Arbitrage rendu le 17/08 : critère validé, doctrine
contour+trame retenue, les 3 candidats retenus, même traitement aux éléments
restants, priorité zonage U puis trait de côte. Phases 2-3 ci-dessous.)*

---

# PHASES 2-3 — livraison et vérification (17/08/2026)

## 6. Phase 2 — le jeu de tokens par thème

`frontend/src/lib/mapTheme.ts` = LE jeu de tokens par thème (colonne `sombre` =
littéraux historiques verbatim, mêmes sources que la légende ; colonne `clair` =
valeurs arbitrées). Consommé à la création des couches et par `applyClairMode`
(un seul point de bascule — aucune condition éparpillée). Nouvelles couches :
`ov-zonage-line`/`ov-ppr-line` (+ jumelles MVT — largeur 0 en Sombre, 1 px en
Clair) et `ov-anru-trame` (motif diagonal canvas, opacité 0 en Sombre).

| élément | clair livré | aplat mesuré | contour/trait mesuré |
|---|---|---|---|
| zonage U | `#1E9E58` @ 0,22 + contour | 1,26 ✓ | 3,08 ✓ |
| zonage non-U | `#6E4F27` @ 0,22 + contour | 1,39 ✓ | 6,67 ✓ |
| PPR | `#D14432` @ 0,20 + contour | 1,31 ✓ | 4,09 ✓ |
| ANRU | `#8FA818` @ 0,30 + trame | 1,28 ✓ | 2,41 — la trame compense (arbitré) |
| 50 pas | `#1777A3` @ 0,20 + tireté | 1,30 ✓ | 4,46 ✓ |
| trait de côte | `#14713E` 2,2 px | — | 3,49 ✓ sur la masse (était 1,00) |
| contour tier brûlante | `#C23A28` | — | 4,77 ✓ |
| contour tier chaude | `#A8720F` | — | 3,69 ✓ |
| liseré brûlantes | `#C1440E` | — | 4,57 ✓ |

Conformes SANS changement (critère aplat ≥ 1,25 déjà atteint, mesuré) : Parc 1,34 ·
AU (fill famille @ 0,55) 1,89 · réserve foncière 1,54 · à creuser 1,41. Aucune
teinte réattribuée : vert reste vert, rouge reste rouge, chartreuse reste
chartreuse, cyan reste cyan.

## 7. DÉCOUVERTE de la vérification pixel (Phase 3) — le recouvrement

La première salve de captures a RENVERSÉ un implicite de la Phase 1 : l'aplat
corrigé ne rendait QUE sur la masse non parcellisée (`#A3BCA3` mesuré au pixel =
composite exact sur gris) et **pas du tout sur la terre parcellisée** — en Clair,
le remplissage des parcelles est OPAQUE (`#F4F2EC` @ 1) et l'ordre de création le
peignait AU-DESSUS des couches d'information (et des limites communes). La Phase 1
avait mesuré le composite mathématique « couche sur fond » ; le rendu réel
empilait « fond sur couche ». Correction : en Clair, les 4 remplissages
parcellaires descendent sous le bloc d'information (`moveLayer`, dans
`applyClairMode`) — limites noires, sélections et étiquettes restent au-dessus ;
en Sombre, l'ordre d'origine est RESTAURÉ.

## 8. Vérification au pixel (captures servies, pas la théorie)

Sur les captures (`qa/m105b/captures.mjs`, 19 vues clair+sombre, seul +
combinaisons, Saint-Paul puis Le Port) les composites SERVIS sont EXACTS au
calcul : U sur terre `#C5E0CB` (8 953 px) · non-U `#D7CEC1` (70 533 px) · 50 pas
`#C8D9DD` (4 961 px) · trait de contour PPR pur `#D14432` · ANRU sur U `#B5CF95`
(25 043 px au cadre quartier).

## 9. LE VERDICT DES COMBINAISONS (l'exigence de l'arbitrage)

- **zonage U + PPR** (capture 05, Saint-Paul) : PAS confondues — le PPR se lit
  par son contour rouge `#D14432` + lavis rosé, le zonage U par son aplat mint +
  contour vert. Réserve honnête : à petite échelle, la mosaïque multirisque rend
  une image DENSE en traits rouges (chargée mais lisible) ; à l'échelle de
  travail parcellaire la densité tombe.
- **zonage U + ANRU** (captures 08/09, Le Port) : PAS confondues — le quartier
  NPNRU se lit en olive TRAMÉ (hachures visibles au zoom quartier), distinct du
  mint U et du beige non-U ; la trame porte la distinction daltonienne comme
  arbitré.

## 10. Non-régression Sombre + portes

Sombre : colonne de tokens verbatim, ordre des couches restauré, contours
largeur 0, trame opacité 0 — les captures sombre (mêmes cadres) montrent le rendu
historique (chartreuse pleine sans trame, aucun contour de zone). Greps : aucun
mauve hors IA, `#F5C518` seulement token Pages Jaunes, les littéraux restants de
MapView sont outils/marque/sélection hors périmètre (documentés). Portes :
tsc 0 · build OK · suite 1553 passed · golden 0 FAIL (33 INDÉTERMINÉ = quota API
du jour, panne d'environnement dite, jamais un écart métier).
