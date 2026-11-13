// GABARIT-3D-2 LOT B — harnais : B1 part de la vue occupée par le CONTOUR (doit augmenter), B2 les cotes
// d'altitude ne sont plus TRAVERSÉES par le contour. Mesuré à l'OUVERTURE et après « Recentrer », aux 5
// tailles, BZ1065 + CM1658. Capture à 1440×694. Phase (before|after) passée en argv → nomme les sorties.
//   node scripts/gabarit_3d2_viewer.mjs before   (puis, après le correctif) ... after
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const PHASE = process.argv[2] || 'run'
const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-2'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://localhost:10090/socle/'
const IDUS = [['BZ1065', '97411000BZ1065'], ['CM1658', '97415000CM1658']]
const TAILLES = [[1280, 720], [1440, 694], [1440, 900], [1920, 1080], [2560, 1300]]
const browser = await webkit.launch()
const res = {}

async function ouvrir(page, idu) {
  await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-canvas] canvas', { timeout: 20000 })
  await page.waitForFunction(() => window.__gab3d?.probe?.pf > 0, { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(400)
}
const lire = (page) => page.evaluate(() => {
  const p = window.__gab3d?.probe || {}
  const c = window.__gab3dCotesAudit ? window.__gab3dCotesAudit() : null
  return { contourPct: p.contourPct, cadre: p.cadre, cotes: c }
})

for (const [court, idu] of IDUS) {
  res[court] = {}
  for (const [w, h] of TAILLES) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
    const page = await ctx.newPage()
    await page.goto(URL, { waitUntil: 'domcontentloaded' })
    await ouvrir(page, idu)
    const ouv = await lire(page)
    await page.click('[data-gab3d-recentrer]'); await page.waitForTimeout(500)
    const rec = await lire(page)
    res[court][`${w}x${h}`] = { ouverture: ouv, recentrer: rec }
    if (w === 1440 && h === 694) {
      await page.screenshot({ path: `${OUT}/${court}_1440x694_${PHASE}.png` })
      console.log(`[cap] ${court}_1440x694_${PHASE}.png`)
    }
    await ctx.close()
  }
}
fs.writeFileSync(`${OUT}/mesures_${PHASE}.json`, JSON.stringify(res, null, 2))
console.log(`\n== ${PHASE} — contourPct + 3 règles des cotes (OK = ni contour/bâti, ≤40 px, sur terrain) ==`)
const fmt = (c) => {
  if (!c?.cotes) return '?'
  const k = c.cotes, hd = k.hi_detail || {}, ld = k.lo_detail || {}
  return `OK=${k.ok} trav=${k.hi_traverse || k.lo_traverse} dist(hi/lo)=${hd.dist}/${ld.dist} terr=${hd.sur_terrain && ld.sur_terrain}`
}
for (const court of Object.keys(res)) for (const t of Object.keys(res[court])) {
  const o = res[court][t].ouverture, r = res[court][t].recentrer
  console.log(`  ${court} ${t}: ouv ${fmt(o)} contour=${o.contourPct}% | rec ${fmt(r)}`)
}
await browser.close()
