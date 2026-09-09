# RECETTE-9 — ce que la recette de RECETTE-8 a trouvé

Branche `fix/recette-9` (depuis `fix/recette-8`, non mergée). Worktree `~/Desktop/labuse-recette6`.
**Aucun merge, aucune bascule, aucun rescoring.** Seule ingestion : le LiDAR au travail 9 (bornée,
4 parcelles de Saint-Denis). Ports tenus : **API `:8031`, front `:5199`** ; `:8020`/`q_v14` de Vic
jamais touchés (SIGTERM uniquement). Un commit par travail, branche poussée à chaque lot.

## La règle de preuve
**Un travail n'est « fait » que prouvé sur l'artefact FINAL, produit depuis le VRAI chemin.** Pour un
document : le PDF régénéré et son texte relu. Pour un écran : la capture navigateur depuis l'entrée
réelle (la fiche), plus une assertion sur la donnée sous-jacente. Une fonction corrigée, un test vert
ou une capture d'un autre endroit ne valent pas preuve (cf. T11).

## Bilan des 11 travaux

| # | Travail | État | Preuve (artefact final) |
|---|---|---|---|
| T1 | 🔴 Dossier financier inaccessible (3 défauts) | ✅ fait | `T1-financier-etabli-EL0157.pdf` + captures questionnaire (indispensable + bannière + nav) |
| T2 | 🔴 Taxe absente sur parcelle à potentiel faible | ✅ fait | `T2-dossier-taxe-EL0157.pdf` (§8 dit comment obtenir le montant) |
| T3 | 🔴 « 1 bu » toujours là | ✅ fait | `T3-dossier-EL0157.pdf` §7 « 1 arrêt de bus » + test au RENDU |
| T4 | « Zone Zone Um » doublon | ✅ fait | `T4-apporteur-EL0157.pdf` « Zone : Um (famille U) » |
| T5 | 🔴 Le gris de la carte — trancher | ✅ fait | 6 captures `T5-A…E` : le gris = le fond Sombre |
| T6 | Contour blanc Remonter le temps absent | ✅ fait | `captures/T6-remonter-le-temps-contour.png` (cible 0→1 feature) |
| T7 | Espace CRM/Projet ↔ 6 boutons | ✅ fait | `captures/T7-avant-10px` / `T7-apres-24px` |
| T8 | Exposition — prouver, pas affirmer | ✅ fait | `T8-exposition-10-parcelles.txt` (tableau des 10 + r) |
| T9 | LiDAR — finir le travail | ✅ fait | 2 chiffrages + 4 consommateurs branchés (PDF + captures) |
| T10 | Verrou libellés — liste noire → registre | ✅ fait (partie faisable) | `T10-verrou-libelles.md` + tests ; parité pleine = chemin+coût écrits |
| T11 | Pourquoi 3 « faits » ne l'étaient pas | ✅ écrit | §T11 ci-dessous |

**Vérif** : vitest **202**, tsc **0**, pytest ciblé (recette9/8/provenance/exports2/potentiel/bati/
fiche1/financier/apporteur/commune/taxe) **339 passed** ; **1 fail PRÉ-EXISTANT** `test_exports2_lot6`
(prouvé identique sur base sans les changements T9). Provenance Z5 (libellés) verte.

---

## T1 — le Dossier financier redevient accessible (3 défauts)
**Diagnostic** (`scripts/_recette9_t1_repro.py`, reproduit empiriquement) : sur une parcelle **sans
potentiel chiffrable** (`capacite_estimee` faux — « Potentiel faible / Densité atteinte », le cas de
la recette), la surface vendable du bilan n'existe que si le porteur **saisit un nombre de
logements**. Or ce champ n'était **pas marqué indispensable** et le blocage « Programme
constructible » ne tombait qu'**à l'arrivée** du document. Prouvé : parcelle faible sans logements →
`manques=['Programme constructible']` ; avec logements → surface vendable servie, document établi.

- **Défaut n°1 (mention à la saisie)** : `GET /questionnaire` calcule `programme_depuis_potentiel`
  (helper `qf`, testé) et marque `logements_vises_saisi` **indispensable** quand le potentiel ne
  chiffre pas le programme ; une **bannière** le dit sur l'écran « Votre projet ». Sur une parcelle
  à fort potentiel : rien de plus à saisir (`programme.auto=true`, vérifié CS0027).
