# IMPLANTATION-4 — L'Étude vit dans Docs, plus de doublon de logements ni de SDP

Branche `feat/implantation-4` depuis `main` (après merge d'IMPLANTATION-3). Worktree
`~/Desktop/labuse-implant4`, ports 8861 / 6061. **Aucun merge, aucun run de données, rien en prod.**
Trois lots, un commit par lot ; ce document + les captures en 4ᵉ commit.

## ÉTAPE 0 — garde

- `pwd` = `/Users/openclaw/Desktop/labuse-implant4`, branche `feat/implantation-4`, arbre propre.
- IMPLANTATION-3 présent dans `main` (`fe7a78a0` LOT A « document Étude », `d4466ddf` LOT B « Dossier
  sans doublon de capacité », merge `fa03c59e`). La branche part du HEAD de `main`.

## Le problème réglé

Avant IMPLANTATION-4, l'« Étude de faisabilité » existait **deux fois** : un **outil** (menu Outils,
`#m=programme`, moteur d'implantation M22) ET un **document** PDF (9ᵉ carte Docs). En parallèle, un
**ancien moteur** de faisabilité (fiche `getFaisabilite`, `/compare`, `/moteurs/assemblage`, repère
`faisabilite` du Bilan) imprimait un **nombre de logements** et une **SDP maximale** qui **doublonnaient
et contredisaient** l'Étude. IMPLANTATION-4 range tout :

1. **L'Étude quitte les Outils et vit dans Docs** (un seul composant, une seule API, aucun second calcul).
2. **Plus aucun nombre de logements de l'ancien moteur** : l'Étude est la seule source.
3. **Libellés de SDP** disjoints : ancien moteur = « SDP maximale réglementaire », Étude = « SDP du scénario ».

---

## LOT A — L'Étude quitte Outils, vit dans Docs

**L'entrée sort du menu Outils.** `registry.ts` : l'entrée `programme` passe en `hidden: true`. Le Rail
affiche `MODULES.filter((m) => !m.hidden).length` → **le compte de tuiles passe de 16 à 15** (verrou
dynamique, pas de constante en dur ; capture A1 : « 15 outils fonciers », pas de carte « Faisabilité »).
La clé reste au registre (valide pour `COMPONENTS`, la garde clic-carte de MapView et la rétro-compat
des liens).

**La 9ᵉ carte Docs ouvre l'écran d'étude complet**, sur le modèle du Bilan :
- Nouvel overlay `EtudeEcran.tsx` (patron `BilanEcran` : `fixed inset-0`, en-tête « ← Fermer », corps),
  monté au niveau `App` et piloté par le store (`etudeIdus` + `ouvrirEtude`/`fermerEtude`, rejoint
  `CLOSE_OVERLAYS` → toute navigation le ferme). Chargé à la demande (son chunk embarque maplibre).
- Il rend le **MÊME composant M22** en mode `embedded` : configuration (assiette 1–8 parcelles, type,
  objectif, programme, stationnement), scénarios A/B/C, **sections repliables**, **hypothèses**, puis
  **« Générer le PDF »** (le bouton PDF existant, qui lit la même réponse — aucun second calcul).
- **Carte intégrée** : nouveau composant `PlanMasseCarte.tsx`, instance MapLibre **autonome** (fond
  ortho via le proxy + calques `etude-*` copiés AU TRAIT de `MapView`), affichant le plan masse déjà
  servi (`actif.geojson` filtré par couche cochée). Elle ne touche JAMAIS la carte de fond (plus de
  `setModuleMap` en mode embedded). En embedded, M22 tient une **sélection locale** (il ne touche plus
  au `msel` global, partagé avec l'Assemblage). Captures C1 (config) / C2 (scénarios + plan masse).

**Fiche parcelle** : la tuile « Étude de faisabilité → » (`constructibilite.tsx` + les deux tuiles de
`Fiche.tsx`) appelle `ouvrirEtude([idu])` → ouvre cet écran dans Docs sur la parcelle (plus
`setModule('programme')`).

**Assemblage** : pont « **Étude de faisabilité de cet assemblage →** » (`moteurs.tsx` M16) →
`ouvrirEtude(msel)` avec les parcelles sélectionnées (capture F1).

**Anciens liens** : dans `App.tsx`, `#m=programme` **redirige** vers l'overlay (`ouvrirEtude`), avec la
parcelle si `#idu=…` est présent — plus de 404, plus d'ouverture du panneau d'outil retiré.

Tests : `EtudeDocs.test.tsx` (registre : `programme` hidden, 15 tuiles ; store : ouverture/fermeture +
fermeture à toute navigation ; rendu de l'overlay = écran d'étude complet, assiette amorcée, config).

---

## LOT B — Plus aucun nombre de logements de l'ancien moteur

Le nombre de logements ne vient plus **que** de l'Étude (dessiné, contrôlé, par scénario).

- **Comparatif** — écran (`ComparePanel.tsx`) ET PDF (`exports/blocs/comparatif.py`) : la ligne
  « Logements possibles » devient **« voir l'Étude de faisabilité »** — aucun chiffre, aucun tri, aucun
  badge. L'API `/compare` garde la donnée (désormais inutilisée). Captures E2 (écran).
- **Fiche · Constructibilité** (`constructibilite.tsx`) : plus de « N logts » en tête ; on affiche la
  **SDP maximale réglementaire** + un renvoi cliquable **« Nombre de logements et plan masse : voir
  l'Étude de faisabilité → »** (ouvre l'écran d'étude). `logMax` reste interne (couleur « rien à bâtir »),
  il n'imprime aucun nombre.
- **Assemblage** (`moteurs.tsx`) : la tuile « Logements » (fourchette cumulée de l'ancien moteur) est
  **retirée** ; le nombre de logements se lit via le pont vers l'Étude. Capture F1 (grille KPI =
  « Surface d'assiette · SDP estimée cumulée · vs meilleure seule », plus de tuile Logements).
- **Bilan** : le repère `faisabilite` (`bilan/reperes.py`) **ne renvoie plus `logements`** → l'ancien
  moteur ne pré-remplit plus aucun logement. Nouveau **pont « Bilan de ce scénario → »** dans l'écran
  d'étude : ouvre le Bilan pré-rempli avec le programme du scénario (logements par type → lots du 1ᵉʳ
  produit, SDP du scénario → SDP), **étiqueté « depuis l'Étude »**. Capture D1 (badge « depuis l'Étude ·
  scénario A », SDP 1 800, 28 lots).
- **Dossier (et Flash)** : déjà au renvoi « voir l'Étude de faisabilité » depuis IMPLANTATION-3 (banc
  `test_a05_1_capacite_pdf_fiche.py`) — inchangé.

