# RETOURS-13 — 7 retours de recette (fiche, scan patrimoine, 3D, couches, terrain)

Mandat d'exécution sur les captures du 24/09 au soir. Branche `fix/retours-13`
(worktree `~/Desktop/labuse-retours13`, base `main`), **non mergée**. Un commit par
point, captures avant/après dans `captures/`.

| Commit | Point |
|---|---|
| `c5a3312a` | P1 — en-tête de fiche à deux boutons |
| `59db9d15` | P2 — Potentiel : « Expliquer ce calcul en clair » retiré |
| *(déjà conforme)* | P3 — Scan patrimoine : « Voir ses parcelles » |
| `6a61f662` | P4 — 3D : chip « Bâtiments » |
| `b6f581c3` | P5 — couche « Courbes de niveau » |
| `9118bdd6` | P6 — Terrain : profil altimétrique |
| `c8c87542` + `9cac3724` (fix) | P7 — en-tête de fiche collé |

**Vérification** : `tsc -b` vert · `vite build` vert · **vitest 187/187** · pytest
profil **4/4** + faisabilité **19/19** (23/23), app importe. Aucune rupture nouvelle.

---

## 1. En-tête de la fiche : deux boutons, pas trois

**Fait.** « Synthèse IA » supprimée (bouton + panneau `SyntheseIAPanel` + mutation
`getExplain`). Il reste, sur **une seule rangée** (`.ia`, flex), **même hauteur**
(charte `Bouton`, 32 px) :

- **« Demander à LABUSE d'analyser la parcelle → »** — principal, plein, vert
  (`Bouton niveau="primaire" ton="vert"`) ;
- **« Poser une question »** — secondaire (`niveau="secondaire" ton="ia"`), ouvre le
  Copilote (AskBar) juste dessous.

`Fiche.tsx` : les deux boutons vivent désormais dans le bloc Analyse (le bouton
d'analyse et la carte de verdict sont adjacents) ; l'ancienne rangée `data-ia-tete`
plus bas est supprimée.

### « Analyser » lit-il le scoring SERVI ? — oui, aucune version codée en dur

La chaîne, fonction par fonction :

1. Le clic appelle **`revelerVerdict(idu)`** (`store/useApp.ts`) — un simple drapeau
   de session qui **révèle** `f.analyse_labuse` (aucun appel réseau propre).
2. `f` vient de **`getFiche(idu)`** (`lib/api.ts:387`) =
   `GET /parcels/{idu}?source=${SOURCE}`.
3. **`SOURCE`** (`lib/api.ts:22`) = `import.meta.env.VITE_RUN_LABEL`, injecté au build
   depuis **`config/served_run.txt`** (`vite.config.ts`) — le point de vérité unique du
   run servi.

Aujourd'hui `served_run.txt` = **`q_v11_m137`** ; la fiche sert donc le scoring de ce
run. À la bascule (page Données / Circuit → `bascule_flux.basculer()`), `served_run.txt`
passe à `q_v15`, `SOURCE` suit, et la fiche lit le nouveau score **sans changement de
code**. Il n'existe **aucun littéral `q_v11`/`q_v15`** dans le front (hors fixtures de
test admin).

Captures : `captures/P1-entete-2-boutons.png`, `captures/P7-entete-haut.png` (les deux
boutons côte à côte).

---

## 2. Potentiel : « Expliquer ce calcul en clair » retiré

**Fait.** Le bouton violet IA sous les 11 (ici 12) étapes, et son encart `AvisIA`, sont
supprimés de `FaisabiliteTab` (`constructibilite.tsx`). Ce composant étant **partagé**
entre la fiche (tiroir Potentiel) et l'outil Faisabilité (M22), le bloc part des deux —
un bloc, un rendu. Le Copilote reste accessible par « Poser une question » (P1).

Nettoyage : mutation `explain`, `ex`, imports `faisabiliteExplain`/`AvisIA`/`renderRich`/
`Bouton` retirés ; prop `embedded` conservée au type (compat appelants). Le test
`Faisabilite.test.tsx` (Lot F) est réécrit : le bouton est désormais **absent en fiche
comme dans l'outil** (6/6).

