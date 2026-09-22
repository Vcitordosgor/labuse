# M-W micro — « la carte ne s'affiche plus après vite 8 »

## Verdict : la carte N'EST PAS cassée par vite 8. Deux vraies causes de confusion, corrigées.

Reproduction Playwright autonome (Chrome système piloté, WebGL swiftshader, backend `labuse api`
sur la base applicative). Sonde = `qa/mw_map_probe.mjs` : console + pageerror + réseau (chunks,
tuiles) + **preuve de peinture** (lecture des pixels du canvas WebGL, `preserveDrawingBuffer`
forcé — sinon le screenshot headless est noir à tort). Captures dans `qa/mw_captures/` (local).

### A/B décisif — vite 5 (référence, ce qui tourne en prod) vs vite 8 (M-W)

| scénario | chunk maplibre | tuiles fond | canvas peint (px non noirs /4000) | erreurs console |
|---|---|---|---|---|
| **build vite 5** (main) | 200 | 12×200 | **3529** (20 couleurs) | 0 |
| **build vite 8** (M-W) | 200 | 12×200 | **3529** (20 couleurs) | 0 |
| **dev vite 5** (main) | 200 | 8×200 | peint | 3 × 404 `/moi`,`/events` |
| **dev vite 8** (M-W) | 200 | 8×200 | peint | 3 × 404 `/moi`,`/events` |

**Identique au pixel près entre vite 5 et vite 8, en dev ET en build.** Les trois suspects du
mandat sont innocentés : (a) le `React.lazy(import())` charge bien `MapView-*.js` qui importe
`maplibre-*.js` (arête préservée sous Rolldown) ; (b) le proxy dev sert les tuiles ; (c) la CSS
maplibre (`maplibre-*.css`) suit le chunk (200). Le rendu « sombre » est le fond **dark_nolabels
Carto** zoomé sur l'île entière (océan quasi noir **par design** — le même sur vite 5), pas une
carte absente : 3529/4000 pixels non noirs le prouvent.

## Ce qui trompait réellement — 2 corrections (périmètre config M-W)

### 1. `vite.config.js` fantôme masquait `vite.config.ts` (la cause probable côté user)
`tsconfig.node.json` est `composite: true` → `tsc -b` (dans `npm run build`) **émettait
`vite.config.js`** à côté du `.ts`. Or **Vite résout `.js` AVANT `.ts`** : il chargeait ce
compilé. Conséquence : toute édition de `vite.config.ts` n'était prise en compte en `npm run dev`
**qu'après un rebuild** — et un `vite.config.js` périmé (présent aussi sur main, daté d'avant)
fait tourner le dev sur une **config d'hier**. C'est le piège le plus plausible derrière « ça ne
marche pas / mon correctif n'a pas d'effet ».
**Fix** : `tsconfig.node.json` → `emitDeclarationOnly: true`. Le projet composite garde sa
déclaration (`.d.ts`) mais **n'émet plus le `.js` fantôme** ; Vite charge le `.ts`, source de
vérité unique. Vérifié : après `npm run build`, **aucun `vite.config.js` régénéré**.

### 2. `/moi` et `/events` manquaient au proxy dev → seules erreurs rouges
En `npm run dev`, `/moi` (menu compte) et `/events` (cloche de notifs) **n'étaient pas dans
`apiPaths`** → 404 rouges en console. Pré-existant (identique sur vite 5), sans effet sur la
carte, mais ce sont **les seules erreurs rouges** et le mandat exige une console propre.
**Fix** : ajout de `/moi`, `/events` à `apiPaths` (`vite.config.ts`). Le backend les sert (200) ;
en prod (même origine) ils marchaient déjà.

## Validation — complète (captures jointes dans `qa/mw_captures/`)

- **Carte visible en dev ET build** : `map-dev-final.png`, `map-build-final.png` ; canvas peint
  3529 px non noirs ; la cloche affiche de nouveau son badge (preuve que `/events` répond).
- **Console sans erreur rouge** : dev = 0 erreur, 0 asset ≥400 (après les 2 fix).
- **Garde M-Q intacte** : `test_run_serving_coherence` 3 verts (dont
  `test_bundle_front_construit_sur_le_run_servi`) ; `q_v8_calibre` toujours injecté dans le bundle.
- **`npm audit` : 0** (chaîne esbuild toujours purgée).
- **Tailles de chunks INCHANGÉES** (le fix est config/proxy, le build est identique) :
  maplibre 786,6 kB (gzip 210,0), vendor 170,6 (54,5), index 494,1 (129,3), MapView 33,1 (async),
  TimeMachine 3,6 (async). maplibre toujours hors du graphe initial (lazy M-V intact).
- **vitest 26/26.**

## Interdits respectés
Pas de revert du lazy-load M-V, pas de downgrade de vite. `manualChunks → codeSplitting` conservé.

## Si le user voit encore la carte « vide » après ces fix
Ce n'est pas le code M-W. Reste probable côté environnement, dans l'ordre :
1. **`vite.config.js` périmé sur sa copie** → `rm frontend/vite.config.js` (le fix #1 empêche sa
   réémission ; une copie déjà là doit être supprimée une fois).
2. **Cache d'optim deps vite** après le saut de majeure → `rm -rf frontend/node_modules/.vite`,
   relancer `npm run dev`.
3. **Cache navigateur** (ancien bundle) → rechargement forcé (Cmd+Shift+R).
