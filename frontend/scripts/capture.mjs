// Capture + vérification du Socle V1 (filtres + fiche). Vérifie console/page.
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
await page.waitForTimeout(4000)
await page.screenshot({ path: `${OUT}/01_dashboard.png` })

// Fiche — top résultat (Synthèse : barres Q/A dépliables)
await page.locator('.overflow-y-auto > button').first().click()
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/04_fiche_synthese.png` })

// Onglet Règles
await page.getByRole('button', { name: 'Règles', exact: true }).click()
await page.waitForTimeout(500)
await page.screenshot({ path: `${OUT}/05_fiche_regles.png` })

// Fiche événementielle : AC 0253 (filtrer Chaude puis cliquer sa carte)
await page.locator('button[title="Fermer"]').click().catch(() => {})
await page.getByRole('button', { name: /^Chaude/ }).first().click()
await page.waitForTimeout(800)
const ac = page.locator('.overflow-y-auto > button', { hasText: 'AC 0253' }).first()
await ac.scrollIntoViewIfNeeded()
await ac.click()
await page.waitForTimeout(1000)
await page.screenshot({ path: `${OUT}/06_fiche_evenement.png` })

const banner = await page.locator('text=ÉVÉNEMENT').count()
console.log('AC0253 bandeau événement présent :', banner > 0)
console.log('CONSOLE ERRORS:', errors.length ? errors.slice(0, 10) : 'aucune')
await browser.close()
