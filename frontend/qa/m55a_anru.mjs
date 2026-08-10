// M55-A-bis — capture ANRU (Saint-Denis, 3 périmètres) pour comparaison avant/après couleur.
// Usage : LABEL=before|after node qa/m55a_anru.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-a-couches/captures'
const LABEL = process.env.LABEL || 'after'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.locator('button:has(span:text-is("ANRU (NPNRU)"))').first().click()
await page.waitForTimeout(500)
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.4655, -20.8855], zoom: 13.4, pitch: 0 }))
await page.waitForTimeout(3500)
const n = await page.evaluate(() => window.__labuse_map.queryRenderedFeatures({ layers: ['ov-anru'] }).length)
console.log(`ANRU polygones rendus: ${n} (${LABEL})`)
await page.screenshot({ path: `${OUT}/anru_${LABEL}.png`, clip: { x: 300, y: 0, width: 1140, height: 900 } })
await browser.close()
