// GABARIT-3D-3 LOT 4 — la légende sous le plan-clé est ENTIÈREMENT visible aux 5 tailles (jamais coupée
// par le panneau de la coupe). Contrôle : la boîte de `[data-gab3d-legende]` tient dans la vue ET au-dessus
// du panneau `[data-gab3d-coupe-panneau]`, et ses 4 entrées sont rendues. BZ1065.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-3'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://localhost:10090/socle/'
const IDU = '97411000BZ1065'
const TAILLES = [[1280, 720], [1440, 694], [1440, 900], [1920, 1080], [2560, 1300]]
const PHASE = process.argv[2] || 'after'
const browser = await webkit.launch()

async function ouvrir(page) {
  await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), IDU)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-legende]', { timeout: 20000 })
  await page.waitForTimeout(600)
}
const mesure = (page, w, h) => page.evaluate(({ w, h }) => {
  const leg = document.querySelector('[data-gab3d-legende]')
  const pan = document.querySelector('[data-gab3d-coupe-panneau]')
  if (!leg) return { ok: false, raison: 'légende absente' }
  const r = leg.getBoundingClientRect(), p = pan ? pan.getBoundingClientRect() : null
  const entrees = leg.children.length
  const dansVue = r.top >= -0.5 && r.bottom <= h + 0.5 && r.left >= -0.5 && r.right <= w + 0.5
  const auDessusCoupe = p ? r.bottom <= p.top + 0.5 : true
  return { ok: dansVue && auDessusCoupe && entrees === 4, entrees,
           dansVue, auDessusCoupe, legBottom: Math.round(r.bottom), coupeTop: p ? Math.round(p.top) : null }
}, { w, h })

const res = {}
for (const [w, h] of TAILLES) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'domcontentloaded' })
  await ouvrir(page)
  res[`${w}x${h}`] = await mesure(page, w, h)
  if ((w === 1440 && h === 694) || (w === 1920 && h === 1080)) {
    await page.screenshot({ path: `${OUT}/BZ1065_${w}x${h}_${PHASE}.png` })
    console.log(`[cap] BZ1065_${w}x${h}_${PHASE}.png`)
  }
  await ctx.close()
}
fs.writeFileSync(`${OUT}/legende_${PHASE}.json`, JSON.stringify(res, null, 2))
console.log(`\n== LOT 4 — légende visible (${PHASE}) ==`)
for (const t of Object.keys(res)) console.log(`  ${t}: OK=${res[t].ok} entrées=${res[t].entrees} dansVue=${res[t].dansVue} auDessusCoupe=${res[t].auDessusCoupe} (legBottom=${res[t].legBottom}, coupeTop=${res[t].coupeTop})`)
await browser.close()
