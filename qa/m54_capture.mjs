// M54-EXPO — capture des boutons branchés. Usage : IDU=... TAG=integral node qa/m54_capture.mjs
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'
const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const IDU = process.env.IDU || '97415000CR0849'
const TAG = process.env.TAG || 'run'
const OUT = new URL('./m54_captures', import.meta.url).pathname; mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
await page.waitForSelector('[data-omnibox]', { timeout: 15000 })
await page.fill('[data-omnibox]', IDU)
await page.click('[aria-label="Lancer la recherche"]')
await page.waitForSelector('[data-onepager]', { state: 'attached', timeout: 20000 }).catch(() => {})
await page.waitForTimeout(1500)
const present = await page.evaluate(() => {
  const q = (s) => !!document.querySelector(s)
  return {
    onepager: q('[data-onepager]'), spf: q('[data-spf-letter]'), feedback: q('[data-feedback]'),
    predossier_enabled: q('[data-predossier]'), predossier_gated: q('[data-predossier-gate]'),
  }
})
console.log(`[${TAG}] boutons présents :`, JSON.stringify(present))
const fiche = await page.$('aside:has([data-onepager])')
// exports : scroller la rangée documents en vue, capture de la fiche
const el = await page.$('[data-onepager]')
if (el) await el.scrollIntoViewIfNeeded()
await page.waitForTimeout(400)
if (fiche) await fiche.screenshot({ path: `${OUT}/fiche-exports-${TAG}.png` })
// SPF : ouvrir le tiroir Propriétaire (fermé par défaut) puis capturer
const proprio = await page.$('[data-drawer="proprio"] button')
if (proprio) { await proprio.click(); await page.waitForTimeout(500) }
const spf = await page.$('[data-spf-letter]')
console.log(`[${TAG}] spf après ouverture tiroir proprio :`, !!spf)
if (spf && fiche) { await spf.scrollIntoViewIfNeeded(); await page.waitForTimeout(300); await fiche.screenshot({ path: `${OUT}/fiche-spf-${TAG}.png` }) }
// feedback : scroller la bande retour
const fb = await page.$('[data-feedback]')
if (fb && fiche) { await fb.scrollIntoViewIfNeeded(); await page.waitForTimeout(300); await fiche.screenshot({ path: `${OUT}/fiche-feedback-${TAG}.png` }) }
console.log(`📸 ${OUT}/fiche-*-${TAG}.png`)
await browser.close(); process.exit(0)
