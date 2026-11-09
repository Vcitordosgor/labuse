# ECRANS-NOV-1 — cinq écrans sur maquettes validées

**Branche** `feat/ecrans-nov-1` (worktree `~/Desktop/labuse-ecrans`) · **front only, zéro prod, pas de merge.**
Ports de travail : front `:9950`, API `:7150`. Maquettes de référence : `docs/design/maquettes/nov-2026/` (5 PNG).
Captures avant/après : `docs/audit-2026-11/ecrans-nov-1/captures/{avant,apres}/`.

## Étape 0 — prérequis

Vérifié **avant toute écriture** : `fix/retours-17` (`32ea0d89a`, `498451e0b`) **et** `feat/docs-da-1`
(`4a8f5409c`→`e2be6ded6`, merge `be5c2d377`) sont **dans `origin/main`**. La branche a été mise à jour
(`git merge origin/main --ff-only`) pour bâtir SUR le travail DOCS-DA-1 (la source d'ordre `sections.yaml`,
les 15 faits du Dossier). Feu vert.

## Hook — VERT

- `npx tsc -b` : **0 erreur**.
- `npx vitest run` : **308 / 308** (65 fichiers). 1 test mis à jour (`EtudeDocs.test.tsx`, cf. §4).
- `npx vite build` : **✓** (avertissements chunk-size pré-existants, non bloquants).
- `scripts/ci/scan_secrets.sh` : **rien trouvé**.
- Python unitaires (sans base, venv `~/Desktop/labuse/.venv`) : **3193 passed, 49 skipped** (les skips
  exigent la base — hors mandat front). Aucun fichier Python touché → suite inchangée.
- Cohérence (12 témoins) : NON rejouée (exige la base locale) — mais **aucune valeur de donnée n'a changé**
  (le mandat ne touche QUE la mise en page et les libellés, jamais un chiffre servi), donc sans objet.

---

## Écran 1 — Fiche parcelle (`1-fiche-parcelle.png`)

Fichiers : `components/fiche/Fiche.tsx`, `AnalyseLabuseCard.tsx`, `primitives.tsx`, `styles/index.css`,
`frontend/vite.config.ts`, `src/vite-env.d.ts`.

- **En-tête aéré** : plus d'espace entre la référence, l'adresse et le secteur (`ref-sous-actions`
  9→14 px, `addr-row`/`sect-line` 6→10 px). Trait vertical déjà retiré (RETOURS-17) ; chevron des
  tiroirs déjà « noir sur vert au survol » (`ChevronSection`, inchangé).
- **Six gros chiffres au style de la fiche commune** : valeur en **mono d'abord**, puis le libellé, puis
  la **source** (`Surface → Cadastre`, `Zone → PLU · constructible`, `Pente → RGE ALTI · 25 %`, …). La
  valeur passe au-dessus du libellé (`.stat-v` avant `.stat-l`), le détail « Dessin du plan » descend
  dans l'infobulle. (Tuiles `data-bandeau-chiffres`.)
- **Deux boutons côte à côte, même taille** : « Analyse LABUSE » (vert) **reste** affiché à côté de
  « Copilote » (mauve) **même une fois l'analyse révélée** (avant il disparaissait) — la carte se déploie
  dessous.
- **Carte d'analyse refaite** (`AnalyseLabuseCard`) : la **bande en grand** (22→28 px), le **signal ET
  la zone en puces sur une ligne** (ajout de la puce « zone U »), « Ce qui compte », et un **pied**
  « Classer par : **potentiel** · chance de vente » (→ révèle l'analyse + ferme la fiche = tri des
  résultats) et « Comprendre l'analyse » (ouvre le panneau pédagogique, modale locale). **Aucun
  identifiant de run.**
- **Ordre des sections = sections.yaml, miroir du Dossier** : `declarations/fiche/sections.yaml` est
  **parsé au build** (`vite.config.ts` → `VITE_FICHE_SECTIONS`), plus codé en dur. `Fiche.tsx` en dérive
  `SECTION_ORDER`/`SECTION_LABELS` et range ses tiroirs par **flex `order`** (ajout d'une prop `order`
  à `RefDrawer`). Ordre servi **vérifié live** : Identité · Urbanisme · Potentiel · Risques et
  environnement · Terrain · Bâti · Réseaux et desserte · Marché · Fiscalité et dispositifs · Quartier.
  Les **groupes silencieux** (« Le bien / Le droit du sol / Le marché / Le projet ») sont retirés (la
  fiche est à plat, comme le Dossier) ; le pied (mentions + signalement) = « Limites et sources », §11.
- **Faits DOCS-DA-1 à l'écran** : la fiche lit les mêmes sections (via `getFiche`, le même robinet que
  le Dossier) ; les faits ajoutés au Dossier qui ont une surface fiche apparaissent dans leurs tiroirs
  (Terrain/Marché/Bâti/Réseaux…) par ce même lecteur — aucune valeur recalculée au front.

---

## Écran 2 — Filtres et Analyse (`2-filtres-analyse.png`)

Fichiers : `components/panel/FiltreLabuse.tsx`, `ResultsSection.tsx`, `LeftPanel.tsx`.

### Panneau des filtres
- **Un seul état sélectionné partout** : vert **opaque**, texte sombre, **coche à droite** (nouveau
  composant `LigneChoix`) ; plus de liseré/encoche. L'état du sol et le zonage gardent le `Chip` opaque
  (coche).
