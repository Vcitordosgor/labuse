// VITESSE-CARTE-1 — banc NAVIGATEUR carte/couches (LECTURE SEULE).
// Page MapLibre autonome servie SUR L'ORIGINE de l'API (:8710) → mêmes endpoints de tuiles, pas de
// CORS, worker maplibre identique au réglage de l'app (setWorkerCount = min(4, floor(hc/2))). On
// mesure ce que l'app ne laisse pas instrumenter facilement : coût navigateur (parse worker + peinture
// GPU) et incrément d'ACTIVATION de couches (1 → 5 → 10 des plus lourdes), le PAN, et la bascule 2D/3D.
// Chaque scénario : réseau (n tuiles, octets), temps jusqu'à `idle` (toutes tuiles peintes), blocage
// du fil principal (long-tasks). 3 passages, médiane.
//   BASE=http://127.0.0.1:8710 node carte_bench.mjs > ../mesures/carte_bench.csv
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
const HERE = dirname(fileURLToPath(import.meta.url))
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const BASE = process.env.BASE ?? 'http://127.0.0.1:8710'
const MLJS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.js')
const MLCSS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.css')
const CHROME_BIN = process.env.CHROME_BIN

// St-Denis : île z9, commune z11, parcelle z14 (centres)
const VIEWS = { ile: { c: [55.45, -20.88], z: 9 }, commune: { c: [55.45, -20.88], z: 11 }, parcelle: { c: [55.447, -20.882], z: 14 } }
// couches overlay par poids décroissant (mesuré server_tiles.csv)
const LOURDES = ['alea_mvt', 'ppr', 'batiment', 'alea_inondation', 'plu_gpu_zone', 'artificialisation', 'sup', 'ebc', 'znieff', 'dpu']

const HTML = `<!doctype html><meta charset=utf8><style>html,body,#m{margin:0;height:100%;width:100%}</style><div id=m></div>`

function pctl(a, p) { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(p * s.length))] }

async function run() {
  const browser = await chromium.launch({ executablePath: CHROME_BIN })
  console.log('scenario,passe,n_tuiles,octets_ko,idle_ms,lt_n,lt_ms')
  for (let passe = 0; passe < 3; passe++) {
    const ctx = await browser.newContext()
    const page = await ctx.newPage()
    // sert la page banc sur l'origine API (même origine que les tuiles)
    await page.route(BASE + '/__bench', r => r.fulfill({ contentType: 'text/html', body: HTML }))
    // compteur réseau tuiles
    let tiles = [], bytes = 0
    page.on('response', resp => {
      const u = resp.url()
      if (/\/map\/tiles\//.test(u) || /elevation-tiles|terrarium/.test(u)) {
        tiles.push(u)
        bytes += Number(resp.headers()['content-length'] || 0)  // octets SUR LE FIL (gzip)
      }
    })
    await page.goto(BASE + '/__bench', { waitUntil: 'domcontentloaded' })
    await page.addStyleTag({ path: MLCSS })
    await page.addScriptTag({ path: MLJS })
    // observe les long-tasks
    await page.evaluate(() => {
      window.__lt = []
      new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push(e.duration) }).observe({ entryTypes: ['longtask'] })
    })
    // crée la carte à la vue île, parcelles + limites (défaut Repères)
    await page.evaluate(([base, view]) => {
      const ml = window.maplibregl
      const hc = navigator.hardwareConcurrency || 4
      ml.setWorkerCount(Math.max(2, Math.min(4, Math.floor(hc / 2))))
      const style = { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#181918' } }] }
      window.__map = new ml.Map({ container: 'm', style, center: view.c, zoom: view.z, fadeDuration: 0 })
      const m = window.__map
      window.__ready = new Promise(res => m.on('load', res))
      window.__tileLayers = (kinds, srcPrefix, extent) => {
        for (const k of kinds) {
          const sid = srcPrefix + k
          if (!m.getSource(sid)) m.addSource(sid, { type: 'vector', tiles: [`${base}/map/tiles/${k}/{z}/{x}/{y}.pbf`], minzoom: 0, maxzoom: 15 })
          if (!m.getLayer('L' + k)) m.addLayer({ id: 'L' + k, type: 'fill', source: sid, 'source-layer': k, paint: { 'fill-color': '#c33', 'fill-opacity': 0.4 } })
        }
      }
    }, [BASE, VIEWS.ile])
    await page.evaluate(() => window.__ready)
    // parcelles (route dédiée) ajoutées APRÈS le load du style
    await page.evaluate(base => {
      const m = window.__map
      m.addSource('parcels-ile', { type: 'vector', tiles: [`${base}/map/tiles/{z}/{x}/{y}.pbf`], minzoom: 9, maxzoom: 15 })
      m.addLayer({ id: 'ile-fill', type: 'fill', source: 'parcels-ile', 'source-layer': 'parcels', paint: { 'fill-color': '#2a4', 'fill-opacity': 0.3 } })
    }, BASE)

    const snap = async (label, setup) => {
      tiles = []; bytes = 0
      await page.evaluate(() => { window.__lt = [] })
      const t0 = Date.now()
      if (setup) await page.evaluate(setup)
      // attendre idle (toutes tuiles du viewport peintes), plafonné à 25 s
      await page.evaluate(() => new Promise(res => { const m = window.__map; const t = setTimeout(res, 25000); const done = () => { clearTimeout(t); res() }; if (m.loaded() && m.areTilesLoaded && m.areTilesLoaded()) return done(); m.once('idle', done) }))
      const idle = Date.now() - t0
      const lt = await page.evaluate(() => window.__lt || [])
      console.log(`${label},${passe},${tiles.length},${(bytes / 1024).toFixed(0)},${idle},${lt.length},${lt.reduce((a, b) => a + b, 0).toFixed(0)}`)
    }

    // S1 — île : parcelles + limites (défaut). Mesure après load.
    await snap('ile_defaut+limites', () => { window.__tileLayers(['limites_parcelles'], 'tuyau-') })
    // S4a — activer 1 couche lourde (alea_mvt)
    await snap('activer_1_lourde', () => { window.__tileLayers(['alea_mvt'], 'tuyau-') })
    // S4b — activer 5 couches lourdes
    await snap('activer_5_lourdes', () => { window.__tileLayers(['ppr', 'batiment', 'alea_inondation', 'plu_gpu_zone', 'artificialisation'], 'tuyau-') })
    // S4c — activer 10 couches lourdes
    await snap('activer_10_lourdes', () => { window.__tileLayers(['sup', 'ebc', 'znieff', 'dpu'], 'tuyau-') })
    // S2 — zoom commune z11
    await snap('zoom_commune_z11', () => { window.__map.jumpTo({ center: [55.45, -20.88], zoom: 11 }) })
    // S2 — zoom parcelle z14
    await snap('zoom_parcelle_z14', () => { window.__map.jumpTo({ center: [55.447, -20.882], zoom: 14 }) })
    // S3 — pan latéral z14
    await snap('pan_z14', () => { window.__map.panBy([600, 0], { duration: 0 }) })
    // S5 — 2D→3D (terrain DEM externe + pitch)
    await snap('bascule_3d', () => {
      const m = window.__map
      if (!m.getSource('dem')) m.addSource('dem', { type: 'raster-dem', encoding: 'terrarium', tileSize: 256, maxzoom: 13, tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'] })
      m.setTerrain({ source: 'dem', exaggeration: 1.35 }); m.easeTo({ pitch: 55, duration: 0 })
    })
    await ctx.close()
  }
  await browser.close()
}
run().catch(e => { console.error(e); process.exit(1) })
