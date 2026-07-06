// Capture Playwright du Socle V1 (revue Vic). Vérifie aussi les erreurs console/page.
// Usage : BASE=http://127.0.0.1:8010/socle/ node scripts/capture.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
page.on('pageerror', (e) => errors.push('PAGEERROR ' + e.message))

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForSelector('text=chaudes', { timeout: 15000 })
await page.waitForTimeout(4000) // tuiles carte + rendu parcelles

await page.screenshot({ path: `${OUT}/01_dashboard.png` })

// Ouvrir une fiche : clic sur la 1re carte résultat
const firstCard = page.locator('.overflow-y-auto > button').first()
await firstCard.click()
await page.waitForTimeout(800)
await page.screenshot({ path: `${OUT}/02_fiche_ouverte.png` })

// Fermer + bascule Mutabilité
await page.locator('button[title="Fermer"]').click().catch(() => {})
await page.locator('button:has-text("Mutabilité")').click()
await page.waitForTimeout(1500)
await page.screenshot({ path: `${OUT}/03_mutabilite.png` })

console.log('CONSOLE ERRORS:', errors.length ? errors.slice(0, 10) : 'aucune')
await browser.close()
