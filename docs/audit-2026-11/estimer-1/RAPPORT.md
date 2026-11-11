# ESTIMER-AUDIT-1 — comment l'outil « Estimer un bien » calcule, et ce qu'il vaut

**Branche** `audit/estimer-1` · worktree `~/Desktop/labuse-estimer` · ports 10030/7230 · base locale
`labuse` (434 582 parcelles, DVF géolocalisé arrêté au 31/12/2025). **Lecture seule. Aucune correction,
aucun merge, aucun accès prod.** Date : 10/11/2026.

Ce rapport est écrit pour être lu **sans connaître le code**. Il répond à quatre questions :
1. Comment l'outil fabrique un prix, étape par étape ?
2. Que veut dire « aucune vente depuis 2014 » quand l'outil l'affiche ?
3. Quand on confronte l'outil à de vraies ventes de 2025, de combien se trompe-t-il ?
4. Quelles sont ses faiblesses, par ordre d'importance, et que faudrait-il pour les corriger ?

---

## Résumé en clair (le verdict)

**Estimer est un comparateur de secteur honnête, pas un estimateur de valeur vénale — et il le dit.**
Sur un échantillon de **200 ventes réelles de maisons** et **200 de terrains de 2025** confrontées à ce
que l'outil aurait affiché *sans voir la vente* (rétro-test §3) :

| | maison | terrain nu |
|---|---|---|
| **Écart médian** entre prix affiché et prix réel | **29 %** (prix au m² seul : 24 %) | **27 %** |
| **Quartiles de l'écart** (Q1 – Q3) | 11 % – 46 % | 14 % – 49 % |
| **Part des ventes estimées à ± 20 %** | **34 %** | **40 %** |
| Ventes auxquelles l'outil sait répondre | 200 / 200 | **159 / 200** (41 sans prix) |

Autrement dit : **une estimation sur deux s'écarte de plus d'un quart du prix réel**, et **deux
tiers des maisons** tombent **hors d'une fourchette à ± 20 %**. Ce n'est pas un défaut de réglage : la
donnée DVF ne porte pas ce qui fait le prix d'un bien (état, prestations, exposition fine) — un test de
modèle (gradient boosting) mené par une session sœur plafonnait lui aussi à ~28 % pour la maison. L'outil
affiche d'ailleurs une mention d'incertitude cohérente avec ces chiffres.

Les vrais problèmes sont ailleurs, et ils sont **réparables** : la **surface** d'une maison est presque
toujours *devinée* (et non connue), ce qui ajoute ~5 points d'erreur ; **un terrain sur cinq** ne reçoit
aucun prix faute de ventes dans sa section cadastrale ; le libellé **« aucune vente depuis 2014 »** est
**faux pour 38 503 parcelles** qui ont bien été vendues entre 2014 et 2020 (données chargées mais jamais
lues) ; enfin, l'amélioration vedette d'une session antérieure (la « médiane pondérée ») **est calculée
puis jetée** pour le chiffre affiché. Détails et correctifs au §4.

---

## 1 — La chaîne de calcul exacte

Tout part d'un **point de calcul unique** côté serveur, `estimation_annonce` (`src/labuse/pige/api.py`),
lu à l'identique par l'écran (« Analyser une annonce ») et par le PDF/Doc — mêmes chiffres partout.

### 1.0 — De quel bien parle-t-on ? (la nature)

Avant tout prix, l'outil décide si le bien est une **maison**, un **appartement**, une **copropriété**
ou un **terrain nu**. Il ne regarde **pas** l'état actuel de la parcelle mais **la dernière vente DVF
de cette parcelle** (`_derniere_mutation_dvf`) : si la dernière vente portait sur un terrain, c'est un
terrain ; si elle portait sur une maison, c'est une maison. À défaut de vente, il se rabat sur l'état
bâti de la parcelle (part de la parcelle couverte par du bâti : < 5 % = nu, inconnu = « non mesuré »).
Les copropriétés passent en premier et sont comparées à des appartements.

> **Point important** : « la dernière vente DVF » est lue dans la table `dvf_mutations_parcelle`, qui ne
> contient que **2021 → 2025** (voir §2). Une parcelle vendue en 2017 et pas depuis est traitée comme
> « jamais vendue ».

### 1.1 — Le prix au m² : quelles ventes, quel rayon, quelle période, quels filtres

C'est le cœur. **Deux chemins** selon la nature.

