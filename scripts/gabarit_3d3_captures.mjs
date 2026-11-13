// GABARIT-3D-3 — captures entières à 1440×694 et 1920×1080 : BZ1065 + 2 des 10 parcelles tirées
// (DX0049 bâtie en pente, CT0442 nue en pente). Sol 0,5 m, légende non coupée, pied qui dit la maille.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-3'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://localhost:10090/socle/'
const CAS = [['BZ1065', '97411000BZ1065'], ['DX0049', '97415000DX0049'], ['CT0442', '97413000CT0442']]
const TAILLES = [[1440, 694], [1920, 1080]]
const browser = await webkit.launch()

async function ouvrir(page, idu) {
  await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-legende]', { timeout: 30000 })
  await page.waitForSelector('[data-gab3d-pied]', { timeout: 30000 }).catch(() => {})
  await page.waitForTimeout(1300)
}

for (const [court, idu] of CAS) {
  for (const [w, h] of TAILLES) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
    const page = await ctx.newPage()
    await page.goto(URL, { waitUntil: 'domcontentloaded' })
    await ouvrir(page, idu)
    const pied = await page.locator('[data-gab3d-pied]').innerText().catch(() => '')
    await page.screenshot({ path: `${OUT}/${court}_${w}x${h}.png` })
    console.log(`[cap] ${court}_${w}x${h}.png — pied: ${pied.replace(/\s+/g, ' ').slice(0, 70)}`)
    await ctx.close()
  }
}
await browser.close()
