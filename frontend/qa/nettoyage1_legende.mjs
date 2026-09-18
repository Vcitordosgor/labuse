// NETTOYAGE-1 lot 1 — capture de la légende V1 VIVANTE (outil Permis + mode analyse).
// node qa/nettoyage1_legende.mjs avant|apres
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const LABEL = process.argv[2] === 'apres' ? 'apres' : 'avant'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/nettoyage1/${LABEL}/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
const ex = p.getByText('Explorer la carte', { exact: false })
if (await ex.count().catch(() => 0)) { await ex.first().click().catch(() => {}); await sleep(2000) }

// ── PERMIS : la légende V1 rend « Permis (par état) » ──
await p.evaluate(() => window.__labuse.setModule('permis'))
await sleep(2500)
// déplier la légende
const tog = p.locator('[data-legend-toggle]')
if (await tog.count()) { const e = await tog.first().getAttribute('aria-expanded'); if (e !== 'true') await tog.first().click().catch(() => {}) }
await sleep(800)
const headerTxt = await p.locator('[data-legend] [data-legend-toggle] .label-caps').first().textContent().catch(() => null)
console.log('PERMIS legend header:', JSON.stringify(headerTxt))
const leg = p.locator('[data-legend]').first()
if (await leg.count()) await leg.screenshot({ path: OUT + 'legende_permis.png' }).catch(() => {})
console.log('legende_permis OK')

await br.close()
console.log('DONE', LABEL)
