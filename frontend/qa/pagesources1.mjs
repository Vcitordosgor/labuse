// PAGE-SOURCES-1 — captures avant/après : page Sources cliente + « i » d'une couche.
// node qa/pagesources1.mjs avant|apres
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const LABEL = process.argv[2] === 'apres' ? 'apres' : 'avant'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/pages-sources/${LABEL}/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1800)
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) { await explore.first().click().catch(() => {}); await sleep(1500) }

// 1) le « i » d'une couche (parc_national) — source · [millésime] · prose
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const e = await toggle.first().getAttribute('aria-expanded'); if (e !== 'true') await toggle.first().click().catch(() => {}) }
await sleep(1000)
await p.waitForResponse((r) => r.url().includes('/map/couches-info') && r.ok(), { timeout: 20000 }).catch(() => {})
await sleep(1500)
const row = p.locator('[data-couches-drawer] [data-layer="parc_national"]')
if (await row.count()) {
  await row.first().scrollIntoViewIfNeeded().catch(() => {})
  const pill = row.first().locator('xpath=..').locator('[aria-label="En savoir plus sur cette couche"]')
  if (await pill.count()) { await pill.first().hover().catch(() => {}); await sleep(1000) }
  await p.screenshot({ path: OUT + 'i_couche.png', clip: { x: 70, y: 60, width: 620, height: 700 } })
  console.log('i_couche OK')
} else console.log('  parc_national INTROUVABLE')

// 2) page Sources cliente (pleine page + haut de page)
await p.locator('[data-rail="sources"]').first().click().catch(() => {})
await p.waitForSelector('[data-source-row]', { timeout: 30000 }).catch(() => console.log('sources rows timeout'))
await sleep(1200)
await p.screenshot({ path: OUT + 'sources.png' })
// zoom sur l'en-tête (titre + intro + bandeau + réserve) pour juger l'alignement
await p.screenshot({ path: OUT + 'sources_entete.png', clip: { x: 60, y: 60, width: 1320, height: 620 } })
console.log('sources OK, rows =', await p.locator('[data-source-row]').count())

await br.close()
console.log('DONE', LABEL)
