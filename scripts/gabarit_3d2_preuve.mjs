// GABARIT-3D-2 B2 — captures ENTIÈRES demandées : BZ1065 à 1920×1080 et CM1658 à 1280×720, AVANT
// (placement brut __gab3dRawCotes) et APRÈS (corrigé). Sorties : docs/audit-2026-11/gabarit-3d-2/preuve/.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-2/preuve'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://localhost:10090/socle/'
const CAS = [['BZ1065', '97411000BZ1065', 1920, 1080], ['CM1658', '97415000CM1658', 1280, 720]]
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
  await page.waitForTimeout(600)
}

for (const [court, idu, w, h] of CAS) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'domcontentloaded' })
  await ouvrir(page, idu)
  await page.screenshot({ path: `${OUT}/${court}_${w}x${h}_apres.png` })
  console.log(`[preuve] ${court}_${w}x${h}_apres.png`)
  await page.evaluate(() => { window.__gab3dRawCotes = true }); await page.waitForTimeout(600)
  await page.screenshot({ path: `${OUT}/${court}_${w}x${h}_avant.png` })
  console.log(`[preuve] ${court}_${w}x${h}_avant.png`)
  await ctx.close()
}
await browser.close()
