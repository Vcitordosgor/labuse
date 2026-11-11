# RETOURS-26 — recette de RETOURS-25 (suite)

Branche `fix/retours-23` (même branche), worktree `~/Desktop/labuse-outils`, ports 10010/7210.
**Pas de merge, aucun accès prod.** Vérifié dans **WebKit** (playwright 1.49.1, webkit-2104, reducedMotion) —
une capture par point dans `captures/` (gitignorées ; seul ce compte-rendu est suivi).

Hook complet **VERT** : `tsc -b` 0 · vitest **310/310** · `vite build` OK · scan secrets « rien trouvé » ·
pytest unitaires **3211 passed** (49 skipped = famille base, hors unitaires).

---

## 1. Boîte parcelle unique — option A, dans TOUS les outils

Maquette `docs/design/maquettes/nov-2026/10-boite-parcelle.png`, **option A**. Une fois la parcelle choisie
(saisie OU clic carte), le champ **reste rempli** : **adresse entière en gras** (passe à deux lignes si
besoin, jamais coupée), puis **« IDU · zone · surface »** en dessous, avec une **croix ✕** à droite qui vide
le champ et réaffiche la recherche. **Plus aucun bouton ni lien « Changer de parcelle » nulle part.**

- `EntreeParcelle.tsx` (le composant partagé) : bloc « parcelle choisie » réécrit en boîte option A. Épingle
  mint `◎`, adresse `font-semibold` `break-words`, méta `IDU · zone · surface` en mono discret, bouton ✕
  (`data-entree-vider`, `onChanger`), phrase d'aide dessous. Capture : **`p01-boite-parcelle.png`**
  (« 3 Chemin de la Citerne, 97417 Saint-Denis » · « BZ 1065 · Uh · 1 567 m² » · ✕).
- La **zone PLU** manquait à la source : ajoutée à `/parcels/search` côté back (`app.py`, `COALESCE(zone_lib,
  zone_fam)`, `LEFT JOIN parcel_zone_plu` **après le LIMIT** — ≤ 10 lignes, jamais un scan par parcelle ;
  gardée par `_zone_plu_ready`) et au type `searchParcels` (`lib/api.ts`). Vérifié live : `zone_plu` = « Uh »,
  « UAm », « UA » selon la parcelle.
- Comme tous les outils partagent `EntreeParcelle`, la boîte s'applique d'un coup à **Pièges, Gabarit, Taxe,
  Solaire, Calculette, Blocs/Successions, Comparer** et à **Remonter le temps** (son picker vit dans le
  panneau gauche `ModulePanel`, déjà `EntreeParcelle` → la boîte option A y apparaît automatiquement).
- **Estimer** (`AnalyserAnnonce.tsx`) n'utilisait pas `EntreeParcelle` (deux écrans + en-tête « · Changer de
  parcelle ») : refondu sur `EntreeParcelle` (un seul écran, champ → boîte remplie → rapport dessous ; la
  croix revient à la recherche). Le lien « Changer de parcelle » est **supprimé**.
- Les tests `EntreeParcelle.test.tsx` / `ClicCarte.test.tsx` sont mis à jour (plus de « Changer de parcelle » ;
  la croix `data-entree-vider` appelle `onChanger`).

## 2. Assemblage — espace, 4 lignes, libellés

Capture : **`p02-assemblage-bilan.png`** (BZ1065 + BZ0389 + BZ0798 + BZ0799, contiguës).

- **Espace tuiles ↔ « Bilan »** : la carte de résultat passe en `flex flex-col gap-2` → un espace **normal et
  constant** sépare les tuiles de « Bilan » (avant elles étaient collées, et « Bilan » ouvert empiétait).
- **Les 4 lignes du Bilan tiennent chacune sur une ligne** : libellé à gauche, valeur à droite ; la **précision**
  (€/m² de terrain, source DVF · fiabilité) passe **en dessous**, petite et alignée à droite, au lieu
  d'allonger la valeur et de la faire passer à la ligne. (Charge foncière estimée · Prix de sortie · Marché de
  la zone · la 4ᵉ ci-dessous.)
- **« Parcelles chiffrables 1/3 » → « Prix connu pour 1 parcelle sur 3 »** : libellé « Prix connu pour », valeur
  « N parcelle(s) sur M ». Vérifié WebKit : « Prix connu pour **1 parcelle sur 4** ».
- **« (approche plus lourde) » retiré** (ligne propriétaires). Vérifié WebKit : absent.
- **Phrase « Indivision : non détectable en open data… » retirée.** Vérifié WebKit : absente.
- **Titre « Étape 1 — » retiré** (une seule étape) → « Choisir les parcelles (N maximum) ». Vérifié WebKit :
  « Étape 1 » absent de la page.