**A. Bien bâti (maison / appartement / copropriété)** — le prix au m² affiché est celui de la fonction
`reference_locale` (`src/labuse/faisabilite/bilan.py`), le même moteur « marché de secteur » que la
fiche parcelle. Sa recette :

- **Quelles ventes** : toutes les ventes **de la commune** de la parcelle, **du même type** que le bien
  (maison avec maisons, appartement avec appartements — jamais l'un pour l'autre) ;
- **Filtres** : surface bâtie **≥ 20 m²**, valeur **> 20 000 €**, **ventes de gré à gré seulement**
  (`nature = 'Vente'` ; le neuf/VEFA, les adjudications, échanges, expropriations sont exclus) ;
  prix au m² **dans [1 000 ; 12 000] €/m²** (hors de là = artefact DVF, on l'ignore) ; puis on
  **retire les 5 % de prix les plus extrêmes** (2,5 % de chaque côté) ; une vente est **dédoublonnée
  par mutation réelle** (une vente groupée = une observation) ; **la parcelle n'est jamais son propre
  comparable** ;
- **Rayon** : **adaptatif**, calculé depuis le centre de la parcelle — on essaie **500 m**, puis
  **1 000 m**, puis **1 500 m**, et on s'arrête au premier rayon qui réunit **au moins 8 ventes** ; si
  1 500 m ne suffit pas, repli sur **la commune entière** ;
- **Période** : on **préfère les 5 dernières années** (« récente », soit 2022-2025) ; si l'échantillon
  est trop mince, on élargit à **toutes les années disponibles** ;
- **Le prix retenu** = la **médiane simple** des prix au m² restants.

Le chiffre voyage avec ses paramètres affichés : *« maison · 4 265 €/m² · 34 ventes · rayon 1 000 m ·
2022-2025 »*.

**B. Terrain nu** — le prix au m² vient d'une table pré-calculée `dvf_secteur_medianes`
(`_terrain_section`), **au grain de la section cadastrale** (les 10 premiers caractères de l'identifiant
parcellaire) — **pas** un rayon géographique :

- **Quelles ventes** : les ventes de la section déclarées **« Vente » ou « Vente terrain à bâtir »**,
  **sans bâti** ;
- **Filtres** : prix au m² dans **[50 ; 20 000] €/m²**, période **2021-2025**, **médiane simple**,
  **minimum 8 ventes** — **sinon aucun prix n'est servi** (« pas assez de ventes de terrain nu dans le
  secteur »). Il n'y a **ni rayon adaptatif ni repli commune** pour le terrain.

### 1.2 — Ce que « fiabilité » mesure vraiment

À côté du prix, l'outil affiche un mot (**Élevée / Moyenne / Limitée**) et un pourcentage (*« Précision
mesurée sur les ventes 2025 : ± X % »*). Ce n'est **pas** une mesure de la justesse de *cette* parcelle :
c'est une **bande calibrée** (`_fiabilite_bien`) qui dépend de **deux** choses seulement :

1. le **nombre de comparables** trouvés (`n`) ;
2. leur **dispersion** — l'écart entre le quart le moins cher et le quart le plus cher, rapporté à la
   médiane.

Les bandes diffèrent par type (plus sévères pour la maison, dont la donnée est plus hétérogène) :

| Type | « Élevée » | « Moyenne » | « Limitée » (ou repli commune) |
|---|---|---|---|
| Appartement / copro | n ≥ 15 et dispersion ≤ 0,40 → **± 15 %** | **± 18 %** | **± 30 %** |
| Maison | n ≥ 40 et dispersion ≤ 0,25 → **± 20 %** | **± 26 %** | **± 36 %** |

**Le ± % affiché est l'écart médian réellement mesuré** de la bande sur un banc antérieur (il ne promet
pas une précision que la donnée ne tient pas). **Deux réserves honnêtes** :
- il reflète l'erreur du **prix au m²**, pas du **total** ; or le total ajoute l'erreur de surface (§1.3) ;
- il est calculé sur l'échantillon de comparables, pas sur le bien lui-même (dont on ne sait presque rien).

### 1.3 — La surface habitable (le facteur d'erreur n° 1 du total)

Le **total en euros** d'une maison = **surface × prix au m²**. La surface est choisie dans cet ordre
(`_surface_pour_total`) :

0. **la surface saisie** par l'utilisateur (champ facultatif de l'entrée par adresse) — l'intrant le
   plus sûr ;