Capture : `captures/P2-potentiel-sans-bouton.png` — les étapes du calcul vont
directement aux « HYPOTHÈSES (MODIFIABLES) », sans bouton violet entre les deux.

---

## 3. Scan patrimoine : « Voir ses parcelles → » — DÉJÀ CONFORME

**Aucun changement nécessaire.** Le bouton (`ModulePanel.tsx:316`,
`data-scan-voir-parcelles`) est **déjà** la charte :
`<Bouton niveau="secondaire" ton="vert">`. Le « contour vert fin » décrit par Vic **est
exactement** le rendu d'un `Bouton` secondaire vert (`border-mint text-mint`, fond
transparent). La conversion a été faite en **RETOURS-12 O5** (04/09), soit **avant** les
captures du 24/09 — la capture de recette montrait vraisemblablement une build déployée
antérieure.

Vérifié à l'écran (`captures/P3-voir-ses-parcelles.png`, `captures/P3-scan-patrimoine.png`) :
c'est bien le composant de la charte, même geste (replie le bandeau → ouvre la liste),
même fil de retour. Rien à remplacer.

---

## 4. 3D : le bâti en option (chip « Bâtiments »)

**Fait.** Nouveau **chip « Bâtiments »** (charte `Chip`, vert), **visible uniquement en
mode 3D**, **on par défaut**. Off → relief seul, bâti à plat.

- État de **session** (store `batiVisible` + `setBatiVisible`, pas en base).
- **Carte principale** (`MapView.tsx`) : la couche `fill-extrusion` `batiments-3d` n'est
  chargée/affichée que si `terrain3d && batiVisible`.
- **Outil Gabarit** (`Gabarit.tsx`) : `gabarit-bati-3d` (bâti existant GABARIT-6) suit le
  **même chip** ; off → l'empreinte 2D grise (`gabarit-bati`) demeure = « bâti à plat ».

Captures : `captures/P4-3D-batiments-ON.png` (bâti extrudé sur Saint-Denis, chip vert),
`captures/P4-3D-batiments-OFF.png` (même vue 3D, bâti à plat, chip décoché),
`captures/P4-chip-ON.png`.

---

## 5. Couche « Courbes de niveau »

**Fait.** Nouvelle couche **raster** dans le strip des couches (famille Environnement),
**off par défaut**, avec légende + source + millésime.

### Source retenue

**IGN Géoplateforme — WMTS `ELEVATION.CONTOUR.LINE`** (TileMatrixSet `PM_6_18`, PNG,
dérivée du RGE ALTI). **Couverture 974 vérifiée avant de choisir** : la tuile z14 sur La
Montagne renvoie un PNG RGBA à **19,5 % de pixels de ligne** (teinte bistre mesurée
`#CC8066`). Le repli « dériver du RGE ALTI en base (isolignes 5 m MVT) » n'a donc **pas**
été nécessaire — la couche IGN est servie pour La Réunion.

- **Back** : route dédiée `GET /map/tiles/contours/{z}/{x}/{y}` (`ortho_proxy.py`) qui
  **relaie le PNG brut** (lignes transparentes) + cache disque — *pas* le pipeline ortho
  (fondu de côte / masque mer) qui prendrait la transparence pour du no-data.
- **Front** : le tuyau back ne sert que du vecteur ; la couche est donc déclarée côté
  client (`COURBES_NIVEAU_COUCHE`, `geometrie: 'raster'`) et **fusionnée au plan** → elle
  apparaît dans le panneau et la légende comme les autres. Montage spécialisé raster
  (source + calque `raster`, visibilité suivant le toggle).
- **`data_sources`** : la couche affiche sa source + son millésime dans le « i »
  (« IGN Géoplateforme, WMTS ELEVATION.CONTOUR.LINE, dérivée du RGE ALTI, millésime
  2025 »). Le **référentiel RGE ALTI est déjà au catalogue `data_sources`** (« RGE ALTI
  (altimétrie) », IGN / Géoplateforme). ELEVATION.CONTOUR.LINE en étant le rendu
  cartographique, **aucune ligne doublon n'a été créée** — la doctrine du catalogue
  aliase justement les doublons RGE ALTI (`ALIAS_CANONIQUES`).