- **Défaut n°2 (blocage malgré saisie)** : le champ qui **débloque** est désormais nommé → plus de
  cul-de-sac ; le Financier s'établit — `T1-financier-etabli-EL0157.pdf` (faible → bilan + taxe).
- **Défaut n°3 (retour arrière)** : le fil des 4 étapes devient **cliquable** (aller/revenir à toute
  étape), saisie conservée — `T1-questionnaire-retour-etape1-saisie-conservee.png` (logements=8 après
  étape 2→1). Un « ← Retour » pas-à-pas existait déjà mais discret et limité : on rend la navigation
  explicite.

## T2 — la taxe ne disparaît plus
Conséquence de W2 : le montant est chiffré **au Financier**, mais sur une parcelle à potentiel faible
le Financier ne s'établissait pas → la taxe n'apparaissait **plus nulle part**. T1 rouvre le
Financier ; T2 ferme la boucle côté Dossier : le §8 reprend taux + phrase **et dit en une ligne
comment obtenir le montant**. `T2-dossier-taxe-EL0157.pdf` : « … Pour en obtenir le montant : ouvrez
le Dossier financier et décrivez le programme — le nombre de logements visés et la typologie
suffisent lorsque la parcelle n'a pas de potentiel constructible calculé. » Aucun chiffre inventé.

## T3 — « 1 bu » corrigé AU RENDU + prouvé sur PDF
Le bug W14 : le correctif (`_EQUIP_ACCORD` + `_accord` de module) était posé, mais `rendu()` gardait
une fonction `_accord` **imbriquée** qui l'**ombrait** — jamais appelée. Le test W14 testait la
fonction de module → restait vert pendant que « 1 bu » sortait au PDF. Suppression de l'ombre + test
**au niveau du rendu** (prouvé qu'il aurait mordu : ancien `_accord` → « 1 bu »). **PDF régénéré ce
jour** (`T3-dossier-EL0157.pdf`, §7) : « 1 école, 1 commerce, 1 service de santé, **1 arrêt de bus** ».

## T4 — « Zone Zone Um » : le doublon retiré
W15 a fait lire à l'Apporteur le libellé partagé « Zone Um (famille U) » (bon pour les phrases du
Dossier) mais l'a posé comme **valeur** d'une ligne dont la **clé** est déjà « Zone ». On retire le
préfixe « Zone » redondant. Sweep des 5 documents → même défaut au Financier (« Zone d'investissement
(A/B/C) » → « zone B2 ») corrigé (valeur = code seul « B1 »). `T4-apporteur-EL0157.pdf` : « Zone : Um
(famille U) — … ».

## T5 — le gris de la carte, tranché
Test décisif (`scripts/_recette9_t5_gris.mjs`, 6 captures) :
- **A** île/Sombre → **aucune parcelle peinte**, la carte EST le fond sombre (« Zoomez ou cliquez… »).
- **B** commune/Sombre analyse OFF → contours + remplissage neutre `#22302A/0,28`.
- **C** commune/Sombre analyse ON → image **IDENTIQUE à B** ⇒ **le gris n'est PAS l'analyse**.
- **D** commune/Ortho → la photo apparaît ; **E** commune/Clair → parcelles blanches, **gris disparu**
  ⇒ **c'est le FOND**.

**Cause (une phrase)** : le gris est le **fond de plan « Sombre »** (thème par défaut) — à l'île
aucune parcelle n'est rendue (100 % fond), à l'échelle commune les parcelles ne portent qu'un
remplissage neutre quasi invisible sur ce fond ; ni l'analyse, ni un « voile » de parcelles comme
ceux que les 3 mandats précédents ont retirés — d'où « on ne cherchait pas au bon endroit ».
**Corrigé (le bon calque)** : le seul gris peint par NOS calques (le remplissage neutre) est éteint
sur Sombre/photo (contours conservés, sélection via `parcelAt` préservée), blanc gardé sur Clair —
achève la règle W9/S11/V1 « couleur de palier ou RIEN ». Le gris dominant restant est le thème
Sombre lui-même : Clair/Ortho le lèvent.

