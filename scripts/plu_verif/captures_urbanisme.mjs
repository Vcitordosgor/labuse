// PLU-EXCEPTIONS-1 — capture §Urbanisme (tuiles de règle + « i » d'exception ouvert).
import pw from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright-core/index.js'
const { chromium } = pw
const OUT = '/Users/openclaw/Desktop/labuse-pluverif/docs/audit-2026-09/PLU-EXCEPTIONS-1/captures'
const BASE = 'http://localhost:5865/socle/'
const TEMOINS = [
  { idu: '97422000BE2255', nom: 'le-tampon-Ua-urbanisme' },
  { idu: '97416000CS1429', nom: 'saint-pierre-Uazi-urbanisme' },
]
const EXE = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const browser = await chromium.launch({ executablePath: EXE })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1700 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
for (const t of TEMOINS) {
  try {
    await page.goto(`${BASE}#idu=${t.idu}`, { waitUntil: 'networkidle', timeout: 45000 })
    await page.waitForTimeout(4000)
    await page.getByText('Urbanisme', { exact: true }).first().click({ timeout: 3000 })
    await page.waitForTimeout(1500)
    const tile = await page.$('[data-exception="1"]')
    if (tile) await tile.scrollIntoViewIfNeeded()
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${OUT}/${t.nom}.png`, fullPage: true })
    const info = await page.$('[data-exception="1"] [role="button"]')
    if (info) {
      await info.click({ timeout: 2000 })
      await page.waitForTimeout(900)
      await page.screenshot({ path: `${OUT}/${t.nom}-tooltip.png` })
    }
    console.log('OK', t.nom, info ? '(+tooltip)' : '(tuile marquée introuvable)')
  } catch (e) { console.log('ERREUR', t.nom, String(e).slice(0, 160)) }
}
await browser.close()
