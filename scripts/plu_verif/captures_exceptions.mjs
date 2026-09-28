// PLU-EXCEPTIONS-1 — captures fiche (§Urbanisme + §Potentiel) sur 3 témoins.
// Deux avec exception (Le Tampon Ua, Saint-Pierre Ue/Uazi), un sans (Saint-André).
// Usage : node scripts/plu_verif/captures_exceptions.mjs
import pw from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright-core/index.js'
const { chromium } = pw

const OUT = '/Users/openclaw/Desktop/labuse-pluverif/docs/audit-2026-09/PLU-EXCEPTIONS-1/captures'
const BASE = 'http://localhost:5865/socle/'
const TEMOINS = [
  { idu: '97422000BE2255', nom: 'le-tampon-Ua-avec-exception' },
  { idu: '97416000CS1429', nom: 'saint-pierre-Uazi-avec-exception' },
  { idu: '97409000AB0876', nom: 'saint-andre-sans-exception' },
]

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1600 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()

for (const t of TEMOINS) {
  try {
    await page.goto(`${BASE}#idu=${t.idu}`, { waitUntil: 'networkidle', timeout: 45000 })
    await page.waitForTimeout(4000)
    // déplier les sections « Urbanisme » et « Potentiel » (accordéon de la fiche)
    for (const titre of ['Urbanisme', 'Potentiel']) {
      try { await page.getByText(titre, { exact: true }).first().click({ timeout: 2000 }) } catch {}
      await page.waitForTimeout(800)
    }
    await page.waitForTimeout(800)
    // cadrer la fiche (panneau de droite) pour la capture
    const panel = await page.$('[data-transformation]') || await page.$('[data-forme="tuiles"]')
    if (panel) await panel.scrollIntoViewIfNeeded()
    await page.screenshot({ path: `${OUT}/${t.nom}-fiche.png`, fullPage: true })
    // si exception : cliquer le « i » de la 1re tuile marquée pour ouvrir le texte verbatim
    const info = await page.$('[data-exception="1"] [role="button"]')
    if (info) {
      await info.scrollIntoViewIfNeeded()
      await info.click({ timeout: 1500 })
      await page.waitForTimeout(800)
      await page.screenshot({ path: `${OUT}/${t.nom}-tooltip.png`, fullPage: false })
    }
    console.log('OK', t.nom, info ? '(+tooltip)' : '(pas de tuile marquée trouvée)')
  } catch (e) {
    console.log('ERREUR', t.nom, String(e).slice(0, 200))
  }
}
await browser.close()
