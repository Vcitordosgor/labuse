// M-W micro-mandat — sonde carte après vite 8. Capture console/pageerror/network + présence du
// canvas maplibre + screenshot. Usage : BASE=http://127.0.0.1:8000/socle/ node qa/mw_map_probe.mjs --tag build
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const tagIdx = process.argv.indexOf('--tag')
const TAG = tagIdx > -1 ? process.argv[tagIdx + 1] : 'run'
const OUT = new URL('./mw_captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const errors = []
const pageErrors = []
const failed = []
const badResp = []
const mapReq = []
const tiles = { ok: 0, fail: 0, statuses: {} }
const workers = []

// host = macOS 13 : le chromium bundlé de Playwright 1.62 ne le supporte plus → on pilote le
// Google Chrome système (channel). Flags swiftshader : WebGL logiciel en headless (sinon la
// carte maplibre ne peint pas → screenshot noir trompeur).
const HEADED = process.env.HEADED === '1'
const browser = await chromium.launch({
  channel: 'chrome',
  headless: !HEADED,
  args: HEADED ? [] : ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'],
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
// Force preserveDrawingBuffer pour que le framebuffer WebGL soit LISIBLE (screenshot + pixels) en
// headless — sinon la carte peint mais le buffer est vidé avant capture (→ noir trompeur).
await page.addInitScript(() => {
  const orig = HTMLCanvasElement.prototype.getContext
  HTMLCanvasElement.prototype.getContext = function (type, attrs) {
    if (type === 'webgl' || type === 'webgl2') attrs = Object.assign({}, attrs, { preserveDrawingBuffer: true })
    return orig.call(this, type, attrs)
  }
})
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => pageErrors.push(String(e && e.stack || e)))
page.on('requestfailed', (r) => failed.push(`${r.url()} :: ${r.failure()?.errorText}`))
page.on('response', (r) => {
  const u = r.url()
  if (/maplibre-|MapView-/.test(u)) mapReq.push(`${r.status()} ${u.split('/').pop()}`)
  if (r.status() >= 400) badResp.push(`${r.status()} ${u}`)
  if (/cartocdn\.com|data\.geopf\.fr/.test(u)) {          // tuiles de fond de plan (raster)
    const s = r.status(); tiles.statuses[s] = (tiles.statuses[s] || 0) + 1
    if (s >= 200 && s < 300) tiles.ok++; else tiles.fail++
  }
  if (/worker/i.test(u) && /\.js/.test(u)) workers.push(`${r.status()} ${u.split('/').pop()}`)
})

console.log(`\n=== SONDE CARTE [${TAG}] ${BASE} ===`)
try {
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
} catch (e) { console.log('goto:', String(e).slice(0, 140)) }

// laisse le lazy-load + l'init maplibre se faire
await page.waitForTimeout(3500)

// canvas maplibre présent ? dimensions ?
const canvas = await page.evaluate(() => {
  const c = document.querySelector('.maplibregl-canvas')
  const map = document.querySelector('.maplibregl-map')
  const loading = Array.from(document.querySelectorAll('*')).some((e) => /Chargement de la carte/i.test(e.textContent || ''))
  const rect = (e) => e ? (({ x, y, width, height }) => ({ x: Math.round(x), y: Math.round(y), w: Math.round(width), h: Math.round(height) }))(e.getBoundingClientRect()) : null
  let gl = false, glVendor = null
  if (c) { try { const ctx = c.getContext('webgl2') || c.getContext('webgl'); gl = !!ctx; if (ctx) { const d = ctx.getExtension('WEBGL_debug_renderer_info'); glVendor = d ? ctx.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'ok' } } catch { /* */ } }
  return {
    hasCanvas: !!c, hasMapContainer: !!map, stuckLoading: loading,
    canvasRect: rect(c), mapRect: rect(map), webgl: gl, glRenderer: glVendor,
  }
})

// Le framebuffer WebGL a-t-il des pixels NON NOIRS ? (la carte a-t-elle peint des tuiles ?)
const painted = await page.evaluate(() => {
  const c = document.querySelector('.maplibregl-canvas')
  if (!c || !c.width) return { ok: false, why: 'pas de canvas' }
  const tmp = document.createElement('canvas'); tmp.width = 80; tmp.height = 50
  const ctx = tmp.getContext('2d')
  try { ctx.drawImage(c, 0, 0, 80, 50) } catch (e) { return { ok: false, why: 'drawImage: ' + e } }
  const d = ctx.getImageData(0, 0, 80, 50).data
  let nonBlack = 0, distinct = new Set()
  for (let i = 0; i < d.length; i += 4) {
    if (d[i] > 12 || d[i + 1] > 12 || d[i + 2] > 12) nonBlack++
    distinct.add(`${d[i] >> 4},${d[i + 1] >> 4},${d[i + 2] >> 4}`)
  }
  return { ok: nonBlack > 50, nonBlackPx: nonBlack, distinctColors: distinct.size, total: d.length / 4 }
})

await page.screenshot({ path: `${OUT}/map-${TAG}.png`, fullPage: false })

console.log('canvas maplibre :', JSON.stringify(canvas))
console.log('carte a PEINT :', JSON.stringify(painted))
console.log('tuiles fond (raster) :', `ok=${tiles.ok} fail=${tiles.fail} statuts=${JSON.stringify(tiles.statuses)}`)
console.log(`workers (${workers.length}) :`, workers.slice(0, 4).join(' | ') || '(aucun)')
console.log(`chunks carte (${mapReq.length}) :`, mapReq.slice(0, 12).join(' | ') || '(aucun)')
console.log(`erreurs console (${errors.length}) :`, errors.slice(0, 8).join('\n   • ') || '(aucune)')
console.log(`pageerror (${pageErrors.length}) :`, pageErrors.slice(0, 4).join('\n   • ') || '(aucune)')
console.log(`requêtes échouées (${failed.length}) :`, failed.slice(0, 8).join('\n   • ') || '(aucune)')
console.log(`assets js/css >=400 (${badResp.length}) :`, badResp.slice(0, 8).join('\n   • ') || '(aucun)')
console.log(`📸 ${OUT}/map-${TAG}.png`)

await browser.close()
const verdict = canvas.hasCanvas && canvas.webgl && painted.ok && pageErrors.length === 0
console.log(`VERDICT [${TAG}] : ${verdict ? 'CARTE OK' : 'CARTE KO'}`)
process.exit(0)
