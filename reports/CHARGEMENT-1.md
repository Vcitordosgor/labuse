# CHARGEMENT-1 — un seul indicateur de chargement + gate « ordinateur seulement »

Branche `fix/chargement-1` · ports 8850 (API) / 6050 (front) · DA existante · pas de merge.

## 1. Le composant unique

`frontend/src/components/Loading.tsx` → **`Chargement`** : trois petits points menthe
(`#4ADE80`, le vert de marque) qui défilent en boucle (vague d'échelle décalée de 160 ms,
keyframe `labuse-load`). Deux variantes et rien d'autre :

- `variant="inline"` — dans un bouton, une case, une ligne de texte.
- `variant="bloc"` — centré dans un panneau le temps que la donnée arrive.

Options : `label` (message court optionnel), `accent` (`mint` défaut — **points menthe partout, Outils
et Copilote compris** · `courant` = couleur du texte, pour rester visible DANS un bouton plein),
`delai` (défaut **300 ms**).

**Délai de 300 ms** (`useDelai`) : le composant est monté quand l'attente commence, démonté quand
elle finit. S'il disparaît avant 300 ms, **rien ne s'est affiché** → aucune action rapide ne clignote.

DA : plus de halo/lueur (règle DA), plus de spinner rotatif, plus de squelette gris.
`Loading` / `Skeleton` / `Squelette` sont conservés comme **adaptateurs de compatibilité** : ils
rendent désormais `Chargement` — les ~90 points d'appel existants basculent sans réécriture, un seul
langage visuel. Les styles `.sk` (squelette gris) sont **supprimés** de `styles/index.css`.

## 2. Carte — indicateur discret dans un coin

`components/map/MapView.tsx` : l'ancien bandeau central « Chargement des parcelles… » devient un petit
indicateur **en bas à gauche** (points menthe + libellé court : *Parcelles… / Couche… / Carte…*),
piloté par `geo.isFetching || tilesLoading || layersFetching` (dont les événements MapLibre
`dataloading`/`idle`). Le popup de survol (DOM impératif) reçoit aussi les trois points.

## 3. Gate « ordinateur seulement » (point 6)

Téléphone / tablette / iPad (même déguisé en Mac) / écran physique < 1024 px → **un écran unique**
(logo LABUSE, « LABUSE est disponible sur ordinateur. », « Ouvrez app.labuse.immo depuis votre
ordinateur. », lien Contact), DA de l'app. Aucune autre page accessible. Décidé **une fois au
chargement** : une fenêtre de bureau simplement rétrécie n'est pas bloquée si l'écran fait ≥ 1024 px.

- Détection partagée : `frontend/src/lib/appareil.ts` (`estAppareilMobile`) — UA mobile, iPad Mac+tactile,
  pointeur principal tactile, ou `screen.width < 1024`.
- SPA (app + **dashboard admin**) : `frontend/src/components/EcranOrdinateur.tsx`, branché en tête de
  `frontend/src/main.tsx` (avant App, admin, run-non-configuré).
- Page de connexion + tout le tunnel (2FA, légales, 404) : script same-origin **`/ordinateur.js`**
  (`src/labuse/api/onboarding.py`, CSP `script-src 'self'`), injecté par le gabarit partagé
  `src/labuse/api/coffre_ui.py`, route publique (`_PUBLIC` dans `src/labuse/api/auth.py`).

## 4. Endroits branchés (fichier · écran)