- **Communes en LISTE** (plus de pastilles), « **Toutes les communes** » en tête **et par défaut**
  (sélectionnée quand aucune commune cochée), **sans recherche**. Les ex-« Ajouter/Retirer tout » sont
  retirés.
- **Chaque catégorie en accordéon numéroté** (`AccordionCat`) : « 1 · Communes », « 2 · Le terrain »,
  « 3 · Le propriétaire » (titre + « i » + chevron à droite, teaser « forme juridique… » au repli). Les
  sous-catégories zonage (U/N/A/AU) restent des rangées extensibles (`ZoneSelector`).
- **Pied** : « **N parcelles correspondent à vos critères** » (déjà servi), puis « **Analyser avec
  LABUSE** » en **primaire**, « **Voir la liste** » et « **Réinitialiser** » dessous. La ligne
  « N à instruire · N écartées » est **retirée**.

### Écran d'analyse
- Phrase « **Classées selon vos critères et l'analyse LABUSE** (potentiel à bâtir, risques, accès,
  terrain) ». Boutons « **← Changer les filtres** » et « **Comprendre l'analyse** » (ex-« Retour » /
  « Comprendre »). Barre de répartition + légende (déjà présentes). Bloc **Score LABUSE / Signal de
  mutation** (état « Tous » vert opaque).
- Sur **chaque parcelle** (`AnalyseCard`) : les trois puces **bande · signal · zone sur une ligne**, le
  signal écrit « **Faible** » **sans « Signal »**. La **ligne démolition est neutre** : « **bâti existant
  sur N % de la parcelle — à prendre en compte** » (marqueur `•`, teinte grise, plus de ▼ négatif).
- **« Classer par »** (bloc Score/Signal, 3e rangée) : **Potentiel à bâtir** (défaut) · Chance de vente ·
  Surface, survol vert. **Côté serveur** (`app.py`, `_Q_V2_ORDERS`/`_Q_V2_ORDERS_PAGE` + validateur
  `/filtre`) : trois clés de tri `labuse_potentiel|labuse_vente|labuse_surface`, toujours **DANS la
  bande** (`_BANDE_RANG_SQL` ASC en 1er critère) — potentiel = `sdp_residuelle_m2 ↓`, vente = `signal_p ↓`,
  surface = `COALESCE(contenance, surface) ↓`, `idu` ferme l'ordre. `SortKey`/`ClasserKey`/`CLASSER_SORT`
  (api.ts), `getAnalyse` passe `classer`, la liste ET les groupes de fin (`AnalyseBandeGroup`) suivent.
  **L'ancien tri « Usage » (Va se vendre / À construire) est RETIRÉ de l'écran.** Vérifié live : bande
  d'abord, puis la clé décroissante (ex. Surface → 608 616 > 430 402 > 344 306…), et au back (Entre-Deux /
  Saint-Paul). Sort inconnu → 422.

**Partiel / non fait (écran 2)** — à arbitrer avec Vic :
- « Même phrase pendant l'animation de chargement » : la phrase est sur l'encart d'analyse ; le décompte
  (3 s) garde son texte propre.

---

## Écran 3 — Accueil / panneau « Cartes » (`3-accueil.png`, 342 × 640)

Fichier : `components/panel/LeftPanel.tsx`, `styles/index.css`.

- **Six entrées identiques de 58 px** (hauteur fixée en CSS) : Explorer la carte · Suivre le marché —
  Radar · **Générer un document** (ouvre Docs) · Ouvrir un outil · Demander au Copilote (mauve) · **Voir
  les données** (ouvre la section Données). Sous-titres coupés par des points de suspension (`truncate`).
