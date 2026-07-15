# FIX FINITIONS — points 8, 10, 12, 13, 25 du check

**Branche** : `feat/fix-finitions` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Front only. Zéro touche scoring/cascade/étage 0/run/données** (`git diff main...HEAD` = 3 composants
front + QA + captures). Commits séparés par point.

| # | Point | Type | Fait |
|---|-------|------|------|
| A | 12 — libellés zonage | fix | ✅ zones officielles vs par parcelle |
| B | 8 — chevauchement/scroll | fix | ✅ entonnoir en flux |
| C | 10 — vue mer sans effet | constat + fix | ✅ rendu (pas données) corrigé |
| D | 13 — symboles équipements | fix | ✅ pictogramme par type + légende |
| E | 25 — outil du bas | constat | ✅ identifié = « Sources » (fonctionne) |

## Lot 0 — Constat (lecture seule)
- **Point 10 (vue mer)** : **PAS une donnée vide, PAS cassé — un problème de RENDU.** Les données `vue_mer`
  sont présentes (geojson commune `vm.vue AS vue_mer` ET tuiles MVT île `tiles.py`). La couche ne dessinait
  un liseré cyan que sur les parcelles **promues** à vue mer (`PROMUES_FILTER`), fin (1,4 px) → quasi
  invisible (peu de promues à vue mer dans un cadre donné). Cause exacte = filtre trop restrictif + trait trop discret.
- **Point 25 (outil du bas)** : c'est le bouton **« Sources »** du rail (poussé tout en bas par `mt-auto`,
  icône « pile de disques »). Il ouvre la page **Sources = fraîcheur des données / registre des sources**
  (`openSources`). **Il fonctionne** (testé). Rien de cassé — juste visuellement détaché, d'où le doute.
- **Point 8 (chevauchement)** : reproduit. Le « pourquoi ? » (entonnoir) était un **popover flottant absolu**
  dans un conteneur `overflow-y-auto` → l'explication était **clippée** (« pas vue en entier ») et son
  **fond modal `fixed inset-0`** interceptait le scroll (« pas pu descendre voir les parcelles »). Conflit
  = popover absolu clippé + backdrop modal.

## FIX A — Libellés zonage (point 12)
`LeftPanel` : **« Zonage PLU (zones officielles) »** (polygones bruts du GPU) + **« Zonage PLU (par
parcelle) »** (zone rattachée `parcel_zone_plu`), hints qui explicitent la différence. Preuve :
`fin-A-zonage-labels.png`.

## FIX B — Entonnoir « pourquoi ? » (point 8)
Le popover flottant devient un **panneau EN FLUX** (`data-entonnoir-panel`) : l'explication + le détail par
motif s'affichent **entièrement**, poussent le contenu, et la section défile **naturellement** jusqu'aux
parcelles. **Plus de fond modal** qui bloquait le scroll. Preuve : `fin-B-entonnoir-inline.png` (explication
ouverte + chips de tier + liste accessibles en dessous).

## FIX C — Vue mer (point 10)
Rendu corrigé (les données étaient là) : la couche montre **TOUTES** les parcelles à vue dégagée (plus
seulement les promues), liseré cyan **épaissi (1,6→2,6 px selon le zoom) + halo**. Effet nettement visible
quand activée. Preuve : `fin-C-vuemer.png` (113 parcelles cyan sur le littoral). Zéro touche données.

## FIX D — Symboles équipements (point 13)
Un **pictogramme parlant par type** (pastille couleur + émoji) au lieu de pastilles indistinctes :
🏛️ Mairie · 🏫 École · 🏥 Santé · 🛒 Commerce · 🚌 Transport · 🚓 Police/gendarmerie · ⚽ Sport. Généré via
**canvas → `map.addImage`** (aucune lib ; repli robuste = la pastille colorée + la légende si l'OS n'a pas
la police émoji) ; couche `ov-equip` passée en `symbol`. **Commerce et transport (tcsp) réintégrés** (ils
étaient exclus). **Légende carte** listant chaque type. Preuve : `fin-D-equipements.png` (symboles + légende).

## FIX E — Outil du bas (point 25) — constat
= **« Sources »** (rail, tout en bas). Ouvre la page fraîcheur des données / registre des sources.
**Fonctionne.** Libellé déjà explicite (« Sources » + tooltip « Fraîcheur des données »). Pas de fix requis.

## Non-régression & garanties
- **Zéro touche scoring/données** : `git diff main...HEAD` = `LeftPanel.tsx`, `ResultsSection.tsx`,
  `MapView.tsx` (rendu carte) + QA + captures. Aucun fichier backend/scoring/données.
- Carte, fiches, outils, filtres : intacts (le rendu vue-mer/équipements est additif ; l'entonnoir garde
  sa donnée `/entonnoir`, seul son contenant change). `tsc --noEmit` vert, build Vite OK.

*Commits séparés sur `feat/fix-finitions`. Pas de merge.*
