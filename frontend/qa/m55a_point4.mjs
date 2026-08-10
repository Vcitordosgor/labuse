// M55-A point 4 — chevrons uniformisés (FiltreLabuse + ResultsSection). Dev server vite.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-a-couches/captures'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
// afficher l'analyse LABUSE → ResultsSection + FiltreLabuse apparaissent
await page.locator('[data-verdict-on]').first().click()
await page.waitForTimeout(1500)
await page.locator('aside').first().screenshot({ path: `${OUT}/point4_chevrons_panel.png` })
// ouvrir un tiroir de filtre pour voir la bascule gauche→bas
const tiroir = page.locator('button:has-text("Puis-je construire")').first()
if (await tiroir.count()) { await tiroir.click(); await page.waitForTimeout(500) }
await page.locator('aside').first().screenshot({ path: `${OUT}/point4_chevrons_ouvert.png` })
console.log('point4 capture OK')
await browser.close()
