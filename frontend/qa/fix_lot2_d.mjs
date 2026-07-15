// FIX LOT 2 — D : drawer radar permis (géocodé → localiser ; non géocodé → message).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1360, height: 950 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setModule('permis'))
await p.waitForSelector('button:has-text("mois")', { timeout: 10000 })
await p.waitForTimeout(2000)

// permis GÉOCODÉ : une ligne SANS le badge « non géocodé »
const geoRow = p.locator('[data-permis-row][data-geocode="1"]').first()
await geoRow.click()
await p.waitForSelector('[data-permis-drawer]', { timeout: 10000 })
await p.waitForTimeout(800)
const hasLoc = await p.locator('[data-permis-localiser]').count()
console.log('D géocodé : bouton « Voir la parcelle » présent =', hasLoc > 0)
await p.locator('[data-permis-drawer] > div').screenshot({ path: `${OUT}/fixD-permis-geocode.png` })
// clic localiser → drawer se ferme + parcelle sélectionnée
if (hasLoc) { await p.locator('[data-permis-localiser]').click(); await p.waitForTimeout(2000) }
const sel = await p.evaluate(() => !!document.querySelector('aside'))
console.log('D localiser → carte (drawer fermé, parcelle ciblée) =', sel)
await p.screenshot({ path: `${OUT}/fixD-permis-localise-carte.png` })

// permis NON GÉOCODÉ : une ligne AVEC le badge
await p.evaluate(() => window.__labuse.setModule('permis'))
await p.waitForSelector('button:has-text("mois")', { timeout: 10000 })
await p.waitForTimeout(1500)
const ngRow = p.locator('[data-permis-row][data-geocode="0"]').first()
const ngCount = await ngRow.count()
if (ngCount) {
  await ngRow.click()
  await p.waitForSelector('[data-permis-nongeocode]', { timeout: 10000 })
  await p.waitForTimeout(600)
  console.log('D non géocodé : message =', (await p.locator('[data-permis-nongeocode]').innerText()).replace(/\s+/g, ' ').slice(0, 90))
  await p.locator('[data-permis-drawer] > div').screenshot({ path: `${OUT}/fixD-permis-nongeocode.png` })
} else console.log('D : aucun non-géocodé dans la fenêtre visible')
await b.close()
console.log('captures D OK')
