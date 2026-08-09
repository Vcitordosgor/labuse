// M54-EXPO-2 captures. Usage : node qa/m54b_capture.mjs
import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'
const BASE = 'http://127.0.0.1:8000/socle/'
const IDU = '97415000CR0849'
const OUT = new URL('./m54b_captures', import.meta.url).pathname; mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })

async function openFiche(page) {
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
  await page.waitForSelector('[data-omnibox]', { timeout: 15000 })
  await page.fill('[data-omnibox]', IDU)
  await page.click('[aria-label="Lancer la recherche"]')
  await page.waitForSelector('[data-synthese-ia]', { state: 'attached', timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(1200)
}
async function ficheEl(page) { return page.$('aside:has([data-synthese-ia]), aside:has([data-onepager])') }

// 1) Explain — STUB réel (pas de clé API locale)
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await openFiche(page)
  await page.click('[data-synthese-ia]').catch(() => {})
  await page.waitForSelector('[data-synthese-ia-result]', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(600)
  const stub = await page.$eval('[data-synthese-stub]', () => true).catch(() => false)
  console.log('Explain STUB : badge repli présent =', stub)
  const el = await page.$('[data-synthese-ia-result]'); if (el) await el.scrollIntoViewIfNeeded()
  const f = await ficheEl(page); if (f) await f.screenshot({ path: `${OUT}/explain-stub.png` })
  await page.close()
}
// 2) Explain — VALIDÉ (mock route : available=true)
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await page.route(/\/parcels\/.*\/explain/, (r) => r.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ available: true, explanation: 'Parcelle de 528 m² classée « à creuser » : capacité résiduelle modeste, bâti déjà révélé. Le verdict reflète une probabilité de mutation sous la moyenne du parc. Points de vigilance : une servitude et un aléa faible. À qualifier avant tout contact.', model: 'mock' }) }))
  await openFiche(page)
  await page.click('[data-synthese-ia]').catch(() => {})
  await page.waitForSelector('[data-synthese-ia-result]', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(500)
  const stub = await page.$eval('[data-synthese-stub]', () => true).catch(() => false)
  console.log('Explain VALIDÉ : badge repli présent =', stub, '(attendu false)')
  const el = await page.$('[data-synthese-ia-result]'); if (el) await el.scrollIntoViewIfNeeded()
  const f = await ficheEl(page); if (f) await f.screenshot({ path: `${OUT}/explain-valide.png` })
  await page.close()
}
// 3) Dossier tile (statut/quota) — capture de la barre exports
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await openFiche(page)
  const dq = await page.$eval('[data-dossier-quota]', (e) => e.textContent).catch(() => null)
  console.log('Dossier tile quota indicator =', JSON.stringify(dq))
  const el = await page.$('[data-onepager]'); if (el) await el.scrollIntoViewIfNeeded()
  const f = await ficheEl(page); if (f) await f.screenshot({ path: `${OUT}/dossier-statut.png` })
  await page.close()
}
// 4) Shortlist — activer l'analyse (verdict) puis ouvrir le toggle
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
  await page.waitForSelector('[data-omnibox]', { timeout: 15000 })
  await page.fill('[data-omnibox]', 'Saint-Paul'); await page.click('[aria-label="Lancer la recherche"]')
  await page.waitForTimeout(1500)
  const on = await page.$('[data-verdict-on]'); if (on) { await on.click(); await page.waitForTimeout(1500) }
  const tg = await page.$('[data-shortlist-toggle]')
  console.log('Shortlist toggle présent =', !!tg)
  if (tg) { await tg.click(); await page.waitForSelector('[data-shortlist-item]', { timeout: 15000 }).catch(() => {}); await page.waitForTimeout(800) }
  const n = await page.$$eval('[data-shortlist-item]', (els) => els.length).catch(() => 0)
  console.log('Shortlist items =', n)
  await page.screenshot({ path: `${OUT}/shortlist.png` })
  await page.close()
}
await browser.close()
console.log(`📸 ${OUT}/*.png`)
process.exit(0)
