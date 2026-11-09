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
