// VITESSE-CARTE-FIX-1 (G2) — PREUVE DE NEUTRALITÉ du `ORDER BY mvt.geom` (pixel par pixel).
// Le ORDER BY (requis pour rendre le cache byte-identique à la volée) change l'ORDRE des features dans
// la tuile, donc ses octets — JAMAIS les pixels. On le prouve : pour 5 couches lourdes × 3 zooms, on
// rend la tuile AVANT (sans ORDER BY) et APRÈS (avec), avec le STYLE RÉEL du front (un calque fill par
// niveau filtré par sous-type + contour), on lit le framebuffer (gl.readPixels) et on compare.
// Les .pbf avant/après et le plan (niveaux/style) sont produits par gen_g2_tiles.py.
//
//   CHROME_BIN=... node neutralite_g2.mjs <tiles_dir> <out_dir>
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
const HERE = dirname(fileURLToPath(import.meta.url))
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const MLJS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.js')
const MLCSS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.css')
const CHROME_BIN = process.env.CHROME_BIN
const TILES = process.argv[2] || '/tmp/g2_tiles'
const OUT = process.argv[3] || join(HERE, '..', 'mesures', 'neutralite_g2')
mkdirSync(OUT, { recursive: true })
const plan = JSON.parse(readFileSync(join(TILES, 'plan.json'), 'utf8'))
const COUCHES = Object.keys(plan)
const ZOOMS = [9, 11, 13]
const CENTRE = [55.447, -20.882]   // St-Denis dense
const W = 800, H = 800
const FALLBACK = '#8892a0'
const HTML = `<!doctype html><meta charset=utf8><style>html,body,#m{margin:0;height:${H}px;width:${W}px}</style><div id=m></div>`

// construit les calques fill(+contour) du front pour une couche (cas polygone — nos 5 couches le sont)
function calques(kind, p) {
  const s = p.style || {}
  const niv = (p.niveaux || []).filter((n) => !n.geometrie || n.geometrie === 'polygone')
  const prop = p.niveaux?.[0]?.propriete || 'subtype'
  const out = []
  if (niv.length) {
    for (const n of niv) out.push({ id: `f-${n.id}`, type: 'fill', source: 's', 'source-layer': kind,
      filter: ['all', ['==', ['geometry-type'], 'Polygon'], ['==', ['get', prop], n.valeur]],
      paint: { 'fill-color': n.couleur, 'fill-opacity': n.opacite ?? s.opacite ?? 0.4 } })
  } else {
    let col = s.couleur || FALLBACK
    if (s.couleur_propriete && s.couleurs) { col = ['match', ['get', s.couleur_propriete]]; for (const [k, v] of Object.entries(s.couleurs)) col.push(k, v); col.push(s.couleur || FALLBACK) }
    out.push({ id: 'f', type: 'fill', source: 's', 'source-layer': kind, filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'fill-color': col, 'fill-opacity': s.opacite ?? 0.4 } })
  }
  if (!p.subdivise) out.push({ id: 'o', type: 'line', source: 's', 'source-layer': kind, filter: ['==', ['geometry-type'], 'Polygon'],
    paint: { 'line-color': (s.trait || s.couleur || FALLBACK), 'line-width': s.epaisseur ?? 1, 'line-opacity': s.trait_opacite ?? 0.9 } })
  return out
}

