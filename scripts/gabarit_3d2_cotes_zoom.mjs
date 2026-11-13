// GABARIT-3D-2 B2 — PREUVE PAR L'IMAGE. Pour chaque témoin à 1440×694 : la vue ENTIÈRE, puis un recadrage
// agrandi 3× (dsf=3) centré sur le POINT MESURÉ (la pastille) de chaque cote — on voit la pastille, le filet
// et l'étiquette ensemble, dégagés. AVANT (placement brut __gab3dRawCotes) et APRÈS (corrigé).
// Sorties : docs/audit-2026-11/gabarit-3d-2/zoom/.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-2/zoom'
fs.mkdirSync(OUT, { recursive: true })
const FULL = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-2'
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
// POINTS mesurés = pastilles (cercles #ffd36a) ; on apparie chaque pastille à la cote la plus proche.
const points = (page) => page.evaluate(() => {
  const cv = document.querySelector('[data-gab3d-canvas]'); if (!cv) return []
  const labs = [...cv.querySelectorAll('div')].filter((d) => /\d,\d\s*m$/.test((d.textContent || '').trim()) && d.style.display !== 'none')
    .map((d) => { const b = d.getBoundingClientRect(); return { t: d.textContent.trim(), cx: b.x + b.width / 2, cy: b.y + b.height / 2 } })
  return [...cv.querySelectorAll('circle')].filter((c) => (c.getAttribute('fill') || '').toLowerCase() === '#ffd36a' && c.style.display !== 'none')
    .map((c) => { const b = c.getBoundingClientRect(), x = b.x + b.width / 2, y = b.y + b.height / 2
      let best = null, bd = 1e9; for (const l of labs) { const dd = Math.hypot(l.cx - x, l.cy - y); if (dd < bd) { bd = dd; best = l } }
      return { x, y, t: best ? best.t : '?' } })
})
async function cropPoints(page, court, phase) {
  const pts = await points(page)
  for (const p of pts) {
    const padX = 66, padY = 42
    const clip = { x: Math.max(0, p.x - padX), y: Math.max(0, p.y - padY), width: padX * 2, height: padY * 2 }
    const nom = p.t.replace(/[^\d]/g, '')
    await page.screenshot({ path: `${OUT}/${court}_point${nom}_${phase}.png`, clip })
    console.log(`[pt] ${court}_point${nom}_${phase}.png  (« ${p.t} »)`)
  }
}

for (const [court, idu] of IDUS) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 694 }, deviceScaleFactor: 3 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'domcontentloaded' })
  await ouvrir(page, idu)
  await page.screenshot({ path: `${FULL}/${court}_1440x694_after.png` })   // vue ENTIÈRE (après)
  console.log(`[full] ${court}_1440x694_after.png`)
  await cropPoints(page, court, 'apres')
  await page.evaluate(() => { window.__gab3dRawCotes = true }); await page.waitForTimeout(600)
  await cropPoints(page, court, 'avant')
  await ctx.close()
}
await browser.close()
