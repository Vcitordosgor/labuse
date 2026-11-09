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

**Partiel / non fait (écran 2)** — à arbitrer avec Vic :
- Le bloc « **Classer par** » de la maquette (potentiel à bâtir / chance de vente / surface) : l'écran
  garde son tri « USAGE » (Va se vendre / À construire) + la barre de tri existante. Rebrancher
  « Classer par » sur ces trois clés = changer les options de tri servies (`SortKey`) → plus large que
  le front, laissé en l'état.
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
