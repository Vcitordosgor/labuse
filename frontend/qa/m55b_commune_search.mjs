// M55-B point 2 — la recherche par commune fonctionne-t-elle toujours (Entrée sur un nom) ?
import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1500)
const before = await page.evaluate(() => location.hash)
const omni = page.locator('[data-omnibox]').first()
await omni.click(); await omni.type('Saint-Paul', { delay: 30 })
await page.waitForTimeout(400)
await omni.press('Enter')
await page.waitForTimeout(1500)
// la commune active est reflétée dans le sélecteur de commune du header
const communeLabel = await page.locator('[data-commune-select]').first().innerText()
console.log('placeholder:', await omni.getAttribute('placeholder'))
console.log('commune active après "Saint-Paul" + Entrée:', JSON.stringify(communeLabel.trim()))
await browser.close()
