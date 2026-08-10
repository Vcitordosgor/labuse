// M55-A point 2 — icônes des nouvelles catégories (marché/crèche/collège-lycée) sur la carte.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-a-couches/captures'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.locator('button:has(span:text-is("Équipements"))').first().click()
await page.waitForTimeout(400)
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.5088, -21.2601], zoom: 15.2 }))
await page.waitForTimeout(3500)
const info = await page.evaluate(() => {
  const m = window.__labuse_map
  const feats = m.queryRenderedFeatures({ layers: ['ov-equip'] })
  const bysub = {}
  for (const f of feats) { const s = f.properties?.subtype; bysub[s] = (bysub[s] || 0) + 1 }
  return { total: feats.length, bysub }
})
console.log('équipements rendus (Entre-Deux):', JSON.stringify(info))
await page.screenshot({ path: `${OUT}/point2_equip_nouvelles_categories.png`, clip: { x: 300, y: 0, width: 1140, height: 900 } })
await browser.close()
