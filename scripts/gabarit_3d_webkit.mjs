// GABARIT-3D-1 (pilote, étape 2) — captures + mesures WebKit (moteur Safari) de la visionneuse 3D.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-1/viewer'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://127.0.0.1:10090/socle/'
// témoins au gabarit « ok » (le bouton Vue 3D n'apparaît pas sur un verdict inconstructible)
const IDUS = ['97411000BZ1065', '97415000CM1658']

const browser = await webkit.launch()
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errs = []
page.on('pageerror', (e) => errs.push(String(e)))

async function ouvrirGabarit(idu) {
  // setModule VIDE selectedIdu (« changer d'outil vide tout ») → sélectionner APRÈS.
  await page.evaluate(() => window.__labuse.setModule('gabarit'))
  await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
}
async function ouvrirVue3D() {
  const t0 = await page.evaluate(() => performance.now())
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-overlay] canvas, [data-gab3d-fallback]', { timeout: 20000 })
  // attend une première frame rendue
  await page.waitForFunction(() => {
    const c = document.querySelector('[data-gab3d-canvas] canvas')
    return c && c.width > 0
  }, { timeout: 20000 }).catch(() => {})
  const t1 = await page.evaluate(() => performance.now())
  return t1 - t0
}
async function fermerVue3D() {
  await page.click('[data-gab3d-close]').catch(() => {})
  await page.waitForSelector('[data-gab3d-overlay]', { state: 'detached', timeout: 5000 }).catch(() => {})
}
async function mesureFPS(ms = 2000) {
  // rotation : drag sur le canvas + compte des frames (rAF)
  const box = await page.$eval('[data-gab3d-canvas] canvas', (c) => {
    const r = c.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }
  }).catch(() => null)
  if (!box) return null
  await page.evaluate(() => { window.__fps = 0; const l = () => { window.__fps++; window.__rafid = requestAnimationFrame(l) }; window.__rafid = requestAnimationFrame(l) })
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2
  await page.mouse.move(cx, cy); await page.mouse.down()
  const steps = 40, start = Date.now()
  for (let i = 0; i < steps; i++) {
    const a = (i / steps) * Math.PI * 2
    await page.mouse.move(cx + Math.cos(a) * 80, cy + Math.sin(a) * 60)
    await page.waitForTimeout(ms / steps)
  }
  await page.mouse.up()
  const frames = await page.evaluate(() => { cancelAnimationFrame(window.__rafid); return window.__fps })
  return Math.round((frames / ((Date.now() - start) / 1000)))
}

const res = { mesures: {}, robustesse: {}, erreurs: [] }

// chargement de l'app
await page.goto(URL, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 30000 })
await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())   // bandeau cookies

// 1) ouverture à FROID (premier chargement du chunk Three.js)
await ouvrirGabarit(IDUS[0])
const froid = await ouvrirVue3D()
await page.waitForTimeout(600)
await page.screenshot({ path: `${OUT}/bz1065_vue3d.png` })
const fps = await mesureFPS()
res.mesures.chargement_froid_ms = Math.round(froid)
res.mesures.fps_rotation = fps
await fermerVue3D()

// 2) ouverture à CHAUD (chunk déjà chargé)
await ouvrirGabarit(IDUS[0])
const chaud = await ouvrirVue3D()
res.mesures.chargement_chaud_ms = Math.round(chaud)
await page.waitForTimeout(400)
await page.screenshot({ path: `${OUT}/bz1065_vue3d_chaud.png` })
await fermerVue3D()

// 3) autres témoins (captures)
for (const idu of IDUS.slice(1)) {
  await ouvrirGabarit(idu)
  await ouvrirVue3D()
  await page.waitForTimeout(500)
  await page.screenshot({ path: `${OUT}/${idu}_vue3d.png` })
  await fermerVue3D()
}

// 4) robustesse : 10 ouvertures à la suite + après une pause (mise en veille simulée)
let ok10 = true
for (let i = 0; i < 10; i++) {
  await ouvrirGabarit(IDUS[i % IDUS.length])
  await ouvrirVue3D()
  await fermerVue3D()
  const hasCanvas = await page.evaluate(() => !!document.querySelector('[data-gab3d-overlay]'))
  if (hasCanvas) ok10 = false
}
await page.waitForTimeout(3000)                 // pause ~ mise en veille
await ouvrirGabarit(IDUS[0])
const apresPause = await ouvrirVue3D()
const canvasApres = await page.evaluate(() => !!document.querySelector('[data-gab3d-canvas] canvas'))
await page.screenshot({ path: `${OUT}/apres_pause.png` })
await fermerVue3D()
// C13 — perte de contexte WebGL FORCÉE en cours d'usage → repli plan + coupes
await ouvrirGabarit(IDUS[0])
await ouvrirVue3D()
const extOk = await page.evaluate(() => {
  const c = document.querySelector('[data-gab3d-canvas] canvas')
  const gl = c && (c.getContext('webgl2') || c.getContext('webgl'))
  const ext = gl && gl.getExtension('WEBGL_lose_context')
  if (ext) ext.loseContext()
  return !!ext
})
await page.waitForTimeout(600)
const repli = await page.evaluate(() => !!document.querySelector('[data-gab3d-fallback]'))
await page.screenshot({ path: `${OUT}/perte_contexte.png` })
await fermerVue3D()

res.robustesse = { dix_ouvertures_sans_fuite: ok10, apres_pause_ms: Math.round(apresPause),
                   canvas_ok_apres_pause: canvasApres,
                   perte_contexte_testee: extOk, perte_contexte_repli: repli }
res.erreurs = errs.slice(0, 10)

fs.writeFileSync(`${OUT}/mesures_webkit.json`, JSON.stringify(res, null, 2))
console.log(JSON.stringify(res, null, 2))
await browser.close()
