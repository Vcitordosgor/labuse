# M13 — LOT C · Scroll horizontal global (QA-46)

**Défaut (Vic)** : barres de scroll horizontales dans le panneau Couches, la liste de résultats,
la barre de tri, la fiche parcelle et le CRM. **Diagnostic** : un seul défaut de mise en page,
répété — le contenu débordait latéralement au lieu de s'adapter (retour à la ligne / empilement /
partage de largeur / pagination).

Branche : `fix/m13-c-scroll` (worktree isolé, **non mergée**). Base : `4003a5c` [M13-A].

## Cause racine commune

Deux mécanismes distincts, tous deux corrigés :

1. **Tooltip fantôme (Tip)** — le composant partagé `components/Tip.tsx` montait TOUJOURS son
   tooltip (`position:absolute w-max max-w-[260px]`, masqué par `opacity-0`). Dans un conteneur
   défilant étroit (`overflow-y-auto` calcule `overflow-x=auto`), ce tooltip gonflait le
   `scrollWidth` → **barre horizontale fantôme**, sans qu'aucun contenu visible ne déborde.
   → **Fix racine** : le tooltip n'est plus **monté que lorsqu'il est demandé** (survol / focus /
   tap). Au repos il n'élargit plus rien. Comportement d'affichage identique. C'est ce fix qui
   nettoie Couches, la liste de résultats, la fiche et les cartes CRM d'un coup.

2. **Contenu réellement trop large** — quelques zones avaient un contenu qui ne tenait pas
   (onglets de fiche, pilule de tri, colonnes CRM). Corrigé au cas par cas par empilement /
   flex-wrap / pagination (jamais par une barre horizontale).

`overflow-x-clip` a aussi été ajouté aux conteneurs défilants (ceinture + bretelles) : supprime
toute barre horizontale résiduelle sans créer de conteneur de défilement.

## Preuve par zone

App buildée + servie sur `http://127.0.0.1:8032/socle/`, viewport 1440×900, Playwright headless.
Pour chaque zone : mesure `scrollWidth <= clientWidth` (attendu **true**) sur le conteneur, +
capture PNG. Script : `qa/m13/C/shoot.mjs`.

| Zone | Fix appliqué | Fichier | Conteneur mesuré | scrollWidth / clientWidth | `sw<=cw` | Capture |
|------|--------------|---------|------------------|---------------------------|----------|---------|
| **Couches** | tooltip monté à la demande + `overflow-x-clip` | `panel/LeftPanel.tsx` | `[data-couches-drawer]` | 259 / 259 | **true** | `qa/m13/C/couches.png` |
| **Résultats** | tooltip à la demande + `overflow-x-clip` | `panel/ResultsSection.tsx` | `[data-results-scroll]` | 259 / 259 | **true** | `qa/m13/C/resultats.png` |
| **Barre de tri** | contrôle segmenté **flex-wrap** (s'empile) | `panel/ResultsSection.tsx` | `[data-tri-bar]` | 259 / 259 | **true** | `qa/m13/C/tri.png` |
| — panneau résultats entier | `overflow-x-clip` + tri corrigé | `panel/ResultsSection.tsx` | `[data-results-panel]` | 299 / 299 | **true** | `qa/m13/C/tri.png` |
| **Fiche** | onglets **flex-wrap** (retour à la ligne) + `overflow-x-clip` corps | `fiche/Fiche.tsx` | `[data-fiche-tabs]` | 399 / 399 | **true** | `qa/m13/C/fiche.png` |
| **CRM** | **pagination par flèches** (plus de scroll) + colonnes `flex-1` | `crm/Kanban.tsx` | `[data-crm-cols]` | 1376 / 1376 | **true** | `qa/m13/C/crm.png` |

Document (`documentElement`) : `scrollWidth = clientWidth = 1440` sur les 5 zones (DOC_OK=true).
Aucun conteneur avec `overflow-x: auto|scroll` en débordement (compte = 0) sur chaque zone.

## Choix CRM (consigné — mandat : « pas une barre horizontale »)

Le kanban a 8+ colonnes (`w-[230px]`) qui ne tiennent pas côte à côte. Solution retenue :
**pagination par fenêtre glissante + flèches**, PAS de barre horizontale.

- On affiche une **fenêtre de 5 colonnes** (`COLS_PAR_VUE = 5`) qui **remplissent la largeur**
  (`flex-1 basis-0 min-w-0`) — aucun débordement quel que soit le nombre de colonnes.
- Deux flèches **‹ ›** dans l'en-tête font glisser la fenêtre d'une colonne, avec un compteur
  `4–8 / 9`. Les flèches n'apparaissent que si toutes les colonnes ne tiennent pas.
- Le drag-drop reste possible vers toute colonne **visible** ; pour une colonne hors fenêtre on
  pagine d'abord (compromis assumé, meilleur qu'une barre de scroll pour l'ergonomie).
- Supprimés : l'ancien `overflow-x-auto`, la cale de fin, le fondu de bord droit et le hint
  « N étapes · défiler → » (remplacé par le compteur de pagination).
- Vérifié : la pagination glisse jusqu'au bout (`Colonnes suivantes` se désactive en fin), et le
  conteneur reste `scrollWidth == clientWidth` à **chaque** position de fenêtre.

## Note — chips d'en-tête (`Header.tsx`, `data-chips`)

Laissées en `overflow-x-auto` **à dessein** : c'est un strip de chips DANS la barre d'outils
supérieure (hauteur fixe), pas un des 5 volets signalés par Vic. Les faire wrapper pousserait la
hauteur du bandeau et casserait la mise en page de la toolbar ; un commentaire existant documente
que ce conteneur défilant est requis pour que le popover « + Filtre » ne soit pas rogné. Ce strip
ne produit aucune barre au niveau document (DOC_OK=true partout).

## Vérifications

- **TypeScript / build** : `cd frontend && npm run build` → **0 erreur TS**, build OK.
- **Golden** : `python qa/golden_check.py` → **116/116 PASS**, 0 FAIL, 0 incohérence base↔API.
- **Scoring** : aucune touche (fixes purement présentation front).

## Fichiers modifiés

- `frontend/src/components/Tip.tsx` — tooltip monté à la demande (fix racine).
- `frontend/src/components/panel/LeftPanel.tsx` — Couches : `overflow-x-clip` + `data-couches-drawer`.
- `frontend/src/components/panel/ResultsSection.tsx` — liste + barre de tri : `overflow-x-clip`,
  tri `flex-wrap`, attributs `data-results-panel` / `data-tri-bar`.
- `frontend/src/components/fiche/Fiche.tsx` — onglets `flex-wrap`, corps `overflow-x-clip`,
  `data-fiche-tabs`.
- `frontend/src/components/crm/Kanban.tsx` — pagination par flèches, colonnes `flex-1`,
  `data-crm-cols`.
- `qa/m13/C/shoot.mjs` — harnais de preuve. Captures : `qa/m13/C/*.png`.
