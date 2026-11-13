// GABARIT-3D-2 B2 — PREUVE PAR L'IMAGE : pour chaque témoin à 1440×694, un recadrage agrandi 3× (dsf=3)
// de CHAQUE cote d'altitude, AVANT (placement brut = __gab3dRawCotes, la cote tombe sur le contour/bâti)
// et APRÈS (placement corrigé, cote dégagée). Sorties : docs/audit-2026-11/gabarit-3d-2/zoom/.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-2/zoom'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://localhost:10090/socle/'
const IDUS = [['BZ1065', '97411000BZ1065'], ['CM1658', '97415000CM1658']]
const browser = await webkit.launch()

async function ouvrir(page, idu) {
  await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-canvas] canvas', { timeout: 20000 })
  await page.waitForFunction(() => window.__gab3d?.probe?.pf > 0, { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(500)
}
// rects (viewport CSS px) des cotes d'altitude (divs « 397,0 m ») dans le canvas
const coteRects = (page) => page.evaluate(() => {
  const cv = document.querySelector('[data-gab3d-canvas]'); if (!cv) return []
  return [...cv.querySelectorAll('div')]
    .filter((d) => /\d,\d\s*m$/.test((d.textContent || '').trim()) && d.style.display !== 'none')
    .map((d) => { const b = d.getBoundingClientRect(); return { t: d.textContent.trim(), x: b.x, y: b.y, w: b.width, h: b.height } })
})
async function crops(page, court, phase) {
  const rs = await coteRects(page)
  for (const r of rs) {
    const padX = 60, padY = 36
    const clip = { x: Math.max(0, r.x + r.w / 2 - padX), y: Math.max(0, r.y + r.h / 2 - padY), width: padX * 2, height: padY * 2 }
    const nom = r.t.replace(/[^\d]/g, '')
    await page.screenshot({ path: `${OUT}/${court}_cote${nom}_${phase}.png`, clip })
    console.log(`[zoom] ${court}_cote${nom}_${phase}.png  (« ${r.t} »)`)
  }
}

for (const [court, idu] of IDUS) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 694 }, deviceScaleFactor: 3 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'domcontentloaded' })
  await ouvrir(page, idu)
  await crops(page, court, 'apres')                                   // placement corrigé
  await page.evaluate(() => { window.__gab3dRawCotes = true }); await page.waitForTimeout(600)
  await crops(page, court, 'avant')                                   // placement brut (sur le contour)
  await ctx.close()
}
await browser.close()
