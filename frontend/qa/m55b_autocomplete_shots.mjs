import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-b-recherche-fiche/captures'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1500)
const omni = page.locator('[data-omnibox]').first()
// suggestions (after fix)
await omni.click(); await omni.type('3 chemin de la citerne', { delay: 35 })
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/p1_suggestions_after.png`, clip: { x: 0, y: 0, width: 720, height: 380 } })
// état vide honnête
await omni.click(); await omni.press('Control+A'); await omni.press('Backspace')
await omni.type('zzzqxwv adresse inexistante', { delay: 25 })
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/p1_empty_state.png`, clip: { x: 0, y: 0, width: 720, height: 300 } })
console.log('captures p1 OK')
await browser.close()
