// VITESSE-CARTE-FIX-1 — PREUVE DE NEUTRALITÉ G1 (head-to-head, pixel par pixel).
// Question : le contour cadastral tiré de la source `parcels-ile` (simplifiée par palier à z9-z11,
// extent 1024 ; full-res extent 4096 à z≥12) rend-il un contour IDENTIQUE à celui servi aujourd'hui
// par la source overlay `limites_parcelles` (mvt_parcels, full-res extent 4096 à TOUS les zooms) ?
//
// Méthode : UNE carte, taille fixe, fond uni (#181918 = app Sombre). Pour chaque zoom, on peint le
// MÊME calque `line` (#8FA69A, width 0.3, opacity 0.4 — le style exact de la couche) depuis la
// source A (limites_parcelles, l'ACTUEL) puis depuis la source B (parcels-ile, le PROPOSÉ), on lit
// le framebuffer (gl.readPixels, preserveDrawingBuffer) et on compare pixel par pixel.
// Sortie : par zoom, nb de pixels qui diffèrent, delta canal max, histogramme des deltas. + PNG A/B.
//
//   LC_ALL=C BASE=http://127.0.0.1:8711 CHROME_BIN=... node neutralite_g1.mjs <outdir>
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
const HERE = dirname(fileURLToPath(import.meta.url))
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const BASE = process.env.BASE ?? 'http://127.0.0.1:8711'
const MLJS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.js')
const MLCSS = join(HERE, '..', '..', '..', '..', 'frontend', 'node_modules', 'maplibre-gl', 'dist', 'maplibre-gl.css')
const CHROME_BIN = process.env.CHROME_BIN
const OUT = process.argv[2] || join(HERE, '..', 'mesures', 'neutralite_g1')
mkdirSync(OUT, { recursive: true })

// vues testées : île (z9), zooms intermédiaires (z10, z11), full-res (z12, z13) — St-Denis dense
const VUES = [
  { z: 9, c: [55.47, -21.12] },   // île entière (centre Réunion)
  { z: 10, c: [55.45, -20.90] },
  { z: 11, c: [55.45, -20.88] },  // commune St-Denis
  { z: 12, c: [55.45, -20.88] },
  { z: 13, c: [55.447, -20.882] },
]
const W = 900, H = 900
const HTML = `<!doctype html><meta charset=utf8><style>html,body,#m{margin:0;height:${H}px;width:${W}px}</style><div id=m></div>`
const PAINT = { 'line-color': '#8FA69A', 'line-width': 0.3, 'line-opacity': 0.4 }

