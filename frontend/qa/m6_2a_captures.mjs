// M6 Phase 2a — captures de preuve pour le REVIEW PACK (BAN, disclaimer, Sources, ANRU vide).
// Usage : cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/m6_2a_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures-2a'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

// 1. fiche brûlante rang 1 : adresse en tête + disclaimer en pied
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.fill('input[title^="Recherche du dashboard"]', '97423000AB1908')
await page.keyboard.press('Enter')
await page.waitForTimeout(4500)
await page.screenshot({ path: `${OUT}/fiche-adresse-disclaimer.png` })
const adr = await page.locator('[data-fiche-adresse]').first().textContent().catch(() => null)
const disc = await page.locator('[data-disclaimer-cu]').first().textContent().catch(() => null)
console.log('fiche adresse:', adr, '| disclaimer:', disc ? 'OK' : 'ABSENT')

// 2. cartes de résultats avec adresse (mode île, tri rang)
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3500)
const cards = await page.locator('[data-card-adresse]').count()
await page.screenshot({ path: `${OUT}/cartes-adresse.png` })
console.log('cartes avec ligne adresse:', cards)

// 3. page Sources : licences + attributions
await page.goto(BASE + '#sources', { waitUntil: 'networkidle', timeout: 60000 }).catch(() => null)
await page.waitForTimeout(1500)
// fallback : clic rail « Sources » si le hash ne route pas
if (!(await page.locator('[data-source-row]').count())) {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2000)
  await page.locator('button[title*="Sources"], [title="Sources"]').first().click().catch(() => null)
  await page.waitForTimeout(1500)
}
const nAttr = await page.locator('[data-source-attribution]').count()
const nLic = await page.locator('[data-source-licence]').count()
await page.screenshot({ path: `${OUT}/sources-attributions.png` })
console.log('sources: licences affichées', nLic, '· attributions', nAttr)

await browser.close()