Tests : `BilanDepuisEtude.test.tsx` (pré-remplissage à blanc par défaut vs « depuis l'Étude »).

---

## LOT C — Libellés de SDP

Les deux libellés ne se croisent **jamais** :

| Surface | Avant | Après |
|---|---|---|
| Comparatif (écran + PDF) | « SDP max estimée » | **« SDP maximale réglementaire »** |
| Fiche · Constructibilité (micro) | « SDP … m² » | **« SDP maximale réglementaire … m² »** |
| Dossier (`registre/donnees.py`) | « Surface de plancher créée (table rase) » | **« SDP maximale réglementaire (table rase) »** |
| Bilan — repère `faisabilite` | « Faisabilité … m² SDP (estimation) » | **« SDP maximale réglementaire … m² (estimation) »** |
| Écran Étude (M22) | « m² SDP » / « SDP … m² » | **« m² SDP du scénario »** / « SDP du scénario … » |
| Document Étude PDF (`etude_faisabilite.py`) | en-têtes « SDP » | **« SDP du scénario »** |

Capture E1 (Comparatif : « SDP MAXIMALE RÉGLEMENTAIRE · TERRAIN LIBÉRÉ ») et C2 (Étude : « 1 800 m²
SDP du scénario »).

---

## Preuves

### Tests
- **Front** : `tsc -b` → 0 erreur ; `vitest run` → **266 verts** (58 fichiers), dont 3 ajoutés :
  `EtudeDocs.test.tsx` (LOT A), `BilanDepuisEtude.test.tsx` (LOT B). Les tests pré-existants restent
  verts (`Etude.test.tsx` rend M22 hors embedded = comportement historique intact ; `overlays.test.ts`
  inchangé).
- **Back** : `py_compile` OK sur les 4 fichiers touchés (`comparatif.py`, `reperes.py`,
  `etude_faisabilite.py`, `donnees.py`). L'environnement Python du worktree n'est pas provisionné
  (sqlalchemy/PostGIS absents) et le mandat interdit tout run de données ; le banc Python (dont
  `test_a05_1_capacite_pdf_fiche.py`, marqué `reel`) s'exécute dans l'environnement provisionné.
  Aucune chaîne de libellé modifiée n'est assertée par un test existant (vérifié par grep).

### Captures (`captures/`, harnais Vite à fetch bouchonné — API et navigateur arrêtés, ports
6061/8861 LIBRES vérifiés par `lsof`)
| Fichier | Ce qu'il prouve |
|---|---|
| `A1-menu-outils-sans-faisabilite.png` | Menu Outils : **15 outils**, aucune carte « Faisabilité ». |
| `B1-docs-9e-carte-etude.png` | Grille Docs : 9ᵉ carte « Étude de faisabilité ». |
| `C1-ecran-etude-config.png` | Écran d'étude (overlay Docs) — état configuration. |
| `C2-ecran-etude-scenarios-planmasse.png` | Scénarios A/B/C, **carte intégrée** (plan masse), **« SDP du scénario »**, **« Bilan de ce scénario → »**, **« Générer le PDF »**. |
| `D1-bilan-depuis-etude.png` | Bilan pré-rempli **« depuis l'Étude · scénario A »** : SDP 1 800, 28 lots. |
| `E1-comparatif-voir-etude-sdp-max-regl.png` | Comparatif : **« SDP maximale réglementaire »**. |
| `E2-comparatif-logements-voir-etude.png` | Comparatif : ligne logements = **« voir l'Étude de faisabilité »** (aucun nombre). |
| `F1-assemblage-pont-etude-sans-tuile-logements.png` | Assemblage : **pont vers l'Étude**, grille KPI **sans tuile « Logements »**. |

