# M-V · Volet 3 — Chunk maplibre : chargement différé (code-splitting)

**Problème** : `maplibre-gl` (~802 kB / 217 kB gzip) était `modulepreload`é dans `index.html`
donc chargé au **premier écran**, alors que la carte n'est pas toujours le premier besoin
(login, fiche directe, outils). `manualChunks` isolait déjà maplibre dans son chunk — mais le
chunk restait dans le **graphe initial** car `App.tsx` importait `MapView`/`TimeMachine`
statiquement (et eux importent maplibre-gl).

**Fix** : `MapView` et `TimeMachine` passent en **import dynamique** (`React.lazy(() => import(…))`)
derrière un `<Suspense fallback={<MapLoading/>}>` (état de chargement propre : spinner +
« Chargement de la carte… », jamais d'écran blanc). `manualChunks` **conservé** (mandat) — on
diffère le chargement, on ne retouche pas le découpage. **Aucune montée de version** (vite reste 5.x).

**Mesure (build de prod, avant/après)**

| | maplibre dans `index.html` | JS initial (eager, brut) | JS initial (eager, **gzip**) |
|---|---|---|---|
| avant (main) | **oui** (`modulepreload`) | index 514 + vendor 185 + maplibre 802 = **1 502 kB** | **415 kB** |
| après (M-V V3) | **non** | index 473 + vendor 185 = **659 kB** | **186 kB** |

→ **−843 kB brut / −229 kB gzip (−55 %)** au premier écran. maplibre (217 kB gzip) + le code
`MapView` (10 kB gzip) sont désormais des chunks **asynchrones**, chargés au premier affichage
carte : `MapView-*.js` (33 kB) et `TimeMachine-*.js` (3,6 kB) apparaissent, `maplibre-*.js` sort
du `index.html`.

**Validation** :
- `npx tsc -b` : exit 0. `vite build` : OK. **Aucun avertissement nouveau** — le seul warning
  (« chunks larger than 500 kB ») est **pré-existant** (maplibre 802 kB, présent avant comme après).
- `index.html` ne référence plus `maplibre-*.js` (vérifié : `grep -c maplibre dist/index.html` = 0).
- `vitest run` : 26/26 verts (aucun test ne touchait App/MapView).
- La carte s'affiche normalement après le lazy-load (chunks MapView + maplibre chargés à la
  bascule vue « cartes »).