- Deux icônes ajoutées (`document`, `donnees`). **« Par où commencer » et la ligne de pied retirées.**
- « Voir les données » affiche un **compte de sources** (`${n} sources, au même endroit`, lu de
  l'endpoint accueil déjà dédié) — un compte, **pas** la pastille de fraîcheur retirée par
  PAGES-RANGEMENT-1 ; compte absent → libellé neutre. **Tout tient sans défilement** (vérifié live).

---

## Écran 4 — Documents (`4-documents.png`)

Fichiers : `components/documents/DocumentsView.tsx`, `catalogue.ts`.

- **La parcelle choisie UNE fois en haut** : champ de recherche (`PickerParcelle`), puis référence +
  adresse + zone + surface + bouton « **Changer** ». Amorcée une fois avec la sélection courante.
- **Dix cartes en QUATRE COLONNES par usage** (+ 1 carte-note « même moteur » = onze cartes) :
  Comprendre la parcelle (Dossier · Gabarit · Estimation) · Chiffrer un projet (Étude de faisabilité ·
  Bilan · Comparatif) · Partager et agir (Apporteur · **Courrier** · Pré-dossier PC) · Le secteur
  (Étude de zone). Carte = icône + badge format (PDF/ZIP) + nom + description + « **Générer** ».
  (« Courrier » ajouté au catalogue : pont vers l'outil Courrier prérempli.)
- « **Générer** » agit sur la parcelle choisie ; Comparatif/Étude de zone ouvrent leur petite fenêtre de
  saisie supplémentaire **préremplie** ; Bilan/Étude de faisabilité ouvrent leur écran. Sans parcelle,
  « Générer » est désactivé (sauf Étude de faisabilité, qui compose son assiette dans l'écran).
- « **Mes documents** » en bas conservé, avec l'état « **À jour** » / « **Sources modifiées** » (badge
  existant).
- Petit reste cosmétique pré-existant : `ParcelleResolue` affiche « commune, commune » (l'adresse
  contient déjà la commune) et la surface « dessin » (1 625) plutôt que cadastre (1 567) — comportement
  d'origine, non introduit ici, laissé hors scope.

---

## Écran 5 — Copilote (`5-copilote.png`)

Fichier : `components/fiche/AskBar.tsx` (la barre « Copilote » de la fiche, ex-« Demander à l'IA »).

- Titre « **✦ Copilote** » en **mauve** (comme le bouton de la fiche). Une **phrase** dit sur quelle
  parcelle il répond : « Posez une question sur **BZ1065**. Je réponds avec les chiffres de la fiche,
  rien d'autre. » (référence courte = section + numéro, dérivée de l'IDU).
- Champ **multiligne** (`textarea`, Entrée envoie / Maj+Entrée saute une ligne) ; plus d'exemple coupé.
- « **Par exemple** » + exemples **courts** sur deux rangées, **un clic les envoie** (Combien je peux
  construire ? · Des ventes récentes à côté ? · C'est raccordé à l'assainissement ? · Quel risque
  d'inondation ? · Qui est le propriétaire ? · Que veut dire « zone Uh » ?) — tous sur des sujets que
  `/ask` sait traiter.

---

## Note d'exécution

Une tentative de parallélisation de l'écran 2 par un **fork** a dérapé (le fork, héritant du contexte,
s'est mis sur la fiche = l'écran 1, créant un conflit à deux écrivains sur `Fiche.tsx`). Le fork a été
**arrêté** ; ses éditions des tuiles (valeur-en-tête + source) étaient dans une région DISJOINTE des
miennes, correctes et conformes à la maquette — **conservées**. L'écran 2 a ensuite été fait en propre,
avec itération visuelle. Leçon : ne pas déléguer un écran à un **fork** (qui se prend pour moi) ; un
agent frais, scope explicite, serait plus sûr.

---

# RETOURS-18 — corrections de recette (même branche, pas de merge)

Trois maquettes de plus : `2b-filtres-reel.png`, `4b-documents.png`, `6-projet.png`. **Une capture après
par point** dans `captures/retours-18/`. Hook VERT (tsc 0, vitest, build, secrets, pytest unit 3193).

## Accueil et en-tête
1. **Accueil** (`LeftPanel.tsx`, `index.css`) — entrée **Radar retirée** (5 entrées), espaces réajustés,
   panneau `overflow-hidden` (plus de défilement). *(01-accueil-sans-radar)*
2. **« + Projet »** (`index.css`) — survol **vert opaque + encre sombre** comme « + CRM » : `.act-mint`
   (source plus tardive) masquait le fond `.hover-fill:hover` → forcé, et l'encre passe en `--ink`
   (plus de texte blanc). *(02-projet-hover-vert)*
3. **3D** (`MapView.tsx`, vérif) — **aucun saut de zoom ni de centre** à l'activation, sur **les DEUX**
   options du menu (« Relief seul » ET « Relief + bâtiments ») : mesuré live (zoom/centre identiques
   avant/après, seul le `pitch` s'incline). Déjà porté par RETOURS-17, vérifié sur les deux boutons. *(03-3d-sans-saut)*
4. **Cloche** (`Header.tsx`) — la cloche CLIENT ne montre QUE la **liste blanche** de kinds
   (`parcelle_suivie`, `radar`, `bascule`, `bodacc`, `match`, `nouveaute`) ; le compteur « non lues »
   suit la même liste. **Types retirés** (exploitation/admin, défense de profondeur au front) : tout
   kind hors liste — ex. `systeme`, `run`/calcul de nuit, `agent`/`batch`, `registre`, cohérence,
   déploiement, jobs de nuit, incidents, résumé matin, selftest, vigie/silence. *(04-cloche-client)*
5. **Outils sous l'en-tête** (`Rail.tsx`, `App.tsx`) — le panneau Outils a QUITTÉ le rail (il
   élargissait la colonne et poussait le logo + la recherche) : extrait en `OutilsPanel`, monté dans
   `<main>` SOUS l'en-tête. Logo et recherche NE BOUGENT PLUS (mesuré : `left` identique). *(05-outils-sous-entete)*
6. **Avatar** (`Header.tsx`) — ouvrir le compte **ferme une fiche commune** ouverte
   (`setContexteCommune(null)` à l'ouverture du menu). *(06-avatar-ferme-fiche-commune)*
7. **Alignements** (`Header.tsx`) — barre de recherche MOINS HAUTE (`h-10`→`h-9`) : logo, recherche,
   « Fiche commune », Signaler, cloche, avatar sur la même ligne de base. *(07-entete-alignee)*

## Fiche commune (`ContextePanel.tsx`)
8. **Ouvre EN HAUT** (bandeau visible), jamais sur « Identité » : le `scrollIntoView` ne s'applique
   QU'aux toggles **utilisateur** (nouveau `userActed()` dans le contexte d'accordéon), pas à
   l'ouverture par défaut (`claimDefault`, asynchrone). *(08-09-fiche-commune-haut)*
9. **Bandeau** — les deux lignes de résumé de l'en-tête (« CINOR — … » et « N ha · N parcelles »)
   RETIRÉES (doublon du bandeau 9 chiffres). *(08-09-fiche-commune-haut)*
10. **Menu des communes** (`Header.tsx`) — survol **vert** (`.hover-fill`). *(10-menu-commune-hover-vert)*

## Fiche parcelle
11. **Cartes** (`index.css`, `Fiche.tsx`) — au survol, **texte sombre sur vert, jamais blanc** (la
    règle de survol vise TOUS les descendants `*`, plus seulement `.t-val`) ; « N m max » à **12,5 px**
    comme les autres valeurs (une valeur ReactNode sautait le wrapper `.t-val` et héritait du 16 px). *(11-carte-hover-sombre)*
12. **Copilote fiche** (`AskBar.tsx`) — phrase « Posez une question sur… » RETIRÉE, espacements
    resserrés. *(12-copilote-fiche-resserre)*
13. **Analyse** (`Fiche.tsx`, `useApp.ts`) — se **referme au clic ailleurs** (hors carte et hors bouton ;
    nouveau `masquerVerdict`) ; le bouton « Analyse LABUSE » la **rouvre**. *(13-analyse-rouvre)*
14. **« Le projet »** (`formes.tsx`, `Fiche.tsx`) selon 6-projet.png — les quatre portes (Étude de
    faisabilité · Densifier l'existant · Calculette foncière · Assemblage) en **UNE colonne, toutes
    vert-contour** (`OutilsSection colonne`), au-dessus de « Étudier quand même ». *(14-le-projet)*

## Copilote (page) — `CopiloteView.tsx`, `ConversationsSidebar.tsx`, `index.css`
15. « C » retiré ; titre **« Sur quoi on travaille ? » seul** ; sous-titre, « Conservées 30 jours… »,
    « Entrée pour envoyer… » et le **trait gris** au-dessus de la zone d'écriture RETIRÉS (zone
    remontée). *(15-16-copilote-page)*
16. **Focus** (`index.css`, global) — plus de double contour sur les CHAMPS : `outline:none !important`
    au focus de `input/textarea/select/[contenteditable]` ; seul le contour de la DA (mauve ici) marque
    le champ. Appliqué à TOUTE l'app. *(15-16-copilote-page)*

## CRM — `DeplacerMenu.tsx`, `Kanban.tsx`
17. **« Déplacer »** = **menu de la DA** (déclencheur + volet `.floating`, lignes survol vert), plus le
    `<select>` natif ; **flèche (chevron) avec sa marge** (`ml-1`). Test `Kanban.test.tsx` mis à jour. *(17-18-crm-deplacer-note)*
18. **« Note »** présent sur **toutes les cartes**, quelle que soit la colonne (« Note » si remplie,
    « + Note » sinon ; avant : seulement quand vide). *(17-18-crm-deplacer-note)*

## Documents — `DocumentsView.tsx`, `catalogue.ts`
19. Selon 4b : **ancien flux rétabli** (clic sur la carte → la fenêtre demande l'adresse) ; barre de
    parcelle en haut, phrase d'intro et encart « Chaque document est lu… » RETIRÉS ; cartes alignées
    (icône + flèche, titre 1 ligne, description **exactement 2 lignes** `line-clamp-2`), **toute la
    carte cliquable** (survol bordure verte), plus de « Générer » ni de badge « PDF ». *(19-documents-4b)*
20. **Comparatif** — marge normale (`mt-3`) entre le dernier champ et le bouton. *(20-comparatif-marge)*

## Filtres — `FiltreLabuse.tsx` (selon 2b-filtres-reel.png)
21. **Quatre accordéons numérotés** (Communes · Le terrain · Affiner la recherche · Le propriétaire),
    **tous fermés à l'ouverture, UN SEUL ouvert à la fois** (état `openCat` partagé), tête = résumé du
    choix (« Toutes » / « — »). **UNE seule façon d'être sélectionné** partout (`LigneChoix` : vert
    opaque + texte sombre + coche à DROITE ; au repos texte clair, sans bordure, sans coche ; survol
    `bg-mint/15`) — plus aucun chip, case ni encoche. **Sous-accordéons avec le compte** : zonage
    (U · urbain / N · naturel / A · agricole / AU · à urbaniser → sous-zones), forme juridique, activité.
    « Toutes les communes » 1ʳᵉ ligne et défaut (+ « … N autres »). Titres sur une ligne.
    *(21-filtres-fermes, 21-filtres-communes, 21-filtres-terrain, 21-filtres-affiner, 21-filtres-proprietaire)*

**Note d'exécution** — le pt 21 (gros rewrite de `FiltreLabuse.tsx`) a été confié à un **agent frais**
(scope : ce seul fichier, sans navigateur) pendant que je faisais les pts 1-20 ; vérifié + capturé
ensuite dans l'app. (Leçon de l'écran 2 appliquée : agent frais, pas un fork.)

# RETOURS-19 — recette de Vic sur RETOURS-18 (même branche, pas de merge)

**15 points**, **une capture après par point** dans `captures/retours-19/`, et pour le **point 3 une
mesure** (tableau avant/après). Hook VERT (tsc 0, vitest **310**, build, secrets).

1. **Accueil centré** (`LeftPanel.tsx`) — titre + 5 cartes **centrés verticalement** sous Filtres
   (`justify-center`), cartes **64 px** (`.acc-entry`), plus de grand vide en bas. *(01-accueil-centre)*
2. **Notifications** (`Header.tsx`, `notifBell.test.tsx`) — le compteur compte les **non vues**
   (`vuMax` persisté en `localStorage`, `e.id > vuMax`) ; **ouvrir la cloche le remet à 0**
   (`marquerVues`) ; chaque notif garde **son point jusqu'au clic** (`lu` + `readOne` par ligne).
   Test : badge « 3 non vues » → clic cloche → « Notifications » + `vuMax=12` ; clic ligne → POST /read.
   *(02-notifications)*
3. **3D — le zoom ne saute plus** (`MapView.tsx`) — cause : `setTerrain` (exagération DEM) **recadre**
   pour garder un centre élevé en vue (asynchrone, au chargement du DEM). Fix : on **mémorise** zoom+centre
   avant, on **restaure** par `setZoom`/`setCenter` (qui **préservent le pitch**, contrairement à `jumpTo`)
   sur `idle` **et** à 900/1300/1800 ms, APRÈS le basculement du pitch (`easeTo pitch:55`). Mesuré dans
   Playwright depuis une parcelle sélectionnée (haute altitude), les 3 boutons :

   | Bouton               | avant (RETOURS-18)        | après (RETOURS-19)              |
   |----------------------|---------------------------|---------------------------------|
   | 3D                   | z 17 → 17 (pitch 0→55)    | z 17 → 17, pitch 0→55           |
   | Relief               | z 17 → **15,81** (saut)   | z 17 → **17**, pitch 0→55       |
   | Bâtiments + relief   | z 17 → **15,81** (saut)   | z 17 → **17**, pitch 0→55       |

   Seule l'inclinaison change, zoom+centre identiques. *(03-3d-zoom-stable)*
4. **Fiche commune — toutes sections fermées à l'ouverture** (`ContextePanel.tsx`) — plus aucun tiroir ne
   revendique l'ouverture par défaut (`openId` reste `null`), **Identité comprise**. Vérifié : 0/9 ouvert.
   *(04-fiche-commune-fermee)*
5. **Bouton « Fiche commune »** (`Header.tsx`) — **style secondaire** identique à « Signaler » (liseré
   neutre au repos, aplat vert plein + encre sombre à l'ouverture), **plus d'ambre**. *(05-bouton-fiche-commune)*
6. **Contours de focus** (`index.css`, `@layer base`) — `*:focus:not(:focus-visible){outline:none
   !important}` (aucun contour bleu navigateur, à la souris) + `*:focus-visible{outline:2px solid
   var(--mint)!important}` (clavier seul = **contour vert DA**). Mesuré : Tab → `rgb(74,222,128)` 2 px.
   *(06-focus-vert)*
7. **Filtres — aucun texte coupé** (`FiltreLabuse.tsx`) — libellés longs **à la ligne**
   (`break-words leading-snug`, `items-start`) au `Group` et à `LigneChoix`, **comptes visibles à droite**
   (`shrink-0`). Mesuré : 0 label clippé dans le panneau (342 px). *(07-filtres-texte)*
8. **Pied des filtres** (`FiltreLabuse.tsx`) — ordre **« Voir la liste brute » → « Analyser avec LABUSE »
   → « Réinitialiser »** (mesuré : tops 469 < 509 < …). *(08-pied-filtres)*
9. **Liste brute — bouton « Trier par surface »** (`ResultsSection.tsx`) — l'unique tri factuel porte ce
   libellé explicite (↓/↑ inversible) ; préfixe « Trier » + info « deux lunettes » (sans objet en factuel)
   retirés. *(09-liste-brute-tri)*
10. **Fiche parcelle — six tuiles séparées** (`index.css` `.fiche-v6 .stats`/`.stat`) — coins arrondis
    (6 px), espacement (gap 6 px), fond relevé + liseré par tuile, **marges haut/bas égales** (12/14) —
    comme le bandeau de la fiche commune ; fini la grille soudée. *(10-fiche-tuiles)*
11. **« Réseaux et desserte » sur une ligne** (`index.css` `.fiche-v6 .t-title`) — `white-space:nowrap`
    (+ ellipse de secours) ; vérifié sur **tous** les titres de section (dont « Risques et environnement »),
    0 clippé. *(11-titres-section)*
12. **Copilote — exemples rapprochés de la zone de texte** (`CopiloteView.tsx`) — l'accueil s'ancre
    `justify-end` : les suggestions se posent **juste au-dessus du champ** (écart 46 px, l'espace libre
    remonte au-dessus du titre), plus de grand vide. *(12-copilote)*
13. **« + Projet » — survol vert opaque + texte sombre** (déjà câblé RETOURS-18, re-vérifié) — fond
    dégradé `--fill-mint` (opaque) + encre `--ink`, **comme « + CRM »**. Capture **pendant le survol**.
    *(13-projet-hover)*
14. **CRM** (`Kanban.tsx`) — note **plus coupée en haut** (plafond de hauteur + défilement interne
    retirés, elle s'enroule en entier) ; **IDU déjà cliquable → fiche parcelle** (`focusParcelle(fiche:true)`,
    conservé) ; phrase « Contact saisi manuellement — … aucune donnée propriétaire automatiquement »
    **retirée**. *(14-crm)*
15. **Documents — « Étude de zone » même taille** (`DocumentsView.tsx`) — `h-full` retiré de `DocCard` :
    une carte **seule** dans sa colonne ne s'étire plus à toute la hauteur (les colonnes sont étirées par
    la grille). Mesuré : 140 px comme les autres (au lieu d'une tuile géante). *(15-documents)*

**Pièges rencontrés** — (1) un `{/* … */}` **premier enfant après `return (`** = deux nœuds racine →
`PARSE_ERROR` (encore, dans `DocumentsView.tsx`) ; corrigé en `//` au-dessus du `return`. (2) `--fill-mint`
est un **dégradé** (`linear-gradient`) : `getComputedStyle(...).backgroundColor` lit transparent alors que
le fond est bien un vert opaque (c'est `backgroundImage`) — vérifier le bon ⚡ pour ne pas croire à une
régression. (3) les outils Playwright `click`/`hover` attendent le paramètre **`target`** (pas `element`/`ref`).

# RETOURS-20 — recette de Vic sur RETOURS-19 (même branche, pas de merge)

**10 points**, **une capture après par point** dans `captures/retours-20/` ; pour les survols, capture
**pendant le survol**. Hook VERT (tsc 0, vitest **310**, build, secrets). Le bloc Score/Signal/Classer par
n'est **pas** retouché (remplacé par un autre mandat).

1. **Bouton « Fiche commune » sans chevron** (`Header.tsx`) — le `<svg>` chevron est retiré ; ne reste que
   le libellé. *(01-bouton-sans-chevron)*
2. **Accueil — espace trait↔titre réduit** (`LeftPanel.tsx`) — le trait sous « Filtres » resserré
   (`my-3` → `mt-3 mb-1`) et l'accueil `py-4` → `py-2` ; le bloc **reste centré** (`justify-center`). Mesuré :
   trait→titre **54 → 50 px**, désormais équilibré avec le bas (50/46). *(02-accueil-espace)*
3. **Ligne sélectionnée — fond vert seul** (`FiltreLabuse.tsx` `LigneChoix`) — aucune bordure, aucun
   contour, aucune ombre : seulement le fond vert, le texte sombre et la coche. Mesuré sur « Saint-Denis »
   sélectionnée : **border-width `0px` (4 côtés)**, **outline-style `none`**, **box-shadow `none`**,
   background `rgb(74,222,128)`, color `rgb(6,48,26)`, coche présente. (Déjà conforme — vérifié, pas de
   changement de code.) *(03-ligne-selectionnee)*
4. **Chargement de l'analyse** (`strings.ts`, `FiltreLabuse.tsx`) — « LABUSE croise ses 99 sources (PLU,
   risques, cadastre, bâti, ventes) pour classer les N parcelles de [commune]… », avec **N et la commune
   réels** (périmètre du run). Vérifié : « …les **38 217** parcelles de **Saint-Denis**… ». *(04-chargement)*
5. **L'étape de résumé supprimée** (`FiltreLabuse.tsx`) — fin du décompte → on arrive **directement** sur
   les résultats (plus de « LABUSE a analysé… Voir les parcelles »). Le `setTimeout` appelle `voirParcelles()`
   au lieu de passer en phase `'revealed'`. Vérifié : après le décompte, `data-voir-parcelles`/`data-phrase`
   absents, résultats affichés. *(05-resultats-directs)*
6. **Phrase retirée** (`ResultsSection.tsx`) — « Classées selon vos critères et l'analyse LABUSE (potentiel
   à bâtir, risques, accès, terrain) » supprimée. Vérifié absente du DOM. *(06-sans-phrase-classees)*
7. **Rectangle gris retiré** (`LeftPanel.tsx` `VerdictHero`) — plus de fond ni d'ombre derrière « Comprendre
   l'analyse » / « Retour » (fond + `shadow-elev-1` retirés). Mesuré : background transparent, box-shadow
   `none`. *(07-sans-rectangle-gris)*
8. **« ← Changer les filtres » → « ← Retour »** (`strings.ts` `changerFiltres`, `LeftPanel.tsx`) — partout
   où il apparaît. Vérifié : bouton `data-verdict-off` = « ← Retour ». *(08-retour)*
9. **Menu « Ajouter cette parcelle à… »** (`Fiche.tsx` `ProjetButton`) — dernière ligne **« Nouveau projet »**
   (sans « avec cette parcelle ») ; **aucun libellé coupé** (`break-words` au lieu de `truncate`, **et menu
   ancré `right-0`** pour ne plus déborder hors écran — « + Projet » est à droite du pied) ; **survol de
   chaque projet = fond vert opaque + texte sombre** (`.hover-fill`) ; **« + Projet » ouvert sans double
   contour** (outline `none`, box-shadow `none`, un seul liseré `act-cmp`). *(09-menu-projet)*
10. **Copilote — un seul bloc centré** (`CopiloteView.tsx`) — titre + exemples + zone de texte forment un
    bloc **centré verticalement** (`justify-center`, le champ vit DANS le bloc, plus pinné en bas qu'en
    conversation), **écart normal** exemples↔champ (24 px), plus de grand vide noir en haut. Vérifié à
    **deux hauteurs** : 900 px (void 238/238) et 620 px (void 98/98) — toujours centré, champ visible.
    *(10-copilote-900, 10-copilote-620)*

**Pièges** — (1) encore un `{/* … */}` **premier enfant après `{open && (`** → `PARSE_ERROR` 500 sur
`Fiche.tsx` ; corrigé en déplaçant le commentaire DANS le `<div>`. (2) le décompte dure 3 s < aller-retour
d'une capture → extension temporaire de `RITUEL_MS` (20 s) pour capturer l'écran de chargement, puis
revert. (3) un `live` pas encore chargé fait retomber le N du décompte sur le total de l'île (433 229) ;
en usage réel le compteur « N parcelles correspondent » est déjà chargé avant « Analyser » → N commune juste.

# RETOURS-21 — WebKit/Safari, focus & sélection uniques, carte & compteur (même branche, pas de merge)

**10 points.** Tout vérifié **dans WebKit** (moteur de Safari, `playwright webkit`) **après un clic souris**,
pas seulement dans Chrome. Captures Safari dans `captures/retours-21/`. Hook VERT (tsc 0, vitest **310**,
build, secrets).

> Environnement : Playwright 1.62 veut `webkit-2336` (non supporté sur ce macOS mac13-arm64). On a donc
> installé `playwright@1.49.1` (hors dépôt, `/tmp/pw-wk`) qui pilote le `webkit-2104` déjà en cache — moteur
> Safari fonctionnel. Harnais `/tmp/retours21_webkit_focus.cjs`.

## 1. Règle de focus UNIQUE (globale)
`src/lib/focusModality.ts` (nouveau) pose `html[data-input="mouse"|"key"]` : `mouse` dès un `pointerdown`,
`key` seulement sur une touche qui DÉPLACE le focus (Tab/flèches/Home/Fin/PagePrec-Suiv/Échap). `index.css`
(`@layer base`) : `*:focus-visible { outline:2px vert }` au clavier, et `html[data-input="mouse"] *:focus,
*:focus-visible { outline:none }` au clic. **Pourquoi la modalité et pas `:focus-visible` seul** : en Safari
un champ texte matche `:focus-visible` même au CLIC → le drapeau souris est le seul moyen de l'éteindre.
Règles locales RETIRÉES : bordure menthe des champs (`focus:border-mint` ×34 → 0, balayage), anneaux
`focus-within:border/shadow` du composeur Copilote (×2) + `focus-visible:ring` (CopiloteEmbarque ×2), aplats
de focus `focus-visible:bg/text` de `Bouton` (snapshot `formes` mis à jour). **Mesures WebKit après clic :**

| Élément (clic souris) | outline | box-shadow | verdict |
|---|---|---|---|
| Copilote — zone de texte | `none 0px` | `none` | ✓ (bordure inchangée) |
| Signaler — zone de texte | `none 0px` | `none` | ✓ (bordure inchangée) |
| Signaler — chip « Bug » | `none 0px` | `none` | ✓ (vert = sélection, pas focus) |
| En-tête — bouton « Signaler » | `none 0px` | `none` | ✓ (vert = état ouvert, pas focus) |
| Filtre — ligne commune | `none 0px` | `none` | ✓ |
| Filtre — « Procédure collective » | `none 0px` | `none` | ✓ |
| + Projet (fiche) | `none 0px` | `none` | ✓ (bordure menthe = design au repos) |
| **CLAVIER (Tab)** | **`solid 2px rgb(74,222,128)`** | — | ✓ **contour vert** |

*(01-copilote-champ-clic, 02-signaler-chip-et-champ)*

## 2. Règle de sélection UNIQUE
Tout élément choisi = **fond vert opaque + texte sombre**, jamais un simple contour. Les chips Bug/Idée/
Question de « Signaler » passaient `border-mint bg-mint/10 text-mint` (contour + teinte) → **`bg-mint
text-mint-on`** (`Header.tsx`). Les lignes de filtre (`LigneChoix`) et les puces de tri (`Tri`) étaient déjà
en aplat vert + encre sombre. *(02, 04)*

## 3. Survol des cartes Documents
`DocumentsView.DocCard` : `hover:border-mint` (simple contour) → **`.hover-fill`** = fond vert opaque + texte
et icônes sombres, comme les autres survols. Mesuré WebKit : fond `linear-gradient(#52E68C→#2FBE66)`, titre/
flèche/trait SVG `rgb(7,16,9)`. *(03-documents-survol)*

## 4. Le « i » d'une ligne sélectionnée
Le cercle du « i » des signaux restait **gris clair** (`border-current/40` **n'est pas une classe Tailwind
valide** → repli `gray-200`). `border-current` : le cercle (et le texte) prennent la couleur de la ligne →
**encre sombre sur le vert**. Mesuré : `color` et `border-color` du « i » = `rgb(6,48,26)`. *(04)*

## 5. Fiche parcelle — cadre gris derrière les six tuiles retiré
`.fiche-v6 .head` (le conteneur des tuiles) : fond + bordure retirés (`background:transparent; border:0`) et
le filet `.stats border-top` supprimé → **seules les six tuiles** (chacune son liseré) restent. *(05-fiche-tuiles-sans-cadre)*

## 6. Analyse — fin trait blanc sous « Filtres » retiré
`LeftPanel` : le séparateur `border-t border-line` sous la section « Filtres » ne s'affiche plus **en analyse**
(`!verdict`) ; conservé hors analyse (accueil). Vérifié : séparateur absent, l'en-tête « ✓ Analyse LABUSE »
suit directement.

## 7. « Fiche commune » = hauteur de la barre de recherche
Bouton passé à **`h-9`** (comme la recherche). Mesuré : recherche 36 px / Fiche commune 36 px, **haut 10/10,
bas 46/46** (alignés).

## 8. Compteur « N parcelles correspondent » < 300 ms
Cause : débounce **400 ms** + comptage serveur `/filtre?limit=0` (`COUNT(*)` filtré) **~1 s à froid**, ~5 ms
chaud (mémoïsé 30 s). AVANT ≈ 405 ms (chaud) / ~1,4 s (froid). Fix (`FiltreLabuse`) : débounce **400 → 120 ms**
+ passage à **react-query** (clé = filtres débouncés, `staleTime 30 s`) → une combinaison DÉJÀ VUE s'affiche
du cache **sans réseau** ; `placeholderData` = valeur précédente → pour une combinaison neuve, l'ancien nombre
reste affiché tout de suite (flottant) puis se CORRIGE. **Mesuré APRÈS : bascule d'un filtre en cache =
140 ms** (38 217 → 44 793), < 300 ms.

## 9. Carte — « Résultat trop large pour peindre » (~110 000 parcelles)
**Cause** : en analyse avec un critère HORS-TUILES (signaux, état du sol, propriétaire… que la tuile vectorielle
ne sait pas exprimer), la carte demande au serveur la LISTE EXACTE des IDU à peindre. **Limite** : le serveur
plafonne cette liste à **20 000** (`_FILTRE_IDUS_CAP`, `app.py`) ; au-delà il renvoie `idus_tronque` et l'ancien
code affichait « trop large pour peindre » (aveu d'impuissance) en peignant au mieux le sur-ensemble des tuiles.
**Fix** (`MapView` + `api.getFiltreIdus(f, bande)`) : au-delà du plafond, on ne renonce pas — on demande
SEULEMENT les IDU des **meilleures bandes (Excellente=A + Bonne=B)**, bien moins nombreuses (l'endpoint
`/filtre?idus=1&bande=A|B` existe déjà), et on les peint EXACTEMENT. Message réécrit : « La carte peint les
meilleures bandes (Excellente + Bonne) parcelle à parcelle ; … reste dans la liste. » (repli approximation si
même A+B dépasse le plafond — rare). Jamais un message d'impuissance.

## 10. Hook + captures Safari
tsc 0, vitest 310, build, secrets ; cinq captures WebKit (Safari) après clic/survol dans `captures/retours-21/`.

**Pièges** — (1) `webkit-2336` non supporté sur ce macOS → `playwright@1.49.1` + `webkit-2104` en cache.
(2) `border-current/40` n'est PAS une classe Tailwind (pas de variante d'opacité sur `current`) → repli gris
silencieux. (3) le compteur `[data-compteur-vivant]` n'est rendu QUE section « Filtres » dépliée (`data-filtres-
toggle` aria-expanded=true) — une mesure panneau replié le croit absent.

# RETOURS-22 — trait Filtres, cadre tuiles, défilement des sections (même branche, pas de merge)

**3 points**, une capture par point dans `captures/retours-22/`. Hook VERT (tsc 0, vitest 310, build, secrets).
Le bloc Score/Signal/Classer par n'est PAS touché.

1. **Fin trait sous « Filtres » retiré dans TOUS les états** (fermé, ouvert, analyse) — `LeftPanel` : le
   séparateur `border-t border-line` (les deux occurrences desktop+mobile) est SUPPRIMÉ (R-21 ne le retirait
   qu'en analyse). Vérifié : absent fermé ET ouvert. *(01-sans-trait-filtres)*
2. **Fiche parcelle — cadre des six tuiles retiré, tuiles égales, libellés sur une ligne** (`index.css`) :
   - `.fiche-v6 .stats` → **`border:0`** (et non `border-top:0` : la bordure GLOBALE `.stats`
     (`border:0.5px --line-2`) subsistait en bas et sur les côtés = le cadre encore visible). Mesuré :
     border `0px` sur les 4 côtés.
   - **Même hauteur ajustée au contenu, sans vide en bas** : `grid-auto-rows:1fr` (six tuiles égales) +
     `min-height` RETIRÉ (hauteur = contenu le plus riche, plus de plancher 62 px) + `.stat` en flex colonne
     `justify-content:center` (contenu centré → pas de vide en bas). Mesuré : les 6 tuiles à **88 px** (avant
     94 px, gonflées par un libellé sur 2 lignes).
   - **Chaque libellé sur une ligne** : `.stat-l` `white-space:nowrap` + interlettrage `.06em→.04em`.
     « SDP RESTANTE » + son « i » tiennent sur une ligne (mesuré : 14 px, non tronqué). *(02-fiche-tuiles)*
3. **Filtres — ouverture d'une section défile jusqu'à son DÉBUT** (`FiltreLabuse.AccordionCat`) : au passage
   fermé→ouvert (clic utilisateur), on aligne le haut de la carte (`.gcard`) sur le haut du conteneur défilant
   (`[data-filtres-drawer]`, trouvé par remontée du 1er ancêtre défilant), `scrollTo({top, smooth})`. La
   hauteur dépliée n'importe pas (on vise le début, jamais la fin). Mesuré : panneau défilé en bas (593) →
   ouverture de « Le terrain » → en-tête à **4 px du haut** du conteneur. *(03-section-ouverte-debut)*
