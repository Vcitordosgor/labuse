// COMMUNE-FIX-1 — captures avant/après de la fiche commune (3 témoins), panneau entier, DSR 2 (lisible).
// Usage : node scripts/cf1_capture.mjs <avant|apres>
import pkg from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright-core/index.js'
const { chromium } = pkg

const EXEC = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const OUT = '/Users/openclaw/Desktop/labuse-commune/docs/audit-2026-09/COMMUNE-FIX-1/captures'
const phase = process.argv[2] || 'apres'
const TEMOINS = ['Saint-Paul', 'Saint-Denis', 'Cilaos']
const slug = (c) => c.toLowerCase().replace(/[^a-z]+/g, '-')

const browser = await chromium.launch({ executablePath: EXEC, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 2400 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
await page.goto('http://localhost:5355/socle/', { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(8000)   // laisse la carte + le store s'initialiser

for (const commune of TEMOINS) {
  await page.evaluate((c) => { const s = window.__labuse; s.setContexteCommune(null); s.setContexteCommune(c) }, commune)
  // attend que le panneau ait chargé ses données (une carte connue)
  await page.getByText('Population et logement').first().waitFor({ state: 'visible', timeout: 40000 })
  await page.waitForTimeout(1500)
  await page.evaluate(() => document.querySelectorAll('[data-contexte-panel] details').forEach((d) => (d.open = true)))
  await page.waitForTimeout(600)
  const el = await page.$('[data-contexte-panel]')
  const file = `${OUT}/${phase}-${slug(commune)}.png`
  await el.screenshot({ path: file })
  console.log('captured', file)
}
await browser.close()
console.log('done', phase)
