// M-W micro² — sonde carte en rendu MATÉRIEL (GPU Metal), pas swiftshader. Ne force PAS
// preserveDrawingBuffer (on teste le VRAI chemin de compositing des navigateurs de Vic).
// Usage : MODE=hw|sw BASE=http://127.0.0.1:8000/socle/ node qa/mw_map_hw.mjs --tag hw
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const MODE = process.env.MODE || 'hw'
const FORCE_PDB = process.env.PDB === '1'
const tagIdx = process.argv.indexOf('--tag'); const TAG = tagIdx > -1 ? process.argv[tagIdx + 1] : MODE
const OUT = new URL('./mw_captures', import.meta.url).pathname; mkdirSync(OUT, { recursive: true })

const hwArgs = ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=metal', '--enable-webgl', '--enable-accelerated-2d-canvas']
const swArgs = ['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist']
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: MODE === 'sw' ? swArgs : hwArgs })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })

const consoleMsgs = []; page.on('console', (m) => consoleMsgs.push(`${m.type()}: ${m.text()}`))
page.on('pageerror', (e) => consoleMsgs.push(`pageerror: ${e}`))
const carto = { ok: 0, fail: 0, st: {} }
page.on('response', (r) => { if (/cartocdn\.com/.test(r.url())) { const s = r.status(); carto.st[s] = (carto.st[s] || 0) + 1; if (s < 300) carto.ok++; else carto.fail++ } })

// Instrumentation AVANT tout script : capter la création du contexte WebGL, ses attributs, les
// pertes de contexte, et (option) forcer preserveDrawingBuffer pour comparer.
await page.addInitScript((forcePdb) => {
  window.__diag = { ctx: [], lost: 0, restored: 0, mapErrors: [] }
  const orig = HTMLCanvasElement.prototype.getContext
  HTMLCanvasElement.prototype.getContext = function (type, attrs) {
    if (forcePdb && /webgl/.test(type)) attrs = Object.assign({}, attrs, { preserveDrawingBuffer: true })
    const ctx = orig.call(this, type, attrs)
    if (/webgl/.test(type)) {
      window.__diag.ctx.push({ type, ok: !!ctx, attrs: attrs || 'default', lost: ctx ? ctx.isContextLost() : null })
      this.addEventListener('webglcontextlost', () => { window.__diag.lost++ })
      this.addEventListener('webglcontextrestored', () => { window.__diag.restored++ })
    }
    return ctx
  }
}, FORCE_PDB)

console.log(`\n=== SONDE MATÉRIELLE [${TAG}] mode=${MODE} pdb=${FORCE_PDB} ${BASE} ===`)
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch((e) => console.log('goto', String(e).slice(0, 100)))
await page.waitForTimeout(4000)

async function inspect(label) {
  const r = await page.evaluate(() => {
    const cv = document.querySelector('.maplibregl-canvas')
    const mp = document.querySelector('.maplibregl-map')
    const cs = (el) => { if (!el) return null; const s = getComputedStyle(el); return { opacity: s.opacity, filter: s.filter, mixBlend: s.mixBlendMode, transform: s.transform === 'none' ? 'none' : 'set', visibility: s.visibility, display: s.display } }
    // renderer GL réel
    let renderer = null
    try { const c = document.createElement('canvas'); const g = c.getContext('webgl2') || c.getContext('webgl'); const d = g && g.getExtension('WEBGL_debug_renderer_info'); renderer = d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : (g ? 'ok(no-debug-ext)' : 'no-gl') } catch (e) { renderer = 'err:' + e }
    return {
      canvas: cv ? { w: cv.width, h: cv.height, cw: cv.clientWidth, ch: cv.clientHeight, css: cs(cv) } : null,
      mapEl: mp ? { cw: mp.clientWidth, ch: mp.clientHeight, css: cs(mp) } : null,
      diag: window.__diag, renderer,
    }
  })
  console.log(`[${label}] renderer:`, r.renderer)
  console.log(`[${label}] canvas:`, JSON.stringify(r.canvas))
  console.log(`[${label}] mapEl:`, JSON.stringify(r.mapEl))
  console.log(`[${label}] diag:`, JSON.stringify(r.diag))
  await page.screenshot({ path: `${OUT}/hw-${TAG}-${label}.png` })
  // moyenne de luminance de la zone carte (droite) pour trancher noir vs peint
  const lum = await page.evaluate(async () => {
    const cv = document.querySelector('.maplibregl-canvas'); if (!cv) return null
    const t = document.createElement('canvas'); t.width = 60; t.height = 40
    const x = t.getContext('2d'); try { x.drawImage(cv, 0, 0, 60, 40) } catch (e) { return 'draw-err:' + e }
    const d = x.getImageData(0, 0, 60, 40).data; let sum = 0, nb = 0
    for (let i = 0; i < d.length; i += 4) { const L = (d[i] + d[i + 1] + d[i + 2]) / 3; sum += L; if (L > 12) nb++ }
    return { avgLum: +(sum / (d.length / 4)).toFixed(1), nonBlack: nb, total: d.length / 4 }
  })
  console.log(`[${label}] readback luminance:`, JSON.stringify(lum), '(NB: fiable seulement si PDB forcé)')
  return r
}

await inspect('ile')

// zoom sur une commune (Saint-Paul) → parcelles colorées ?
try {
  await page.fill('[data-omnibox]', 'Saint-Paul'); await page.keyboard.press('Enter')
  await page.waitForTimeout(4500)
  await inspect('saint-paul')
} catch (e) { console.log('zoom commune KO:', String(e).slice(0, 100)) }

console.log(`console (${consoleMsgs.length}) :`, consoleMsgs.slice(0, 10).join('\n   • ') || '(vide)')
console.log(`tuiles carto : ok=${carto.ok} fail=${carto.fail} st=${JSON.stringify(carto.st)}`)
console.log(`📸 ${OUT}/hw-${TAG}-*.png`)
await browser.close()
process.exit(0)