## T6 — le contour blanc s'affiche enfin
W13 avait bien mis la couleur blanche (`#ECF5EF`) et c'était committé. Mais **depuis la fiche** le
contour restait **absent** : la source `cible` avait **0 feature** (prouvé : geojson 200, source
présente, style chargé, mais `setData` jamais appliqué — course StrictMode entre la recréation des
cartes et l'effet qui pose la géométrie). Fix : la FC voulue est gardée dans un ref, réappliquée
quand la donnée change **et** quand une carte (re)crée la source. `T6-remonter-le-temps-contour.png` :
contour blanc sur le 1950 **et** l'ortho actuelle (cible = 1 feature des deux côtés).

## T7 — l'espace franchement augmenté
10 px (RECETTE-7 B4) restait trop faible. Respiration **doublée (10 → 24 px)** + un filet de
séparation. `T7-avant-10px.png` / `T7-apres-24px.png` (même fiche EL0157).

## T8 — l'exposition prouvée, pas affirmée
Tableau des 10 (`T8-exposition-10-parcelles.txt`) :
- **r(productible, GHI) = 0,988** → le productible imprimé EST quasi l'**irradiation horizontale**
  (azimut-indépendante) : il **ne varie pas** avec l'orientation. Le test « nord→haut / sud→bas » est
  donc **inapplicable** — le productible ne juge pas l'orientation (PVGIS ~horizontal).
- **Deux méthodes d'exposition indépendantes** (gdaldem W22 vs 4 points RGE ALTI de `enrichment.py`)
  **convergent en direction** : jamais un écart de ~180° ; les désaccords sont plat↔pente au seuil de
  3°. ⇒ **l'orientation n'est PAS retournée** (convention géographique 0°=N, validée par une 2e
  méthode). L'exposition est saine ; le productible est une grandeur horizontale distincte.

## T9 — le LiDAR : les 2 chiffrages + les 4 consommateurs branchés
**Les 2 chiffrages** (`scripts/_recette9_t9_lidar_chiffrage.py`, 39 bâtiments de Saint-Denis) —
« +0,57 m d'écart médian, c'est peu ; la valeur du LiDAR = précision du faîtage, ou distinction
faîtage/égout ? » :
- **A (précision du faîtage)** : |faîtage − BD TOPO| médian = **1,10 m**, 41 % seulement à ≤1 m →
  **modeste** (BD TOPO donne déjà un faîtage grossièrement juste).
- **B (distinction faîtage/égout, que BD TOPO ne donne JAMAIS)** : amplitude faîtage−égout médiane =
  **2,08 m** (jusqu'à 8 m) ; BD TOPO n'est un faîtage que **59 %** du temps ; BD TOPO − égout médian
  **+1,43 m** → la hauteur constructible réelle (égout) est ~1,4 m **sous** le nombre BD TOPO.
- **Réponse** : la valeur du LiDAR est la **distinction faîtage/égout (B)**, pas la précision (A).
  L'égout décide la surélévation (règle à l'égout, cause de fond de E1) et BD TOPO ne le donne pas.
  → l'ingestion complète se justifie **pour l'égout**, pas pour gagner ~1 m sur le faîtage.

**Le branchement** (point unique `hauteur_lidar.hauteur_batie`/`hauteur_lidar_servie`, table bornée
`batiment_hauteur_lidar` alimentée par `ingest_hauteur_lidar` — seule ingestion du mandat), étiquette
**estimé → sourcé** :
1. **Fiche** (`bati.le_bien_block` + front `leBien.tsx`) → « 6,9 m au faîtage · 3 m à l'égout — LiDAR
   HD (mesuré) » (`captures/T9-fiche-le-bien-lidar.png`).
2. **Apporteur** (via `le_bien`) → « environ 6,9 m de haut » (`T9-apporteur-lidar-EL0157.pdf`).
3. **Dossier surélévation** (`_potentiel_transformation_block` + bloc `potentiel.py`) → compare enfin
   un **égout MESURÉ (3,0 m)** à la règle d'égout (10 m) → « Surélévation possible — **7,0 m
   disponibles**, hauteur à l'égout mesurée au LiDAR HD », sourcé (`T9-dossier-lidar-EL0157.pdf`). La
   réparation de fond de E1 : « 3,4 m disponibles » (soustraction sur un faîtage BD TOPO) devient
   **7,0 m mesurés à l'égout**.
4. **Extrusion 3D** (`/map/batiments.geojson`) → préfère le faîtage LiDAR, flag `lidar` par bâtiment
   (EL0157 → 3 bâtiments `lidar=true`, h=6,9). Repli BD TOPO (estimé) partout où le LiDAR n'est pas
   ingéré — le point unique gère les deux natures. Aucune ingestion massive de l'île (doctrine D).

## T10 — le verrou des libellés : liste noire → dérivée des vocabulaires
Avant : liste noire figée à la main (19 codes) — attrapait `surelevation` mais aurait laissé passer
tout **nouveau** code non inscrit. **Fait** : `_CODES_TECHNIQUES` est **dérivée des vocabulaires
contrôlés** (`scenarios`, `tiers_client`, `enums`), formes non ambigües seulement (`_`, MAJUSCULES,
variante sans-accent d'un libellé mono-mot). Un nouveau code snake_case/CAPS/sans-accent est couvert
**automatiquement**. Dérivé = **31** (⊇ 19 à la main, +12 auto ; **0 faux positif** :
reconstruction/revente/division/chaude non pris). Tests `test_recette9_verrou_libelles.py` (4).
**Reste (parité pleine avec les nombres — non faisable ici, chemin+coût dans `T10-verrou-libelles.md`)** :
attraper un libellé **français inventé** (ni code ni identifiant) exige un **tag de provenance au
rendu** (span `data-provenance` par libellé) + une sonde qui confronte chaque libellé à la valeur
servie — refactor transverse de la couche de rendu, sous go.

---

## T11 — pourquoi T3, T6 et T7 étaient « faits » sans l'être

Trois façons différentes de prendre la preuve **à côté** de l'artefact livré :

- **T3 — la preuve au mauvais endroit.** W14 avait corrigé une fonction `_accord` de **module** et
  un **test** de cette fonction (vert). Mais le rendu réel appelait une fonction `_accord`
  **imbriquée** qui l'ombrait. La « preuve » (un test vert) portait sur du code **jamais exécuté par
  le document**. Personne n'a relu le §7 d'un PDF régénéré sur un cas « 1 bus ».
- **T6 — la capture d'un autre chemin.** W13 avait bien changé la couleur et l'avait committée ; la
  capture « après » montrait un contour blanc — mais prise en désignant la parcelle par l'**omnibox**
  (qui pose `tempsPinIdu`), pas par le **bouton de la fiche** (qui, lui, laissait la source vide à
  cause d'une course StrictMode). L'artefact du **vrai chemin utilisateur** n'a jamais été regardé.
- **T7 — l'artefact non jugé.** Le correctif (un espaceur de 10 px) était committé, mais « fait » a
  été déclaré sans **regarder** si l'espace lisait comme une séparation. 10 px ne suffisaient pas ;
  aucune capture avant/après ne l'a mis en évidence.

**Le fil commun** : un **test vert**, un **diff committé** ou une **capture d'un endroit commode** ont
tenu lieu de preuve, à la place de **l'artefact final produit depuis le vrai chemin**.

**Ce qui change dans la méthode (et que RECETTE-9 applique partout) :**
1. **Prouver sur l'artefact final, depuis le chemin réel.** Document → régénérer le **PDF** et relire
   son **texte** (T3 §7, T4, T2, T9). Écran → capturer depuis l'**entrée réelle** (T6 : le bouton de
   la fiche, pas l'omnibox) **et** asserter la **donnée** sous-jacente (T6 : `cible` = 1 feature ;
   T5 : les paint-properties et le compte de features rendus), jamais un seul coup d'œil.
2. **Faire mordre le test à l'altitude de l'artefact.** T3 : test **au rendu** (`_rendu_equip`) qui
   assure le HTML produit, et **preuve qu'il attrape** le bug (ancien `_accord` → « 1 bu »). Un test
   qui ne peut pas échouer sur le vrai bug n'est pas une preuve.
3. **Un vert / un diff / une capture au mauvais endroit ne comptent pas.** Vérifier que le diff est
   bien **sur le chemin qui s'exécute** (T3 : l'ombre) et que l'artefact regardé est **celui qui est
   servi** (T6 : le bon chemin ; T5 : le bon calque après avoir écarté fond, analyse, échelle).

---

**Rien n'est mergé.** Branche `fix/recette-9` poussée ; `main` et `fix/recette-8` intactes.
