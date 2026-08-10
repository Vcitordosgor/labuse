// M55-B point 3 — état de chargement (spinner loupe) + état vide (toast).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-b-recherche-fiche/captures'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
// retarde la recherche IDU pour rendre le spinner CAPTURABLE
await page.route('**/parcels/search**', async (route) => {
  await new Promise((r) => setTimeout(r, 1500)); route.continue()
})
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1200)
const omni = page.locator('[data-omnibox]').first()
const loupe = page.locator('button[aria-label="Lancer la recherche"]').first()
// 1) état de chargement : IDU improbable → passe par /parcels/search (retardé) → spinner
await omni.click(); await omni.type('AB0189', { delay: 20 })
await page.waitForTimeout(300)
await loupe.click()
await page.waitForTimeout(400)
console.log('bouton aria-busy pendant recherche:', await loupe.getAttribute('aria-busy'))
await page.screenshot({ path: `${OUT}/p3_loading.png`, clip: { x: 0, y: 0, width: 720, height: 90 } })
await page.waitForTimeout(1800)
// 2) état vide : requête sans résultat → toast honnête
await omni.click(); await omni.press('Control+A'); await omni.press('Delete')
await omni.type('ZZZQXW9999', { delay: 20 })
await page.waitForTimeout(300)
await loupe.click()
await page.waitForTimeout(2200)
await page.screenshot({ path: `${OUT}/p3_empty_toast.png`, clip: { x: 0, y: 0, width: 1440, height: 900 } })
const toast = await page.locator('text=/Aucune commune, parcelle ni adresse/').count()
console.log('toast vide présent:', toast > 0)
await browser.close()
