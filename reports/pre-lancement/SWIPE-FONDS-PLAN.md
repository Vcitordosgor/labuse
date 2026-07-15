# SWIPE FONDS DE PLAN — comparateur généralisé (point 24)

**Branche** : `feat/swipe-fonds-plan` (NON mergée — Vic valide + merge). **Date** : 2026-07-15.
**Front / carte uniquement. Zéro touche scoring/cascade/étage 0/run/données** (`git diff main...HEAD`
= 4 fichiers, tous sous `frontend/`).

Objectif : appliquer **le même geste de rideau que « 1950 »** aux **fonds de plan** — tirer un curseur
pour comparer deux fonds cartographiques, au lieu d'un simple toggle de couche.

| # | Commit | Étape |
|---|--------|-------|
| A | `map/basemaps.ts` | registre des fonds extrait de MapView → source de vérité partagée |
| B | moteur | comparateur généralisé à deux fonds quelconques (échange sur place) |
| C | UI | choix des deux fonds + sortie propre vers fond unique |

---

## Lot 0 — Constat & faisabilité (verdict : **(b) MEDIUM / refactor léger**)

**Comment « 1950 » fonctionne** (`components/outils/TimeMachine.tsx`) : **custom, aucune lib**. Deux
instances **MapLibre GL** superposées ; celle de droite est **rognée en CSS `clip-path: inset(0 0 0 X%)`**
selon la position de la poignée ; **caméras synchronisées** dans les deux sens (`move` → `jumpTo`, garde
anti-boucle) ; les parcelles promues sont dessinées des deux côtés. Le mécanisme (rideau + double carte +
synchro) est **générique** ; seuls **les deux fonds de tuiles ET les libellés** étaient **codés en dur**
(`ORTHOIMAGERY.…1950-1965` à gauche, `ORTHOIMAGERY.ORTHOPHOTOS` à droite, badges « 1950-1965 »/« aujourd'hui »).

**Les fonds disponibles** (`components/map/MapView.tsx`, `BASEMAP_SOURCES`) : **5** — Sombre (Carto),
Plan IGN, Ortho actuelle, Ortho 2000-2005, Ortho 1950-1965. Bascule aujourd'hui via `MapToolbar`
(« FOND DE PLAN » + « REMONTER LE TEMPS ») → store `useApp` (`basemap`/`orthoYear`) → visibilité de
couche dans MapView. **C'est le « filtre de vue carte » actuel.**

**Verdict** : **(b)** — le geste est déjà générique, il suffit de **paramétrer les deux sources + les
libellés** et de partager le registre des fonds. Pas de nouveau comparateur, pas de lib, pas de refonte.
→ construction (pas de STOP).

## FIX A — Registre des fonds partagé (`map/basemaps.ts`)
Le comparateur doit connaître **les mêmes fonds** que la carte. On extrait `WMTS` + `BASEMAP_SOURCES`
(les 5 fonds, **valeurs identiques**) de MapView vers un module partagé. MapView les **importe** désormais
(zéro changement de comportement). Ajout de `BASEMAP_CHOICES` (liste ordonnée + libellés courts) +
`basemapLabel()` pour l'UI du comparateur. **Source de vérité unique.**

## FIX B — Moteur généralisé (échange sur place)
`TimeMachine` prend deux fonds via état (`leftKey`/`rightKey`, **défaut `bm-ortho-1950` ↔ `bm-ortho-now`**).
- `mkMap()` crée une carte **nue** ; `applyBasemap(map, def)` **pose/échange le raster `bm` SUR PLACE**
  (même instance) → **caméra, synchro et surcouche parcelles préservées** ; réinséré **sous** la couche
  parcelles `'p'` (le contour reste au-dessus). Overzoom `maxzoom` conservé (1950 s'arrête ~z15).
- Libellés **dynamiques** (nom réel du fond) au lieu des badges figés.
- **Non-régression** : défauts = anciennes valeurs → ouvrir « 1950 » reste **1950 ↔ actuelle**.

## FIX C — UI : choix des deux fonds + sortie
Barre de contrôle **« COMPARER [gauche] ⇔ [droite] »** (deux sélecteurs listant les 5 fonds). Le fond
change **en direct**, le rideau et la caméra ne bougent pas. Bouton **« ✕ Quitter »** → `setModule(null)`
→ retour à la **carte à fond unique** (le `MapToolbar` existant, **intact**). Le geste reste **exactement**
celui de « 1950 » (même poignée `⇔`, même `clip-path`, même feel).

---

## Tests & preuves (`frontend/qa/swipe_fonds_plan.mjs`, live sur `:8010/socle/`, Saint-Paul)
- `swipe-1-defaut-1950.png` — **défaut 1950 ↔ actuelle** : le geste d'origine, inchangé (non-régression).
- `swipe-2-plan-vs-ortho.png` — **Plan IGN ↔ Ortho actuelle**, rideau à ~38 % (deux fonds quelconques).
- `swipe-3-ortho-vs-sombre.png` — **Ortho ↔ Fond sombre**, rideau à ~60 % (autre paire).
- **Synchro caméras** : bouger la gauche → la droite suit, **écarts lng/lat/zoom = 0** (log QA).
- `swipe-4-sortie-fond-unique.png` — **« Quitter »** → carte simple restaurée, **comparateur démonté**
  (`[data-cmp-left]` absent, `canvas` présent) → le **toggle de fond unique** est intact.

## Non-régression & garanties
- **Zéro touche scoring/données** : `git diff main...HEAD` = `basemaps.ts` (nouveau), `MapView.tsx`
  (import du registre), `TimeMachine.tsx` (comparateur), `qa/swipe_fonds_plan.mjs` (QA). Aucun fichier
  backend/scoring/cascade/étage 0/run.
- **« 1950 » intact** : c'est le défaut du comparateur ; l'entrée fiche « 1950 » ouvre 1950 ↔ actuelle.
- **Toggle de fond unique intact** : `MapToolbar`/`MapView` non modifiés côté comportement (registre
  déplacé à valeurs identiques) ; « Quitter » y revient.
- `tsc --noEmit` vert ; build Vite OK.

*3 commits (A–C) sur `feat/swipe-fonds-plan`. Pas de merge.*
