import { chromium } from '../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'
const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = new URL('./m54c_captures', import.meta.url).pathname; mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true })

// 1) Veilles : régler la commune puis ouvrir le panneau
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } })
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
  await page.waitForSelector('[data-omnibox]', { timeout: 15000 })
  await page.fill('[data-omnibox]', 'Saint-Paul'); await page.click('[aria-label="Lancer la recherche"]')
  await page.waitForTimeout(1500)
  await page.click('[data-rail-veilles]')
  await page.waitForSelector('[data-veilles-panel]', { timeout: 10000 })
  await page.waitForTimeout(1200)
  const zones = await page.$$eval('[data-veille-zone]', (e) => e.length).catch(() => 0)
  const alertes = await page.$$eval('[data-alerte]', (e) => e.length).catch(() => 0)
  console.log('Veilles : zones =', zones, ' alertes =', alertes)
  await page.screenshot({ path: `${OUT}/veilles.png` })
  await page.close()
}
// 2) Compare : injecter 3 IDU puis capturer
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 950 } })
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
  await page.waitForSelector('[data-omnibox]', { timeout: 15000 })
  const idus = ['97415000AB0001', '97415000AB0002', '97415000AB0003']
  console.log('Compare IDUs =', idus.join(', '))
  for (const idu of idus) {
    await page.fill('[data-omnibox]', idu); await page.click('[aria-label="Lancer la recherche"]')
    await page.waitForSelector('[data-compare-add]', { timeout: 15000 }).catch(() => {})
    await page.waitForTimeout(700)
    await page.click('[data-compare-add]').catch(() => {})
    await page.waitForTimeout(400)
    // fermer le panneau compare pour rouvrir une autre fiche proprement
    await page.evaluate(() => { const b = document.querySelector('[data-compare-panel] [aria-label="Fermer"]'); if (b) b.click() })
    await page.waitForTimeout(300)
  }
  // rouvrir le comparateur : re-cliquer Comparer sur la dernière fiche
  await page.click('[data-compare-add]').catch(() => {})
  await page.waitForSelector('[data-compare-panel]', { timeout: 10000 }).catch(() => {})
  await page.waitForTimeout(1200)
  const cols = await page.$$eval('[data-compare-col]', (e) => e.length).catch(() => 0)
  console.log('Compare colonnes =', cols)
  await page.screenshot({ path: `${OUT}/compare.png` })
  await page.close()
}
await browser.close()
console.log(`📸 ${OUT}/*.png`)
process.exit(0)
