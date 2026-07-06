// Capture + vérification des filtres du Socle V1 (revue Vic). Vérifie aussi console/page.
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

const cards = () => page.locator('.overflow-y-auto > button').count()
const counter = () => page.locator('text=chaudes').first().innerText()

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForSelector('text=chaudes', { timeout: 15000 })
await page.waitForTimeout(4000)
await page.screenshot({ path: `${OUT}/01_dashboard.png` })
console.log('DÉFAUT  :', await cards(), 'cartes ·', await counter())

// Filtre statut « Chaude » (panneau gauche) → doit filtrer carte + liste
await page.getByRole('button', { name: /^Chaude/ }).first().click()
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/02_filtre_chaude.png` })
console.log('CHAUDE  :', await cards(), 'cartes')

// + Filtre → Q ≥ 90 (chip omnibox apparaît, compteurs baissent)
await page.getByRole('button', { name: '+ Filtre' }).click()
await page.waitForTimeout(300)
await page.getByPlaceholder('ex. 70').fill('90')
await page.waitForTimeout(300)
await page.keyboard.press('Escape').catch(() => {})
await page.mouse.click(700, 500)
await page.waitForTimeout(1000)
await page.screenshot({ path: `${OUT}/03_filtre_score.png` })
console.log('Q>=90   :', await cards(), 'cartes ·', await counter())

// Retirer le chip « Chaude » via ×
const chip = page.locator('span', { hasText: 'Chaude' }).locator('button[title="Retirer"]').first()
await chip.click().catch(() => {})
await page.waitForTimeout(1000)
console.log('SANS STATUT (Q>=90 restant) :', await cards(), 'cartes ·', await counter())

console.log('CONSOLE ERRORS:', errors.length ? errors.slice(0, 10) : 'aucune')
await browser.close()