## 3. Scan patrimoine — espace entre les deux chemins

Capture : **`p03-scan-chemins.png`**. Cause trouvée : la classe `.door` porte `margin-bottom:8px` ; les deux
chemins étaient dans `flex flex-col gap-2` **sans** `mb-0`, d'où 8 px (gap) + 8 px (marge) = **16 px**, le
double des autres outils (Communes, Solaire, qui mettent `mb-0`). Correctif : `mb-0` sur chaque `.door` → seul
le `gap-2` (8 px) compte, **même espace que partout ailleurs**.

## 4. Estimer — champ « surface habitable » saisissable, sans flèches

Capture : **`p04-estimer-surface.png`**. Le champ passe de `type="number"` (flèches haut/bas) à
`type="text" inputMode="numeric"` : **aucune flèche**, **clavier numérique** sur mobile, les non-chiffres sont
filtrés à la frappe. La valeur est **validée à la sortie du champ (blur) ou sur Entrée** — un brouillon local
(`surfaceDraft`) n'est reporté dans la valeur qui pilote l'estimation (`surfaceHab`) qu'à ce moment. Vérifié
WebKit : `type=text`, `inputmode=numeric`.

## 5. Gabarit 3D — les deux hauteurs écrites SUR la vue

Captures : **`p05-gabarit-3d-bz1065.png`** et **`p05b-gabarit-3d-ap1319.png`**.

Deux pastilles sont posées **sur la vue 3D** : **« Règle : X m »** (vert) et **« Bâti : N m »** (gris). Ce sont
des **Marker maplibre** (overlay HTML) : alignés sur l'écran (billboard), donc **droits et lisibles sous tous
les angles** (pitch/rotation). Détails techniques qui ont demandé deux corrections :
- le décalage écran passe par l'option **`offset`** du Marker, **pas** par un `transform` CSS sur l'élément
  (maplibre écrase le `transform` de l'élément par son propre transform de positionnement — sans quoi les
  pastilles se superposaient) ;
- les deux pastilles sont ancrées au **même point** (centre de la parcelle), séparées horizontalement (Règle à
  gauche, Bâti à droite) et verticalement **au prorata de la hauteur** → la pastille physiquement la plus haute
  s'affiche la plus haute, qu'il s'agisse de la règle ou du bâti.

**Le bâti est-il réellement à la hauteur de l'enveloppe ? NON — mesuré, il la DÉPASSE sur les deux parcelles.**
- **BZ1065** (demandée) : règle **7 m**, bâti existant **10 m** → le bâti dépasse la limite réglementaire
  actuelle.
- **AP1319 Saint-André** (2ᵉ témoin) : règle **17 m**, bâti **19 m** → même constat.

C'est cohérent et honnête : l'enveloppe verte est extrudée à la **hauteur MAXIMALE que la règle autorise
aujourd'hui** ; le bâti gris est extrudé à sa **hauteur RÉELLE mesurée** (LiDAR HD / BD TOPO). Quand une
construction est **antérieure à un abaissement du PLU**, elle peut donc **dépasser** l'enveloppe — ce n'est pas
un défaut de calcul, c'est « ce qui est là » vs « ce que la règle permet désormais ». Le texte d'explication du
panneau, qui affirmait à tort « le bâti est plus bas », est **réécrit en conditionnel** (sous / au-dessus / à la
hauteur) à partir des deux valeurs réelles.

> **Parcelle de la capture de Vic** : son IDU exact n'était pas fourni ; la vérification porte sur **BZ1065**
> (explicitement demandée) et un second témoin **AP1319 (Saint-André)**. Sur les deux, le bâti dépasse
> l'enveloppe — à confirmer sur l'IDU précis de Vic s'il nous le transmet (le mécanisme est générique).

## 6. Gabarit — règles non intégrées en UN SEUL bloc

Capture : **`p06-gabarit-regles-un-bloc.png`**. L'accordéon séparé « Le détail des N règles non intégrées »
(qui vivait dans la carte Couverture) **disparaît**. La **boîte jaune « ⚠ N règles applicables non intégrées »**
(sous « Voir les règles appliquées ») **DEVIENT l'accordéon** : son en-tête déplie **en dedans** le détail
complet (nom · pourquoi · source), exactement ce que renvoie le moteur (`nonIntegratedRules`), rien d'inventé.
Vérifié WebKit : **un seul** `[data-gabarit-non-integrees]`, situé dans « Voir les règles appliquées ».

