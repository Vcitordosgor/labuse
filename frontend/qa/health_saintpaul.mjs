// DIAGNOSTIC ciblé : Saint-Paul + Brûlantes v2 — la liste est-elle vraiment vide ?
// (DB dit 27 brûlantes v2 à Saint-Paul, île=117). LECTURE SEULE, :8010.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/health-check-post-m6/captures'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })

await page.goto(BASE + '#v=1&c=' + encodeURIComponent('Saint-Paul'), { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await page.waitForTimeout(5000)

// AVANT filtre : combien de cartes (toutes tiers) à Saint-Paul ?
const cartesAvant = await page.locator('[data-results-scroll] button').count()
const videAvant = await page.locator('[data-liste-vide]').count()
console.log(`Saint-Paul (sans filtre tier) : cartes=${cartesAvant} listeVide=${videAvant}`)

// cliquer la chip Brûlantes v2
await page.locator('button', { hasText: 'Brûlantes v2' }).first().click()
await page.waitForTimeout(5000)
const chipTxt = ((await page.locator('button', { hasText: 'Brûlantes v2' }).first().textContent()) ?? '').replace(/\s+/g, ' ').trim()
const cartesApres = await page.locator('[data-results-scroll] button').count()
const videApres = await page.locator('[data-liste-vide]').count()
const videTxt = videApres ? ((await page.locator('[data-liste-vide]').textContent()) ?? '').replace(/\s+/g, ' ').trim() : ''
// carte réelle = data-result-card ? sinon compter celles portant un IDU-like
const cardTexts = []
for (let i = 0; i < cartesApres; i++) cardTexts.push(((await page.locator('[data-results-scroll] button').nth(i).textContent()) ?? '').replace(/\s+/g, ' ').trim().slice(0, 50))
// features brûlantes rendues sur la carte (filtre MapLibre côté client)
await page.waitForTimeout(2000)
const mapFeats = await page.evaluate(() => {
  const m = window.__labuse_map
  try {
    const fs = m.querySourceFeatures('parcels')
    const brul = fs.filter((f) => f.properties?.tier_v2 === 'brulante' && Number(f.properties?.etage0 ?? 0) < 1)
    return { total_source: fs.length, brulantes_dans_source: brul.length }
  } catch (e) { return { err: String(e) } }
})
console.log(`\nSaint-Paul + Brûlantes v2 :`)
console.log(`  chip="${chipTxt}"`)
console.log(`  cartes liste=${cartesApres} | listeVide=${videApres} "${videTxt}"`)
console.log(`  textes cartes: ${JSON.stringify(cardTexts)}`)
console.log(`  carte MapLibre source Saint-Paul: ${JSON.stringify(mapFeats)}`)
await page.screenshot({ path: `${OUT}/DIAG-saintpaul-brulantes.png` })
console.log('\nerreurs console:', errs.length); errs.slice(0, 5).forEach((e) => console.log('  ·', e))
await browser.close()