1. sinon, la **surface bâtie de la dernière vente DVF** de la parcelle (2021-2025) ;
2. sinon, **l'emprise au sol du bâti (BD TOPO) × un ratio** = la médiane (surface vendue ÷ emprise) des
   ventes de maisons **de la commune** (une maison vaut en moyenne ~0,5× son emprise, car l'emprise
   compte le sol de tout le bâtiment, pas l'habitable) ;
3. si la parcelle est « non mesurée » et sans vente : **aucun total n'est affiché** (on refuse de
   fabriquer un chiffre).

> En pratique (§3), la surface est **presque toujours devinée** : sur 200 maisons, seulement **26** ont
> hérité d'une surface de vente DVF antérieure ; **174** sont passées par l'emprise × ratio. Le ratio
> communal n'existe d'ailleurs que pour **24 communes** (les autres n'ont pas 20 ventes de calage).

### 1.4 — Comment le bâti existant entre dans le résultat

Le bâti **ne s'ajoute pas** au terrain. Pour un bien bâti, l'outil sert **un seul total** = surface
habitable (§1.3) × prix au m² habitable (§1.1-A). L'emprise au sol du bâti existant ne sert qu'à **deviner
la surface** quand la vente ne la donne pas. L'outil affiche aussi, **à titre indicatif et séparé**, une
**« lecture foncière »** : surface de la parcelle × prix au m² de terrain nu du secteur, et la part que
cette valeur foncière représente de l'ordre de grandeur bâti — mais ce n'est pas additionné au total bâti.

### 1.5 — D'où vient la « valeur du terrain »

C'est la **lecture foncière** ci-dessus (`_lecture_fonciere_parcelle`) : **surface de la parcelle**
(contenance cadastrale, sinon dessin) **× le repère €/m² de terrain nu de la section** (§1.1-B). Pour un
**terrain nu**, c'est **le** résultat principal. Pour un bien bâti, c'est une information de contexte.
Cette valeur foncière est présentée avec une **fourchette ± 30 %** (module `estimation_prix.py` /
`fourchette.ts`), une largeur fixe assumée comme prudente (voir §4-f).

---

## 2 — Que signifie « aucune vente depuis 2014 »

L'outil (et le PDF) affichent *« Dernière vente : aucune depuis 2014 »* quand la parcelle n'a **pas de
mutation connue**. Le mot **« 2014 »** laisse entendre que l'outil a regardé douze ans d'historique. **Ce
n'est pas le cas.**

- La donnée DVF **géolocalisée et rattachée aux parcelles** (`dvf_mutations_parcelle`, et la vue
  `v_parcel_dvf_last` qui alimente « Dernière vente ») ne couvre que **2021 → 2025** (102 551 lignes,
  29 565 mutations géolocalisées).
- Les ventes **2014 → 2020** existent bien dans la base (`dvf_mutations_histo`, **110 477 lignes**), mais
  **aucun chemin de l'outil ne les lit** — ni la nature du bien, ni « Dernière vente », ni les
  comparables.

**Conséquence mesurée sur la base** :

| Fait | Nombre |
|---|---|
| Parcelles de l'île | 434 582 |
| Parcelles avec **au moins une vente 2021-2025** (ce que l'outil voit) | **37 868** (8,7 %) |
| Parcelles présentes dans l'historique **2014-2020** | 45 089 |
| **Parcelles vendues 2014-2020 mais PAS depuis 2021** | **38 503** |

Ces **38 503 parcelles** ont une vraie vente entre 2014 et 2020, mais l'outil affiche pour elles
**« aucune depuis 2014 »** — un énoncé **faux** : il faudrait lire *« aucune depuis 2021 »*. Le phénomène
a trois causes qui se cumulent, et qu'il faut distinguer pour le lecteur :

1. **Couverture temporelle** — le robinet de l'outil démarre en 2021, pas en 2014.
2. **Parcelles jamais vendues** — l'immense majorité des parcelles (plus de 9 sur 10) n'a **aucune**
   mutation, même sur 2021-2025 : beaucoup de biens ne changent simplement pas de main sur la période.
   Pour celles-là, « aucune vente » est **vrai** (mais « depuis 2014 » reste trompeur).
3. **Ventes non rattachées** — DVF porte la valeur sur la **mutation entière** (toutes parcelles et lots
   confondus). Une vente groupée (41 % des mutations touchent plusieurs parcelles) est rattachée à chaque
   parcelle qu'elle touche, mais le prix au m² « de la parcelle » est en réalité celui de l'**ensemble**
   vendu ; les ventes sans géolocalisation exploitable ne se rattachent à aucune parcelle.

---

## 3 — Rétro-test : l'outil face à 400 vraies ventes de 2025

### Méthode (honnête, sans tricher)

Script `banc.py` (ci-joint). On tire **200 ventes réelles de maisons** et **200 de terrains nus** de
**2025** (mutations mono-parcelle, graine aléatoire fixe). Pour chacune, on calcule le prix que l'outil
**aurait affiché** et on le compare au prix **réellement payé** (`valeur_fonciere`).

- **Pas de triche (no-leak)** : pour estimer une vente, les comparables sont **strictement antérieurs** à
  sa date et **la vente jugée est exclue** — l'outil ne s'estime jamais lui-même.
- On reproduit **exactement le chemin servi** (§1), y compris le fait que le prix au m² bâti est la
  **médiane simple de secteur** (`reference_locale`), pas la médiane pondérée (voir §4-e).
- On retient **deux scénarios de surface** pour la maison : **surface connue** (= surface réellement
  vendue, ce qu'obtient l'utilisateur qui saisit la surface) et **surface auto** (ce que l'outil fabrique
  tout seul, §1.3). Pour le terrain, la surface est la contenance cadastrale (≈ surface vendue).
- Garde-fous : on ne juge que les ventes dont le prix réel est plausible (maison 1 000-12 000 €/m²,
  terrain 50-4 000 €/m²).

L'écart rapporté est **|prix estimé − prix réel| ÷ prix réel**, en %.

### Résultats globaux

| Mesure | Maison — €/m² | Maison — total (surface connue) | Maison — **total (surface auto)** | Terrain nu — total |
|---|---|---|---|---|
| n jugées | 200 | 200 | 200 | **159** (41 sans prix) |
| **Écart médian** | **24,3 %** | 24,3 % | **29,2 %** | **27,0 %** |
| Q1 (1er quartile) | 8,2 % | 8,2 % | 10,6 % | 13,8 % |
| Q3 (3e quartile) | 43,1 % | 43,1 % | 45,9 % | 49,1 % |
| **Part à ± 20 %** | 45 % | 45 % | **34 %** | **40 %** |
| Part à ± 10 % | 30 % | 30 % | 24 % | 16 % |

Lecture :
- Le **total réellement servi par défaut** (surface auto) pour une maison s'écarte en médiane de
  **29 %** du prix payé ; **seulement 34 %** des ventes tombent à ± 20 %, soit **deux sur trois en
  dehors**. Le Q3 à 46 % dit qu'**un quart des estimations dépasse 46 % d'écart**.
- Dès que la **surface est connue** (utilisateur qui la saisit), l'erreur du total **retombe à celle du
  prix au m²** (24 %) : **la surface devinée coûte ~5 points d'écart médian** et fait chuter la part à
  ± 20 % de 45 % à 34 %.
- Le **terrain** n'est jugeable que pour **159 des 200** ventes : **41 (20 %)** tombent dans une section
  cadastrale sans assez de ventes → **l'outil n'affiche aucun prix**. Là où il répond, l'écart médian
  est de **27 %**, 40 % à ± 20 %.

### Par commune (n ≥ 8 dans l'échantillon)

**Maison — total, surface auto** (ce que l'outil sert seul) :

| INSEE | n | médian | Q1 | Q3 | ± 20 % |
|---|---|---|---|---|---|
| 97408 | 8 | **9,4 %** | 8,4 % | 21,1 % | 75 % |
| 97410 | 8 | **8,1 %** | 4,7 % | 25,9 % | 63 % |
| 97416 | 20 | 14,7 % | 8,1 % | 41,2 % | 55 % |
| 97414 | 14 | 25,7 % | 22,2 % | 41,8 % | 14 % |
| 97415 | 23 | 25,8 % | 10,0 % | 39,5 % | 43 % |
| 97411 | 25 | 33,1 % | 15,4 % | 49,5 % | 28 % |
| 97422 | 27 | 33,8 % | 21,4 % | 43,7 % | 26 % |
| 97412 | 12 | 36,2 % | 21,1 % | 42,1 % | 17 % |
| 97407 | 11 | 36,9 % | 25,4 % | 109,0 % | 9 % |
| 97409 | 12 | 42,7 % | 13,8 % | 50,1 % | 33 % |

**Terrain nu — total** :

| INSEE | n | médian | Q1 | Q3 | ± 20 % |
|---|---|---|---|---|---|
| 97409 | 12 | **14,8 %** | 13,6 % | 17,6 % | 75 % |
| 97420 | 8 | 16,3 % | 8,6 % | 26,7 % | 75 % |
| 97412 | 12 | 19,5 % | 9,2 % | 46,5 % | 58 % |
| 97413 | 11 | 21,4 % | 11,9 % | 65,9 % | 45 % |
| 97416 | 16 | 25,5 % | 15,1 % | 50,3 % | 44 % |
| 97410 | 8 | 29,6 % | 7,4 % | 77,3 % | 38 % |
| 97415 | 24 | 31,6 % | 21,4 % | 55,1 % | 25 % |
| 97422 | 19 | 35,5 % | 22,9 % | 54,5 % | 26 % |
| 97414 | 11 | 39,3 % | 14,6 % | 56,6 % | 36 % |

La dispersion entre communes est **énorme** : de ~8-15 % (secteurs denses et homogènes, où le comparateur
a beaucoup de ventes proches et semblables) à **37-43 %** (communes étalées, à l'habitat hétérogène, où le
rayon s'élargit et mélange des biens différents). **C'est exactement la limite d'un comparateur de
secteur** : il est bon là où le marché est dense et uniforme, et faible là où il ne l'est pas — et il ne
peut pas, seul, savoir dans lequel des deux cas il se trouve au-delà du signal « dispersion » du badge.

Détail vente par vente dans `PAR-VENTE.csv` (métriques dans `METRIQUES.json`).

---

## 4 — Faiblesses, classées par importance (sans les corriger)

### a) La surface de la maison est presque toujours devinée — et c'est le 1er poste d'erreur du total **(majeur)**
174 maisons sur 200 n'ont pas de surface fiable : l'outil passe par **emprise × ratio communal**, qui
ajoute ~5 points d'écart médian (29 % vs 24 %) et fait perdre 11 points de « ± 20 % ». Le ratio n'existe
que pour 24 communes. *Pour corriger (sans le faire)* : brancher une surface habitable fiable par parcelle
(DVF historique 2014-2020 déjà en base — §2 ; RNB/BD TOPO « nombre de niveaux » ; fichiers fonciers
Majic « surface réelle »), et **pré-remplir** systématiquement le champ surface ; à défaut, rendre la
saisie de surface **plus visible** puisque c'est elle qui divise l'erreur.

### b) Le plancher d'erreur du prix au m² maison (~24-27 %) **(majeur, mais structurel)**
Une estimation de maison sur deux s'écarte de ≥ 24 % ; seulement 45 % à ± 20 % même avec la surface
connue. Ce plafond est **intrinsèque à DVF** (ni l'état, ni les prestations, ni l'exposition n'y figurent)
et une session sœur a montré qu'un modèle d'apprentissage ne fait pas mieux (~28 %). *Pour corriger* :
on ne peut pas descendre beaucoup plus bas avec DVF seul — la bonne réponse est **de ne pas sur-vendre la
précision** (ce que l'outil fait déjà via sa mention) et d'**élargir honnêtement la fourchette** là où la
dispersion est forte, plutôt que de viser un chiffre juste.

### c) Un terrain sur cinq sans réponse, et une maille trop grossière **(important)**
Le repère terrain est pris **au grain de la section cadastrale entière**, sans rayon adaptatif ni repli :
**41/200 ventes (20 %)** tombent sans prix (seulement **438 des 936 sections** ont ≥ 8 ventes de terrain),
et là où il répond, une section mélange des terrains très différents (médian 27 %, un quart > 49 %).
*Pour corriger* : donner au terrain **le même moteur adaptatif que le bâti** (rayon 500→1500 m + repli
commune, ventes datées, trim des extrêmes) au lieu d'une table pré-agrégée par section ; intégrer la
distance au littoral/aux Hauts (déjà mesurable via le trait de côte) comme facteur de ressemblance.

### d) « Aucune vente depuis 2014 » est faux pour 38 503 parcelles **(important, trompeur)**
Le libellé promet un historique depuis 2014 ; l'outil ne lit que 2021-2025. 38 503 parcelles vendues
2014-2020 sont affichées « aucune depuis 2014 ». *Pour corriger* : soit **brancher `dvf_mutations_histo`**
(déjà en base, 110 477 lignes 2014-2020) sur « Dernière vente » et la nature du bien, soit **corriger le
libellé** en *« aucune depuis 2021 »* (la seule période réellement consultée). La première option
récupère aussi des surfaces (§a) et des natures de bien plus justes.

### e) La « médiane pondérée » vedette est calculée puis jetée pour le chiffre affiché **(important, écart doc ↔ code)**
`comparateur_bien` calcule une médiane pondérée par la ressemblance (ESTIMER-PRECISION-1, gain annoncé
appartement 17 % → 14,5 %). **Mais** pour tout bien typé maison/appartement, le code l'**écrase** ensuite
par la **médiane simple** de `reference_locale` (le prix affiché et multiplié dans le total). La médiane
pondérée ne sert plus qu'à **choisir les 8 comparables montrés**. Conséquence : le **gain de précision
annoncé n'est pas celui qui est servi** ; la précision réelle de l'appartement reste celle de la médiane
simple (~17 %), pas 14,5 %. *Pour corriger* : décider **lequel des deux** doit servir — soit servir la
médiane pondérée (et revérifier qu'elle tient son gain hors échantillon), soit retirer le calcul inutile
et aligner la documentation sur ce qui est réellement affiché.

### f) Deux systèmes d'incertitude cohabitent **(mineur)**
La **valeur du terrain** (lecture foncière, Copilote, fiche) porte une fourchette **± 30 % fixe** ; la
**tuile Estimer** porte, elle, le **± % par bien** (`precision_pct`, « précision mesurée sur les ventes
2025 »). Deux largeurs différentes pour deux faces du même outil, ce qui peut dérouter. De plus le ± % du
badge mesure l'erreur du **m²** alors qu'il entoure un **total** dont l'erreur (surface auto) est plus
grande (29 % médian pour une bande souvent affichée « ± 26 % ») → la fourchette du total est **un peu trop
étroite** plus d'une fois sur deux. *Pour corriger* : **une seule** doctrine d'incertitude, et **gonfler**
la fourchette du total de la part d'incertitude propre à la surface quand celle-ci est devinée.

### g) Le prix « de la parcelle » d'une vente groupée est celui de l'ensemble **(mineur, déjà signalé)**
DVF porte la valeur sur la mutation entière ; 41 % des mutations touchent plusieurs parcelles. Le code
dédoublonne et borne (filtres [1000;12000], trim 5 %, exclusion VEFA), ce qui amortit mais n'élimine pas
le bruit des ventes multi-lots dans l'échantillon de comparables.

---

## Fichiers & rejeu

| Fichier | Contenu |
|---|---|
| `RAPPORT.md` | ce rapport |
| `banc.py` | le rétro-test (lecture seule, no-leak) |
| `METRIQUES.json` | toutes les mesures du §3 (global, par type, par commune) |
| `PAR-VENTE.csv` | une ligne par vente jugée (réel, estimé, n comparables, rayon, écarts) |

**Rejouer le banc** :
`LABUSE_DATABASE_URL=postgresql+psycopg:///labuse ~/Desktop/labuse/.venv/bin/python docs/audit-2026-11/estimer-1/banc.py`

**Code lu** (points d'appel uniques) : `src/labuse/pige/api.py` (`estimation_annonce`,
`_derniere_mutation_dvf`, `_surface_pour_total`, `_fiabilite_bien`, `_terrain_repere`, `rapport_parcelle`) ·
`src/labuse/marche_service.py` (`comparateur_bien`, `comparateur_terrain`) ·
`src/labuse/faisabilite/bilan.py` (`reference_locale`, `sector_price`, `_ventes_bati_dedup`,
`_selection_secteur`, `trim_extremes_5pct`) · `src/labuse/api/mon_secteur.py` (`_terrain_section`) ·
`src/labuse/ingestion/dvf_marche.py` (`dvf_secteur_medianes`) · `src/labuse/estimation_prix.py` (fourchette
± 30 %) · `src/labuse/exports/blocs/annonce.py` + `frontend/src/components/outils/AnalyserAnnonce.tsx`
(affichage « aucune depuis 2014 », fourchette écran).

**Portée** : lecture seule, aucun fichier de code modifié, aucun merge, aucun accès prod. Les chiffres du
§3 proviennent de la base locale `labuse` (DVF arrêté au 31/12/2025) via le banc ci-joint.