## 7. Fiche parcelle — espaces noirs réduits autour des 6 tuiles

Capture : **`p07-fiche-tuiles.png`**. Les tuiles cumulaient un `marginTop:6` (inline) **et** un `padding:12px 0`
sur `.stats`, qui s'ajoutaient au `gap-3` (12 px) du conteneur défilant → ~30 px de vide noir au-dessus et
24 px au-dessous. Correctifs : `marginTop` retiré et `.stats` `padding:12px 0 → 0`. L'écart haut/bas des tuiles
vaut désormais **exactement le `gap-3` de la fiche** — le même rythme que le reste (entre sections).

---

## Fichiers touchés
**Front** : `outils/EntreeParcelle.tsx` (boîte option A) · `outils/AnalyserAnnonce.tsx` (Estimer : EntreeParcelle
+ champ surface) · `outils/moteurs.tsx` (Assemblage) · `outils/ScanPatrimoine.tsx` (chemins) ·
`outils/Gabarit.tsx` (hauteurs sur la vue + règles un bloc) · `outils/ModulePanel.tsx` (commentaire temps) ·
`components/fiche/Fiche.tsx` + `styles/index.css` (tuiles) · `lib/api.ts` (zone_plu) ·
`outils/EntreeParcelle.test.tsx` · `outils/ClicCarte.test.tsx`.
**Back** : `api/app.py` (`/parcels/search` → `zone_plu` dominante, joint après le LIMIT, gardé par
`_zone_plu_ready`).

## Reproduire les captures
Backend `PYTHONPATH=src …/.venv/bin/python -m uvicorn labuse.api.app:app --port 7210` · Vite
`LABUSE_API_DEV=http://127.0.0.1:7210 npx vite --port 10010` · `node /tmp/retours26-captures.mjs`
(+ `/tmp/retours26-fix.mjs` pour les vues 3D cadrées). Pilotage via `window.__labuse` (setModule/select/setMsel).

---
---

# Refonte — OUTILS-REFONTE-1 (5 outils sur maquettes validées)

Même branche `fix/retours-23`, **pas de merge** (commit seul). Captures **avant/après** WebKit dans
`captures/r-<outil>-avant.png` / `-apres.png`. Hook complet **VERT** : `tsc -b` 0 · vitest **326/326** ·
`vite build` OK · scan secrets OK · pytest unitaires **3259 passed** (49 skipped = famille base).

Règle d'or respectée partout : **aucun chiffre inventé** — chaque valeur vient du même lecteur
qu'aujourd'hui ; là où la maquette montrait une donnée que l'API NE sert PAS, on ne l'a pas fabriquée
(déviations listées plus bas, jamais un faux chiffre).

## Étape 0 — merge origin/main
`git merge origin/main` dans `fix/retours-23` : **aucun conflit textuel** (20 commits entrants —
ESTIMER-2, ECRANS-NOV-2, FONCIER-PUBLIC-1, FRAICHEUR-FIX-1, PLU-VEILLE-1…). `tsc`/vitest/pytest verts
sur l'arbre fusionné. **Estimer vérifié** (son API a changé avec ESTIMER-2, sans le refondre) : l'écran
rend la boîte parcelle + l'ordre de grandeur chiffré (capture `r-estimer-apres.png`) — il fonctionne.

## Pièges et risques (9a) — `r-pieges-*`
Compteur « **N contrainte(s) relevée(s) sur la parcelle** » ; une carte par contrainte (titre · badge
« sourcé » · une phrase · source · liseré gauche ambre/rouge) ; **« Vérifié, rien à signaler » en puces**
(familles examinées & CLAIRES) ; ligne « Non couvert » en bas. Le « rien à signaler » n'est **pas un faux
RAS** : `servitudes.py` sert `verifie` = familles RÉELLEMENT examinées (couches ingérées) moins celles qui
ont remonté quelque chose. BZ1065 : 3 contraintes (ANC · DPU · PPR) + 7 familles claires (Sols pollués,
Bruit, ICPE, Monuments, ER/EBC, Eau & zones humides, Espaces naturels) — Assainissement/Préemption/Risques
n'y sont PAS (ils ont déclenché). *Avant* : aucune section « vérifié » (0 puce).