### Branchés explicitement sur `Chargement` (indicateurs ad hoc remplacés)
| Fichier | Écran | Remplacé |
|---|---|---|
| `components/map/MapView.tsx` | Carte | bandeau central + popup → coin discret (points) |
| `components/header/Header.tsx` | Recherche (omnibox) | pastille pulsante → points inline |
| `components/copilote/ui.tsx` | Copilote (TraitementEnCours) | 3 points pulse maison → `Chargement` (menthe) |
| `components/outils/moteurs.tsx` | Outil PLU (recalcul à blanc) | shimmer `animate-pulse` → bloc (menthe) |
| `components/outils/EtudeZone.tsx` | Outil Étude de zone | bouton « Calcul de la zone… » |
| `components/outils/ModulePanel.tsx` | Outils (pagination « voir plus ») | texte « Chargement… » |
| `components/outils/ProspectionSolaire.tsx` | Outil Prospection solaire | texte « Chargement… » |
| `components/outils/TaxeAmenagement.tsx` | Outil Taxe | « Chargement du contexte parcelle… » |
| `components/panel/ResultsSection.tsx` | Recherche / résultats (×4) | texte « Chargement… » |
| `components/panel/FiltreLabuse.tsx` | Filtres (compteur facette) | texte « Chargement… » |
| `components/fiche/Fiche.tsx` | Fiche parcelle (bouton Signaler) | « Envoi… » |
| `components/fiche/BilanEcran.tsx` | **Bilan** (calcul + génération) | « Chargement du bilan… » + bouton « Génération… » |
| `components/fiche/GabaritLine.tsx` | Fiche parcelle (gabarit) | « Calcul… » |
| `components/fiche/constructibilite.tsx` | Fiche parcelle (calculette ×2) | « recalcul… » `animate-pulse` |
| `components/fiche/SourceDrawer.tsx` | Fiche (tiroir sources) | texte « Chargement… » |
| `components/documents/DocumentsView.tsx` | **Docs** + génération PDF | « Génération… » / « Ouverture… » |
| `components/projets/ProjetsPanel.tsx` | Projets (fusion doublons) | « Fusion… » |
| `components/projets/ParcoursProjet.tsx` | Projets (création ×2) | « Création… » |
| `components/admin/*` (AdminView, Licences, Produit, Ia, Courrier, Destinations, Cron, Contacts) | **Dashboard admin** | `<div>Chargement…</div>` |
| `components/admin/circuit/{Journal,Detail}.tsx` | Admin · Circuit | `<div>Chargement…</div>` |

### Unifiés automatiquement via les adaptateurs (`Squelette`/`Skeleton` → `Chargement`)
Même langage visuel, sans réécriture, sur : **fiche parcelle** (`Fiche`, `AskBar`, `PourquoiPas`,
`constructibilite`), **fiche commune** (`contexte/ContextePanel`), **Comparer** (`compare/ComparePanel`),
**Projets** (`ParcoursTinder`, `ProjetKanban`, `ProjetsPanel`), **CRM** (`crm/Kanban`),
**Veille/Radar** (`radar/RadarHub`, `RadarEcran`, `RadarMarcheColonne`, `VeilleEcrans`),
**Recherche/résultats** (`panel/ResultsSection`), **Sources** (`sources/SourcesPage`),
**Carte** (`map/MapView`, `VefaDetail`), **shell** (`App.tsx` — carte & panneaux lazy), et les
**outils** (`Communes`, `Gabarit`, `Blocs`, `blocB`, `Successions`, `RadarMarche`, `ScoringV2`,
`MonSecteur`, `PluAnnuaire`, `HistoireFrise`, `ProcedureChangement`, `VeillePromoteurs`, `moteurs`,
`ModulePanel`, `ProspectionSolaire`, `EtudeZone`, `TaxeAmenagement`).

## 5. Tests & build

- `frontend/src/components/Loading.test.tsx` — gate 300 ms (rien avant, 3 points après), variantes,
  accents (mint/violet/courant).
- `frontend/src/lib/appareil.test.ts` — iPhone/iPad/petit écran bloqués ; bureau et écran ≥ 1024 px non.
- **`npx vitest run` : 247/247 verts (54 fichiers).** `tsc --noEmit` : 0 erreur. `npm run build` : OK.
- Backend : `pytest` auth / onboarding / parcours CSS / légal verts ; `/ordinateur.js` public + présent
  sur `login_page()` et tout le gabarit `coffre_ui` (vérifié). (Les tests DB-dépendants sont *skipped*
  faute de Postgres TCP ; l'unique échec `test_audit_secu` est une erreur de connexion pré-existante.)

## 6. Captures (`captures/chargement1/`)

`1_fiche_parcelle.png` · `2_fiche_commune.png` · `3_outil_communes.png` · `4_bilan.png`
(les 4 écrans EN chargement, indicateur unique visible) · `5_gate_telephone.png` · `6_gate_ipad.png`.
Rejouables : `frontend/qa/chargement1_cap.mjs` (API 8850 + front 6050).