> **Fiche → Docs** : la tuile « Étude de faisabilité → » de la fiche appelle le même `ouvrirEtude([idu])`
> que les autres portes → ouvre **exactement l'écran de C2**. Le câblage est couvert par les tests
> (`EtudeDocs.test.tsx` : `ouvrirEtude` ouvre l'overlay) ; une capture de fiche complète demande le
> backend réel (payload `/parcels` non bouchonnable de façon fidèle), hors du périmètre « aucun run ».

### Scoring
**Non touché** — aucun fichier de scoring (`score_labuse`, `signal`, cascade, bandes) modifié. Les
changements sont d'affichage (front), de libellés d'export (back) et de câblage d'overlay.

---

## Commits (pas de merge)

1. `feat(implantation-4): LOT A — l'Étude de faisabilité quitte les Outils et vit dans Docs`
2. `feat(implantation-4): LOT B — plus aucun nombre de logements de l'ancien moteur`
3. `feat(implantation-4): LOT C — libellés de SDP (ancien moteur vs Étude)`
4. `docs(implantation-4): RAPPORT + captures + hook QA ouvrirEtude`

## Gestes pour Vic

- **Merger** `feat/implantation-4` (pas de run nécessaire : changements d'affichage/libellés/câblage).
- Exécuter le banc Python dans l'environnement provisionné (notamment `test_a05_1_capacite_pdf_fiche.py`
  et un éventuel témoin de l'export Comparatif) pour confirmer les libellés PDF sur base réelle.