async function run() {
  const browser = await chromium.launch({ executablePath: CHROME_BIN })
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  await page.route(BASE + '/__neu', r => r.fulfill({ contentType: 'text/html', body: HTML }))
  await page.goto(BASE + '/__neu', { waitUntil: 'domcontentloaded' })
  await page.addStyleTag({ path: MLCSS })
  await page.addScriptTag({ path: MLJS })
  await page.evaluate(([base, w, h]) => {
    const ml = window.maplibregl
    ml.setWorkerCount(Math.max(2, Math.min(4, Math.floor((navigator.hardwareConcurrency || 4) / 2))))
    const style = { version: 8, sources: {}, layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#181918' } }] }
    window.__m = new ml.Map({ container: 'm', style, center: [55.45, -20.88], zoom: 9, fadeDuration: 0,
      preserveDrawingBuffer: true, interactive: false, attributionControl: false })
    window.__ready = new Promise(res => window.__m.on('load', res))
    // source A = overlay limites_parcelles (ACTUEL, full-res extent 4096, zoom 0-16)
    // source B = parcels-ile (PROPOSÉ, paliers z9-11 / full z12+, zoom 9-15)
    window.__addSrc = () => {
      const m = window.__m
      if (!m.getSource('A')) m.addSource('A', { type: 'vector', minzoom: 0, maxzoom: 16, tiles: [`${base}/map/tiles/limites_parcelles/{z}/{x}/{y}.pbf`] })
      if (!m.getSource('B')) m.addSource('B', { type: 'vector', minzoom: 9, maxzoom: 15, tiles: [`${base}/map/tiles/{z}/{x}/{y}.pbf`] })
    }
    window.__readPixels = () => {
      const cv = window.__m.getCanvas()
      const gl = cv.getContext('webgl2') || cv.getContext('webgl')
      const buf = new Uint8Array(cv.width * cv.height * 4)
      gl.readPixels(0, 0, cv.width, cv.height, gl.RGBA, gl.UNSIGNED_BYTE, buf)
      // compte les pixels qui diffèrent du fond uni #181918 (24,25,24) → non-vide
      let nbg = 0
      for (let i = 0; i < buf.length; i += 4) {
        if (Math.abs(buf[i] - 24) > 1 || Math.abs(buf[i + 1] - 25) > 1 || Math.abs(buf[i + 2] - 24) > 1) nbg++
      }
      return { buf: Array.from(buf), nbg }
    }
    // attente ROBUSTE : la source du viewport est chargée ET toutes les tuiles peintes, sur 2 frames
    window.__attendre = (src) => new Promise((res) => {
      const m = window.__m
      const t0 = Date.now()
      const check = () => {
        let ok = false
        try { ok = m.isSourceLoaded(src) && m.areTilesLoaded() } catch (e) { ok = false }
        if (ok || Date.now() - t0 > 40000) {
          // 2 rAF + court délai pour garantir la peinture du framebuffer
          requestAnimationFrame(() => requestAnimationFrame(() => setTimeout(res, 200)))
        } else { setTimeout(check, 200) }
      }
      // force une 1re demande de tuiles (repaint) avant de sonder
      m.triggerRepaint(); setTimeout(check, 300)
    })
  }, [BASE, W, H])
  await page.evaluate(() => window.__ready)
  await page.evaluate(() => window.__addSrc())

  const lignes = ['zoom,centre,px_total,px_fond_A,px_fond_B,px_diff,pct_diff,delta_max,px_delta_gt2,px_delta_gt8']
  for (const v of VUES) {
    // peint la variante demandée (contour SEUL sur fond uni), attend le chargement RÉEL, lit le framebuffer
    const peindre = async (src) => {
      return await page.evaluate(async ([src, z, c, paint]) => {
        const m = window.__m
        for (const id of ['CA', 'CB']) if (m.getLayer(id)) m.removeLayer(id)
        m.jumpTo({ center: c, zoom: z })
        m.addLayer({ id: src === 'A' ? 'CA' : 'CB', type: 'line', source: src, 'source-layer': 'parcels', paint })
        await window.__attendre(src)
        return window.__readPixels()
      }, [src, v.z, v.c, PAINT])
    }
    const rA = await peindre('A'); const A = Uint8Array.from(rA.buf)
    await page.screenshot({ path: join(OUT, `z${v.z}_A_limites.png`) })
    const rB = await peindre('B'); const B = Uint8Array.from(rB.buf)
    await page.screenshot({ path: join(OUT, `z${v.z}_B_parcelsile.png`) })
    // ASSERTION ANTI-VIDE : un contour doit avoir peint des milliers de pixels dans CHAQUE variante.
    if (rA.nbg < 1000 || rB.nbg < 1000) {
      console.error(`z${v.z}: CAPTURE VIDE (fond A=${rA.nbg} B=${rB.nbg} px non-fond) — tuiles non peintes, mesure INVALIDE`)
      process.exit(2)
    }
    // diff pixel par pixel (RGBA → on compare RGB, alpha constant sur WebGL opaque)
    let diff = 0, dmax = 0, g2 = 0, g8 = 0
    const npx = W * H
    for (let i = 0; i < npx; i++) {
      const o = i * 4
      const dr = Math.abs(A[o] - B[o]), dg = Math.abs(A[o + 1] - B[o + 1]), db = Math.abs(A[o + 2] - B[o + 2])
      const d = Math.max(dr, dg, db)
      if (d > 0) diff++
      if (d > dmax) dmax = d
      if (d > 2) g2++
      if (d > 8) g8++
    }
    const pct = (100 * diff / npx).toFixed(4)
    lignes.push(`${v.z},"${v.c.join(' ')}",${npx},${rA.nbg},${rB.nbg},${diff},${pct},${dmax},${g2},${g8}`)
    console.log(`z${v.z}: contour=${rA.nbg}/${rB.nbg}px px_diff=${diff}/${npx} (${pct}%) delta_max=${dmax} >2:${g2} >8:${g8}`)
  }
  writeFileSync(join(OUT, 'neutralite_g1.csv'), lignes.join('\n') + '\n')
  console.log('→', join(OUT, 'neutralite_g1.csv'))
  await ctx.close()
  await browser.close()
}
run().catch(e => { console.error(e); process.exit(1) })