async function run() {
  const browser = await chromium.launch({ executablePath: CHROME_BIN })
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  // sert la page + les tuiles locales (avant/apres) via interception
  let courant = { kind: null, variante: null, z: null }
  await page.route('http://127.0.0.1:9/**', (route, request) => {
    const u = request.url()
    if (u.endsWith('/__g2')) return route.fulfill({ contentType: 'text/html', body: HTML })
    const m = u.match(/\/t\/(\d+)\/\d+\/\d+\.pbf/)
    if (m) {
      const z = Number(m[1])
      const f = join(TILES, `${courant.kind}_z${z}_${courant.variante}.pbf`)
      if (existsSync(f)) return route.fulfill({ contentType: 'application/x-protobuf', body: readFileSync(f) })
      return route.fulfill({ status: 204, body: '' })
    }
    return route.fulfill({ status: 404, body: '' })
  })
  await page.goto('http://127.0.0.1:9/__g2', { waitUntil: 'domcontentloaded' })
  await page.addStyleTag({ path: MLCSS })
  await page.addScriptTag({ path: MLJS })
  await page.evaluate(([w, h]) => {
    const ml = window.maplibregl; ml.setWorkerCount(2)
    window.__mk = (center, zoom) => { if (window.__m) window.__m.remove()
      window.__m = new ml.Map({ container: 'm', style: { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#181918' } }] },
        center, zoom, fadeDuration: 0, preserveDrawingBuffer: true, interactive: false, attributionControl: false })
      return new Promise((res) => window.__m.on('load', res)) }
    window.__read = () => { const cv = window.__m.getCanvas(); const gl = cv.getContext('webgl2') || cv.getContext('webgl')
      const b = new Uint8Array(cv.width * cv.height * 4); gl.readPixels(0, 0, cv.width, cv.height, gl.RGBA, gl.UNSIGNED_BYTE, b)
      let nbg = 0; for (let i = 0; i < b.length; i += 4) if (Math.abs(b[i] - 24) > 1 || Math.abs(b[i + 1] - 25) > 1 || Math.abs(b[i + 2] - 24) > 1) nbg++
      return { buf: Array.from(b), nbg } }
    window.__paint = (calques) => new Promise((res) => {
      const m = window.__m
      m.addSource('s', { type: 'vector', minzoom: 0, maxzoom: 22, tiles: ['http://127.0.0.1:9/t/{z}/{x}/{y}.pbf'] })
      for (const c of calques) m.addLayer(c)
      const t0 = Date.now()
      const chk = () => { let ok = false; try { ok = m.isSourceLoaded('s') && m.areTilesLoaded() } catch (e) { ok = false }
        if (ok || Date.now() - t0 > 30000) requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(res, 200))); else setTimeout(chk, 200) }
      m.triggerRepaint(); setTimeout(chk, 300) })
  }, [W, H])

  const lignes = ['couche,zoom,px_total,px_avant,px_apres,px_diff,pct_diff,delta_max,px_gt2,px_gt8']
  let pire = 0
  for (const kind of COUCHES) {
    const p = plan[kind]
    for (const z of ZOOMS) {
      // la tuile peut être vide (ex. alea_mvt z13) → on saute si les deux .pbf sont vides
      const fa = join(TILES, `${kind}_z${z}_avant.pbf`), fap = join(TILES, `${kind}_z${z}_apres.pbf`)
      if (readFileSync(fa).length === 0 && readFileSync(fap).length === 0) { console.log(`${kind} z${z}: tuile vide, sautée`); continue }
      const cal = calques(kind, p)
      const snap = async (variante) => {
        courant = { kind, variante, z }
        await page.evaluate(([c, z]) => window.__mk(c, z), [CENTRE, z])
        const r = await page.evaluate((cal) => window.__paint(cal).then(() => window.__read()), cal)
        await page.screenshot({ path: join(OUT, `${kind}_z${z}_${variante}.png`) })
        return r
      }
      const A = await snap('avant'); const Ab = Uint8Array.from(A.buf)
      const B = await snap('apres'); const Bb = Uint8Array.from(B.buf)
      let diff = 0, dmax = 0, g2 = 0, g8 = 0
      const npx = W * H
      for (let i = 0; i < npx; i++) { const o = i * 4
        const d = Math.max(Math.abs(Ab[o] - Bb[o]), Math.abs(Ab[o + 1] - Bb[o + 1]), Math.abs(Ab[o + 2] - Bb[o + 2]))
        if (d > 0) diff++; if (d > dmax) dmax = d; if (d > 2) g2++; if (d > 8) g8++ }
      pire = Math.max(pire, g8)
      lignes.push(`${kind},${z},${npx},${A.nbg},${B.nbg},${diff},${(100 * diff / npx).toFixed(4)},${dmax},${g2},${g8}`)
      console.log(`${kind} z${z}: contour av/ap=${A.nbg}/${B.nbg} px_diff=${diff} (${(100 * diff / npx).toFixed(4)}%) delta_max=${dmax} >2:${g2} >8:${g8}`)
    }
  }
  writeFileSync(join(OUT, 'neutralite_g2.csv'), lignes.join('\n') + '\n')
  console.log(`→ ${join(OUT, 'neutralite_g2.csv')} · pire delta>8 = ${pire} px`)
  await ctx.close(); await browser.close()
}
run().catch(e => { console.error(e); process.exit(1) })
