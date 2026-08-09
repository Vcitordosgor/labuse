# M-W micro² — Carte noire chez Vic : rendu MATÉRIEL → cause trouvée → fix

## « Le noir venait de X » (réponse explicite)

**X = un conflit CSS de même spécificité, tranché par l'ORDRE de chargement.**
`maplibre-gl.css` pose `.maplibregl-map { position: relative }` (spéc. 0,1,0). L'app pose
`.absolute { position: absolute }` (Tailwind, spéc. 0,1,0 aussi). Le conteneur de carte porte
**les deux classes** (`<div ref className="absolute inset-0">` + `maplibregl-map` ajoutée par
maplibre). À spécificité égale, **la règle chargée en DERNIER gagne**.

Depuis le **lazy-load M-V (volet 3)**, `MapView` est en `import()` dynamique → sa CSS maplibre
part dans un **chunk séparé chargé APRÈS** le bundle app (l'`index.html` ne précharge que
`index-*.css`). Donc `.maplibregl-map{position:relative}` gagne → le conteneur repasse en
`position: relative` → `inset-0` (top/bottom:0) **n'étire plus** l'élément → ses seuls enfants
étant absolus, sa **hauteur tombe à 0** → la carte est clippée (`overflow:hidden`) → **noir**,
sans la moindre erreur console. WebGL, tuiles, style : tous OK ; c'est purement du layout.

**Pourquoi ma sonde précédente ne l'a pas vu** : elle forçait `preserveDrawingBuffer:true` et
lisait les pixels du canvas *directement* — ce qui **contourne le clipping** du conteneur
0-hauteur. Le canvas était bien peint (300 px de repli maplibre), mais **invisible à l'écran**.
L'angle mort n'était pas swiftshader vs matériel : c'était **lecture-buffer vs compositing-écran**.
(Le matériel a quand même servi à reproduire à l'identique le GPU de Vic — voir ci-dessous.)

## Preuve en rendu MATÉRIEL (le GPU de Vic)

Sonde `qa/mw_map_hw.mjs` : Chrome système, **new-headless avec GPU réel** (pas swiftshader),
`preserveDrawingBuffer` NON forcé → le screenshot reflète ce que voit Vic. Renderer obtenu :
**`ANGLE (Apple, ANGLE Metal Renderer: Apple M1)`** — exactement le backend de Vic.

Chaîne d'ancêtres du conteneur (`qa/mw_chain.mjs`), AVANT fix :

```
h=  0  position:relative height=0px  | div.absolute inset-0 maplibregl-map   ← effondré
h=844  position:relative             | div.relative min-w-0 flex-1           ← parent OK (844px)
```

| | conteneur `.maplibregl-map` | canvas | écran (matériel) |
|---|---|---|---|
| **avant fix** | `ch = 0` | 1076×**300** (repli) | **NOIR** (`hw-hw-ile.png`) — symptôme de Vic |
| **après fix** | `ch = 844` | 1076×**844** | **île peinte + parcelles colorées** (`hw-hw-fixed-*.png`) |

## Périmètre : bug PRÉEXISTANT (M-V), pas vite 8

La cause est le **lazy-load M-V** (splitting de la CSS maplibre), déjà **mergé dans main / servi
en prod** — c'est pour ça que Vic le voit sur `:8000/socle` (build prod). Vite 8 n'y est pour
rien (même bug sur le build vite 5). Interdit respecté : **on ne reverte pas le lazy-load M-V**,
on le rend simplement **immunisé à l'ordre CSS**.

## Fix (minimal, robuste à l'ordre CSS)

Ajout de `h-full w-full` aux conteneurs de carte, en plus de `absolute inset-0` :
- `frontend/src/components/map/MapView.tsx` (carte principale) ;
- `frontend/src/components/outils/TimeMachine.tsx` (comparateur swipe, 2 conteneurs).

Des **dimensions explicites** (`height:100%`/`width:100%` du parent, définitivement 844×1076)
survivent quel que soit le `position` gagnant : si maplibre force `relative`, `h-full/w-full`
gardent la taille ; si l'app garde `absolute`, `inset-0` marche aussi. Zéro dépendance à l'ordre
de chargement des feuilles de style. Deux classes utilitaires déjà présentes dans le bundle
Tailwind → **poids identique** (index 494,11 kB, maplibre 786,6 kB — inchangés).

## Validation

- **Capture matérielle** (`qa/mw_captures/hw-hw-fixed-ile.png`, `…-saint-paul.png`) : **île de La
  Réunion peinte** (fond + 24 limites communales), et **parcelles colorées après zoom sur
  Saint-Paul** (traits verts par verdict). Renderer = ANGLE Metal Apple M1.
- **`canvas.width/height` > 0** : 1076×844 (avant : 1076×300 dans un conteneur 0-hauteur).
- Vérifié en **build ET en dev** (même correctif, `mapEl.ch = 844` des deux côtés).
- Garde M-Q : `test_run_serving_coherence` 3 verts (bundle porte `q_v8_calibre`).
- `npm audit` : **0**. `vitest` : **26/26**. Tailles de chunks **inchangées**.
- Interdits respectés : pas de revert lazy-load M-V, pas de downgrade vite, `manualChunks →
  codeSplitting` conservé.

## Note pour Vic
Le fix corrige la racine dans le code servi. Aucune action navigateur nécessaire ; un simple
rechargement après déploiement suffit (l'ancien bundle en cache reste noir tant qu'il est servi).
Sondes rejouables : `qa/mw_map_hw.mjs` (rendu matériel + parcelles), `qa/mw_chain.mjs` (hauteurs).