Captures : `captures/P5-courbes-carte.png` (courbes bistre sur le relief + légende
« Courbes de niveau · Ligne de niveau »), `captures/P5-courbes-panneau.png` (la couche
dans le strip, famille Environnement).

---

## 6. Terrain : profil altimétrique

**Fait.** Section **repliable « Profil altimétrique »** dans le tiroir Terrain :

- **Graphique SVG** (altitude/distance, DA) le long du **plus grand axe** de la parcelle
  (`ST_LongestLine`).
- **5 chiffres** au vocabulaire **cartes.gouv** : distance, dénivelé positif, dénivelé
  négatif, **pente moyenne** (= grade absolu moyen = (D+ + D−) / distance), **plus forte
  pente** (+ altitude min/max).
- **« Tracer un autre profil »** → dessine une ligne sur la carte (nouvel outil `profil`
  qui réutilise la machine à mesurer ; Entrée valide) et **recalcule** le long du tracé.

### Lecture des données

Calcul **live, rien en base**. Endpoints `GET /parcels/{idu}/profil-altimetrique` (axe
parcelle) et `POST /parcels/profil-altimetrique` (ligne dessinée). Ils lisent le **RGE
ALTI en base** (`rgealti_mnt_5m`, 5 m, SRID 2975) — **le même relief que la pente de la
fiche** ; là où la base n'a pas la tuile (emprise non ingérée en dev), ils **complètent
au service de calcul d'altitude IGN** (`connectors/rge_alti`), *même RGE ALTI*, lecture
pure. La fonction de statistiques `stats_profil` est pure et **testée** (4/4).

### Recette / témoin BZ1065

- Axe de la parcelle (72 m) : **pente moyenne 10 %**, plus forte 32,3 %, altitude
  401–405 m, D+ 3,3 m / D− 4 m.
- Ligne dessinée **~424 m** en travers de la parcelle : **pente moyenne 18,6 %** →
  **concorde** avec cartes.gouv (~20 % de pente moyenne sur ~300 m). L'ordre de grandeur
  est bon.

> Note environnement : la base de dev ne contient que 2 tuiles RGE ALTI de démonstration
> (sans donnée exploitable, hors emprise des parcelles) ; c'est le **repli IGN** qui a
> fourni les altitudes réelles ci-dessus. En production, le raster complet est servi et le
> chemin base prime (rapide).

Capture : `captures/P6-profil-altimetrique.png`.

---

## 7. Fiche : en-tête sticky

**Fait.** Le bloc identité (PARCELLE · commune, IDU, adresse, icônes et croix de
fermeture) **reste collé en haut** au défilement — un client ferme la fiche sans
remonter. **Seul ce bloc colle** : les 6 tuiles passent dans une carte séparée qui
**défile** (mandat : pas les tuiles).

- Nouvelle classe `.tete-collee` (`position:sticky; top:0; z-20`, fond opaque + ombre) —
  le bloc collé est un **enfant direct du conteneur défilant** (sinon il décolle avec son
  parent) et **n'est plus dans la carte `.head`** (`overflow:hidden` clipperait le
  sticky). FINITIONS-2 avait annulé un sticky qui embarquait aussi les tuiles ; corrigé.
- **Bug trouvé à la recette et corrigé** (`9cac3724`) : la carte des tuiles, devenue
  enfant flex direct avec `overflow:hidden`, s'écrasait à 1 px (taille mini flex = 0) et
  clippait les 6 tuiles → **`shrink-0`** rétablit sa hauteur (139 px, 6 tuiles présentes).
- La **fiche commune** (`ContextePanel`) ne partage pas cet en-tête → non affectée.

Vérifié : en défilant de 1100 px, `tete.top` reste constant (60 px) ; les 6 tuiles
disparaissent sous l'en-tête collé.

Captures : `captures/P7-entete-haut.png` (haut de fiche), `captures/P7-entete-colle-apres-defilement.png`
(en-tête identité collé, tuiles défilées, tiroirs qui passent dessous).

---

## Hors mandat (non touché)

Le scoring lui-même · les autres outils · les exports · le merge de la branche.