## Gabarit (9b) — `r-gabarit-*`
**4 tuiles** (Zone d'implantation · Emprise maximale · Hauteur maximale · Surface parcelle) ; **règles en
lignes « libellé · valeur · badge »** ; **« Non intégrées » en puces** (remplace l'encadré jaune + son
accordéon) ; « Voir en 3D » / « Exporter en PDF ». Les sections en double (carte « Couverture · N familles »,
accordéon « Voir les règles appliquées ») **disparaissent**. La vue 3D et ses étiquettes de hauteur ne sont
**pas touchées** (leur explication reste en ligne discrète en bas). *Avant* : accordéon « Voir les règles »
+ carte Couverture + encadré jaune dépliable.
- **Déviation honnête** : la maquette montrait une 4ᵉ tuile « Plancher maximal / terrain libéré » — le
  moteur Gabarit ne sert **aucune SDP/plancher** → on garde la Surface parcelle réelle (pas de plancher
  inventé). Le **badge** des règles est la **zone PLU** (« Uh ») ou « mesuré » (règles BD TOPO) : le moteur
  ne sert **pas** le numéro d'article (`source.article = null`) — on n'invente donc pas les « Uh.7 / Uh.6 »
  dessinés sur la maquette.

## Taxe d'aménagement (9c) — `r-taxe-*`
« Votre projet » : **surface taxable** (champ saisissable, clavier numérique, sans flèches) · **Logement /
Autre** (segmenté) · **abattements à cocher** (Résidence principale · Logement social/PTZ) → **encadré
résultat** : total (gros, vert) · assiette (surface × valeur) · part communale · part départementale ·
redevance archéologie · note de valeur forfaitaire → **Exporter en PDF**. Le total reste **honnête** (jamais
inventé : si la commune n'a pas de taux public, message au lieu d'un total). BZ1065 · 120 m² → **5 887 €**.
*Avant* : formulaire long (nombre de logements, nature exonérée agricole/PLAI/reconstruction, forfaits
piscine/PV/stationnement/éoliennes, saisie manuelle des taux, accordéon « où trouver le taux »).
- **Simplification per maquette** : nb logements et taux manuels retirés (les taux restent **lus** du
  prefill). Le calcul back est le MÊME lecteur.
- **Correction (2ᵉ passe)** : les **forfaits** (stationnement · piscine · PV au sol · éoliennes) et les
  **exonérations** de plein droit (agricole · PLAI · reconstruction), retirés par erreur, sont **rétablis**
  dans un bloc **« Options » replié par défaut**, entre « Votre projet » et le résultat. Mêmes valeurs,
  même calcul ; le résultat se **recalcule** à chaque changement et la **ligne du poste apparaît dans le
  détail** (ex. « Stationnement extérieur (2 place(s) × 2 928 €) » → total 5 887 € → 6 209 €). Le **bouton
  « Exporter en PDF » est retiré** (une impression navigateur n'est pas un document LABUSE). Garde F28
  rétabli. Captures `r-taxe-options-replie.png` / `r-taxe-options-ouvert.png`.

## Blocs fonciers (9d) — `r-blocs-*`
**4 menus compacts** (commune · Surface · Plancher restant · Parcelles, en grille 2×2) · case « Inclure les
propriétaires publics » + « Réinitialiser » · **compteur « N blocs · personnes morales DGFiP »** · **cartes
cliquables SANS bouton** (dénomination · SIREN vert · commune · N parcelles · surface · plancher restant ·
zones). Un clic ouvre le bloc (parcelles · carte · **Scan patrimoine**/Assembler, désormais DANS le détail,
plus sur la carte). *Avant* : cartes avec chevron + 2 tuiles encadrées + boutons « Scan patrimoine → »/« Assembler ».

## Comparatif (9f) — `r-comparatif-*`
**3 colonnes avec en-tête** (IDU · commune · **bande LABUSE** · surface) ; les ~20 lignes regroupées en
**5 sections** (Terrain · Urbanisme · Potentiel · Risques · Marché) ; **meilleure valeur en vert** (déjà en
place, conservée) ; **badges allégés** (seules les valeurs estimées portent une puce « est. » discrète ;
les sourcées n'en portent plus) ; **export inchangé** (doc Comparatif). *Avant* : table plate sans sections,
en-tête IDU + chip « raison » + commune, badges « Sourcé/Estimé » sur chaque ligne.
- **Déviation honnête** : `/compare` ne sert PAS la pente, la hauteur en mètres, le nombre de logements, les
  permis à 500 m, ni l'adresse postale (dessinés sur la maquette). On ne les invente pas → on sert ce que le
  lecteur donne (gabarit en niveaux R+N, commune comme localité, « voir l'Étude de faisabilité » pour les
  logements). Les sections et le reste des lignes sont fidèles.

## Courrier — `r-courrier-*`
Délai par défaut **« envoi sous 3 à 5 jours »** (envoi depuis La Réunion), **lu de la config**
(`config.courrier_delai_jours = "3 à 5"`, servi par `/courrier/statut`, affiché dans l'intro). *Avant* :
« 7 à 10 jours ».

## Fichiers touchés (Refonte)
**Front** : `outils/blocB.tsx` (Pièges : compteur · liseré · puces vérifié) · `outils/Gabarit.tsx`
(4 tuiles · règles en lignes · non-intégrées en puces) · `outils/TaxeAmenagement.tsx` (refonte 9c + export) ·
`outils/Blocs.tsx` (4 menus · cartes sans bouton · détail porte les actions) · `compare/ComparePanel.tsx`
(5 sections · en-tête bande+surface · badges allégés) · `lib/api.ts` (commentaire délai).
**Back** : `api/servitudes.py` (`verifie` = familles examinées & claires) · `config.py` (délai 3 à 5).
**Tests** : `test_front_chiffres2_familles.py::test_f28` (aligné sur le retrait de l'UI agricole 9c).

---
---

# RETOURS-27 — recette de la refonte

Même branche `fix/retours-23`, **pas de merge**. Captures WebKit `r27-*.png` (une par point). Hook complet
**VERT** : `tsc -b` 0 · vitest **326/326** · `vite build` OK · scan secrets OK · pytest unitaires verts.
Règle d'or respectée : aucun chiffre inventé.

## 1. Boîte parcelle — tout d'un coup, sans icône (`r27-boite.png`)
Adresse + IDU + zone + surface arrivent **ensemble et quasi instantanément** (mesuré **~72 ms**), plus de
remplissage « à moitié ». Cause de l'ancien délai : la boîte ré-interrogeait l'omnibox (`/parcels/search`,
`ILIKE '%…'` qui **scanne l'île ~3 s** et n'affichait d'abord que l'IDU). Fix : nouvel endpoint **`/parcels/
apercu/{idu}`** (lookup **indexé** `p.idu = :idu`) + rendu **atomique** (ligne « chargement » tant que l'aperçu
n'est pas là, puis tout d'un coup). L'**icône ronde ◎** à gauche est retirée.

## 2. Pièges — liseré jaune fin + procédure PLU (`r27-pieges.png`)
Chaque carte a un **liseré jaune FIN tout autour** (plus de bord gauche épais ; rouge si rédhibitoire).
Si la commune a une **procédure PLU en cours** (lue du radar PLU `veille_plu`, MÊME source que l'outil « Vérif
procédure »), une **carte dédiée** l'indique (« Procédure PLU en cours · Révision générale du PLU — … ») et ce
point **QUITTE « Non couvert »** (le back le retire quand une procédure est servie). Vérifié sur Saint-André
(97409, révision prescrite).

### Géorisques — canalisations de transport de matières dangereuses à La Réunion (sans ingestion)
Vérifié (DEAL/DREAL Réunion « État de l'environnement industriel 2022 », DDRM Réunion, Géorisques) : **OUI, il
en existe** — uniquement des **oléoducs** (hydrocarbures / kérosène / GPL), **≈ 7,3 km, 3 exploitants** (dont
la SRPP), sur **deux communes : Le Port** (dépôt SRPP ↔ ports Est/Ouest) **et Sainte-Marie** (approvisionnement
kérosène de l'aéroport Roland-Garros), avec servitudes d'utilité publique (I1/I3). **Aucun** réseau de
**transport de gaz** (gazoduc). **Conclusion : le caveat « non couvert : canalisations de matières dangereuses »
reste PERTINENT pour 974** — un enjeu réel subsiste au Port et à Sainte-Marie ; on le garde dans « Non couvert »
(couche non ingérée). *(Réserve : la page Géorisques par commune est anti-bot ; chiffres = ordre de grandeur
DREAL ; « 2 communes · oléoducs seulement · pas de gaz » sont des faits en clair des sources d'État.)*

## 3. Gabarit 3D — faîtage LiDAR de parcelle, sans « dépasse » (`r27-gabarit3d.png`)
**Correction prise en compte** : la hauteur LiDAR n'étant **pas rattachée de façon sûre au bâtiment dessiné**
(elle peut provenir d'un bâtiment voisin au contact), le bâti n'est **plus extrudé** à cette hauteur (aucun
volume de bâti), et l'étiquette devient **« Faîtage LiDAR sur la parcelle : X m »** — une **valeur de parcelle,
non attachée à un volume** (offset fixe), quel que soit le nombre de bâtiments. L'enveloppe réglementaire reste
en volume vert avec « Règle : X m » (hauteur = une RÈGLE, fiable). **Aucune phrase « dépasse la règle »** ni
« antérieure à une limite PLU abaissée » (retirées). Vérifié BZ1065 : « Règle : 7 m » · « Faîtage LiDAR sur la
parcelle : 10 m ».
**« ~½ en médiane » — calcul & échantillon donnés** (traçable, dans le « i ») : médiane du ratio
*autorisé / maximum réglementaire* = **0,46 en surface (0,40 en logements)**, mesurée sur **6 601 permis
réellement autorisés post-PLU (Sit@del)**.

## 4. Taxe (`r27-taxe.png`)
« Logement social ou financé par un PTZ » → **« Logement social aidé »** (libellé exact de l'abattement) ;
**« exigible au permis » retiré** ; note = **« Valeur forfaitaire 2026 : 892 €/m² · taux communal 3 % · taux
départemental 2,5 % »** ; **« Non pris en compte » passe dans le « i »** ; **virgules décimales** (2,5 % · 0,4 %) ;
le total **ventile** « Taxe d'aménagement » (5 887 €) · « Redevance d'archéologie préventive · 0,4 % » (428 €) ·
**« Total à prévoir »** (6 315 €) ; la ligne « Terrain : … (référence cadastrale) » est **retirée**.

## 5. Blocs fonciers (`r27-blocs.png`)
**4 menus en grille 2×2** (commune · Surface · Plancher restant · Parcelles, sans chevauchement) ; case
« propriétaires publics » **et** « Réinitialiser » **sur une ligne** ; compteur ; **liste affichée tout de
suite**, mise à jour à **chaque filtre** ; le bouton **« Voir les parcelles » est retiré**.

## 6. Comparatif (`r27-comparatif.png`)
Badges **en toutes lettres** (« sourcé » / « estimé ») sur **chaque ligne** ; en-têtes de colonnes
**homogènes** (« N/M sous 1 an » retiré) ; **« Signal faible » → « Vente : faible »** ; **« Détail contraintes »
replié par défaut** (bouton ▸ qui déplie).

## 7. Assemblage (`r27-assemblage.png`)
**Bilan ouvert par défaut** ; **« Prix connu pour 1 parcelle sur 4 » sur une seule ligne** (phrase continue) ;
le bouton **« Étude de faisabilité de cet assemblage » déplacé tout en bas**, après la liste des parcelles.

## Fichiers touchés (RETOURS-27)
**Front** : `outils/EntreeParcelle.tsx` (aperçu rapide, atomique, sans icône) · `outils/blocB.tsx` (Pièges :
liseré · carte procédure) · `outils/Gabarit.tsx` (faîtage LiDAR, pas d'extrusion bâti, ~½ tracé) ·
`outils/TaxeAmenagement.tsx` (libellés · note · virgules · total ventilé) · `outils/Blocs.tsx` (2×2 · liste
immédiate) · `compare/ComparePanel.tsx` (badges · en-têtes · Vente · détail replié) · `outils/moteurs.tsx`
(Assemblage) · `lib/api.ts` (`getParcelApercu`).
**Back** : `api/app.py` (`/parcels/apercu/{idu}` indexé) · `api/servitudes.py` (`procedure_plu` + retrait du
« Non couvert »).

---
---

# RETOURS-28 — dernière recette des outils

Même branche `fix/retours-23`, **pas de merge**. Captures WebKit `r28-*.png`. Hook complet **VERT** :
`tsc -b` 0 · vitest **326/326** · `vite build` OK · scan secrets OK · pytest **3259 passed**.

## Pièges (`r28-pieges.png`)
« Non couvert » réduit à **UNE ligne fixe** : « Non couvert : oléoducs (Le Port, Sainte-Marie) et servitudes
non publiées au Géoportail. Le certificat d'urbanisme fait foi. » ; le **détail** (couches non ingérées,
servi par l'API) passe dans le **« i »**. Les **procédures PLU n'y figurent plus jamais** (`servitudes.py` les
retire toujours de `non_couvert`). Quand la commune n'a **pas** de procédure en cours, une **puce « Procédure
PLU »** apparaît dans « Vérifié, rien à signaler » (vérifié WebKit : puce présente, « Procédures PLU » absent
de la ligne Non couvert).

## Gabarit (`r28-gabarit.png`)
« Faîtage LiDAR sur la parcelle : X m » **quitte la vue 3D** (le marqueur gris est retiré ; seule « Règle : X m »
reste sur l'enveloppe verte) et devient **une ligne du panneau, sous les tuiles** (« Faîtage LiDAR sur la
parcelle · 10 m » pour BZ1065). La phrase du bas devient : **« En pratique, les permis délivrés utilisent
environ la moitié de ce maximum (médiane sur 6 601 permis). »**

## Blocs fonciers (`r28-blocs.png`)
Les filtres sont **quatre boutons-menus dont le libellé est DANS le bouton** (« Toute l'île ▾ », « Surface :
toutes ▾ », « Plancher restant : tous ▾ », « ≥ 2 parcelles ▾ »), en **grille de 2 colonnes égales**
(`wrapClassName="w-full"`), sans libellé extérieur. Vérifié WebKit : **aucun des 4 n'est tronqué**
(`scrollWidth ≤ clientWidth`), rien de superposé.

## Comparatif (`r28-comparatif.png`)
- **Colonne dédiée aux badges « sourcé »/« estimé »**, entre le libellé et les valeurs (vérifié : ligne
  « Surface » = [Surface][sourcé][1 567 m²]).
- Ligne **« Logements possibles » retirée**.
- **Aucun vert en cas d'égalité, ni sur une valeur nulle ou négative** (`bestIdx` : meilleur unique et > 0 ;
  vérifié : « Taux d'occupation » min = 0 % non vert ; « Charge foncière » négatives non vertes, seule la
  valeur positive l'est).
- Un **clic hors du tableau**, ou **Échap**, le ferme (vérifié WebKit : clic sur le fond ferme l'overlay).
- **« Gabarit max R+0 » en zone Uh corrigé** : égout 4,5 m ÷ 3 = 1 niveau plein (R+0) mais le faîtage à 7 m
  laisse **2,5 m de combles aménageables** → l'affichage devient **« R+0 + combles »**. Ni inventé ni un étage
  de plus : un fait du règlement (faîtage 7 m / égout 4,5 m, vérifié `/outils/gabarit`). Nouveau drapeau
  `combles` servi par le moteur (`engine.py`/`residuel.py`), display-seul (aucun calcul de SDP n'en dépend).
  Vérifié live : BZ1065 (Uh) → `combles=True` → « R+0 + combles » ; DH0076 → « R+4 + combles » ; AK0804 → « R+3 + combles ».

## Assemblage (`r28-assemblage.png`)
Pluriels **résolus, plus de « (s) »** : « 1 personne morale », « 3 propriétaires particuliers » (vérifié :
« 0 personne morale · 4 propriétaires particuliers », aucun « (s) »). La tuile dit **« Bâti conservé : X m² »**
et, dessous, **« Reconstruction : Y m² »** (SDP table rase). Le **« · terrain libéré » répété** dans les lignes
de parcelles est **retiré** (dit une seule fois dans la tuile).

## Fichiers touchés (RETOURS-28)
**Front** : `outils/blocB.tsx` (Pièges) · `outils/Gabarit.tsx` (faîtage en panneau + phrase) · `outils/Blocs.tsx`
(4 boutons-menus) · `compare/ComparePanel.tsx` (colonne badges · retrait Logements · vert strict · clic-dehors ·
R+N+combles) · `outils/moteurs.tsx` (Assemblage) · `lib/api.ts` (`gabarit_combles`).
**Back** : `api/servitudes.py` (PLU hors Non couvert) · `api/app.py` (`gabarit_combles` servi) ·
`faisabilite/engine.py` + `faisabilite/residuel.py` (drapeau `combles`).
**Tests** : `Assemblage.test.tsx` (Bâti conservé/Reconstruction) · `test_capacite_max.py` (mention Gabarit en
phrase littérale ; Comparatif sans la ligne Logements).

---

# RETOURS-29 — recette (même branche `fix/retours-23`, pas de merge, WebKit, capture par point)

## Comparatif v2 (`r29-comparatif.png`) — refonte selon `docs/design/maquettes/nov-2026/15-comparatif-v2.png`
Le tableau est **reconstruit sur la maquette**, sans rien inventer (seules les lignes servies par `/compare`).
- **Aucun classement LABUSE, aucune puce de vente** — ni en en-tête, ni sur les lignes. L'analyse reste dans
  son écran (vérifié : `classement:false`).
- **Colonne étroite en 2ᵉ position** (juste après le libellé) portant le badge de la ligne : **« sourcé »**
  (contour vert) pour une donnée publique, **« estimé »** (contour ambre) pour un calcul de LABUSE.
- **Pied** : « sourcé : donnée publique · estimé : calcul de LABUSE. Un clic sur une contrainte en affiche
  le détail. » (vérifié : `pied:true`).
- **En-tête de colonne** : identifiant (gras) + croix **✕**, **adresse** (aperçu parcelle, lookup BAN servi
  par `/compare`), **zone · surface**, lien **« Ouvrir la fiche → »** (vérifié col. 1 :
  `97415000DH0076 ✕ · 104 Avenue de Bourbon, 97434 Saint-Paul · U2b · 19 513 m² · Ouvrir la fiche →`).
- **Point vert + fine barre proportionnelle** sur les lignes chiffrées — **meilleure valeur unique** de la
  ligne ; **rien en cas d'égalité, ni sur une valeur nulle ou négative** sauf quand 0 EST la meilleure d'une
  ligne « au moins » (Bâti existant « ● aucun », Part du gabarit « ● 0 % ») ; les charges foncières négatives
  ne sont jamais vertes, seule la positive l'est (vérifié : 9 barres, « ● 7 €/m² » vert, −112/−20 €/m² non).
- **Contraintes relevées en puces**, détail au clic (vérifié : `contraintePuce:true`).
- **Fermeture au clic extérieur et à Échap** conservée (vérifié : clic sur le fond ferme l'overlay).
- **Export PDF identique** (`exports/blocs/comparatif.py`) : mêmes 11 lignes, même ordre, mêmes badges
  sourcé/estimé, même en-tête (IDU · adresse · zone · surface), plus de classement / prix de marché /
  logements. Sections : Terrain · Urbanisme · Potentiel constructible · Risques et contraintes.

## Blocs fonciers (`r29-blocs.png`)
- Compteur **« 6 357 blocs appartenant à des sociétés · 4 865 blocs publics masqués »** ; la **seconde partie
  disparaît quand la case « inclure les propriétaires publics » est cochée** (vérifié WebKit : décochée →
  `6 357 … · 4 865 blocs publics masqués` ; cochée → `11 222 blocs appartenant à des sociétés`).
- Le bouton **« Plancher restant : tous » n'est plus jamais tronqué** (les 4 boutons-menus en `w-full`,
  `text-[10px]`, libellé embarqué dans l'option).

## Pièges (`r29-pieges-nc.png`)
- Le **« i »** est **à la fin de la phrase « Non couvert … »**, **sur la même ligne** (inline, plus de retour
  à la ligne) : « … Le certificat d'urbanisme fait foi. ⓘ » (vérifié : `memeLigne:true`, bas du « i » ≈ bas
  de la dernière ligne de texte).

## Assemblage (`r29-assemblage.png`)
- La surface d'assiette tient **sur une seule ligne** (« 196 m² » ne se coupe plus — `whitespace-nowrap` sur
  la valeur ; vérifié : « 5 574 m² » / tuiles « 0 m² » / « 762 m² » non coupées).
- **« 0 personne morale » n'est plus affiché** : la mention « N personne(s) morale(s) · » n'apparaît que si
  N > 0 (vérifié : « 4 propriétaires particuliers », sans préfixe).
- Lignes de parcelles au format **« 468 m² · bâti conservé 0 m² · reconstruction 84 m² »** (vérifié :
  « BZ0389 · 1 960 m² · bâti conservé 0 m² · reconstruction 265 m² », idem BZ0798/BZ0799).

## Fichiers touchés (RETOURS-29)
**Front** : `compare/ComparePanel.tsx` (refonte v2 : 4 sections, colonne badges sourcé/estimé, en-tête IDU ·
adresse · zone · surface + « Ouvrir la fiche → », point vert + barre proportionnelle, retrait classement/vente)
· `outils/Blocs.tsx` (compteur « N publics masqués » conditionnel) · `outils/blocB.tsx` (« i » inline en fin
de « Non couvert ») · `outils/moteurs.tsx` (Assemblage : surface `nowrap`, « 0 personne morale » masqué) ·
`lib/api.ts` (`adresse` sur `CompareRow`).
**Back** : `api/app.py` (`adresse` BAN servie par `/compare`) · `exports/blocs/comparatif.py` (PDF aligné sur
la maquette v2).
**Tests** : `test_bandes_unifiees.py` (classement ABSENT du panneau) · `test_capacite_max.py` (« maximale
réglementaire » dans la ligne ; ligne Logements retirée) · `status.bandes.test.ts` (classement absent).

**Hook complet vert** : `tsc -b` 0 · `vitest` 326 · `npm run build` 0 · `scan_secrets` rien · `pytest`
3 259 passés (49 skipped). Commit sur `fix/retours-23`, **pas de merge**.
