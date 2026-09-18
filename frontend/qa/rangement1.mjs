// PAGES-RANGEMENT-1 — captures avant/après. Usage : node qa/rangement1.mjs avant|apres
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const LABEL = process.argv[2] === 'apres' ? 'apres' : 'avant'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/pages-rangement/${LABEL}/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1800)

// 1) LeftPanel — l'accueil (ligne de fraîcheur), AVANT tout clic « Explorer »
const accueil = p.locator('[data-accueil]')
if (await accueil.count()) await accueil.first().screenshot({ path: OUT + 'leftpanel.png' }).catch(() => {})
else await p.screenshot({ path: OUT + 'leftpanel.png', clip: { x: 70, y: 100, width: 340, height: 820 } })
console.log('leftpanel OK')

// entrer dans la carte
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) { await explore.first().click().catch(() => {}); await sleep(2500) }

// 2) le « i » d'une couche (parc_national : source · millésime · [contrôle])
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const e = await toggle.first().getAttribute('aria-expanded'); if (e !== 'true') await toggle.first().click().catch(() => {}) }
await sleep(1000)
// s'assurer que /map/couches-info a répondu (le bloc source·millésime vient de là, async)
await p.waitForResponse((r) => r.url().includes('/map/couches-info') && r.ok(), { timeout: 20000 }).catch(() => {})
await sleep(1500)
const row = p.locator('[data-couches-drawer] [data-layer="parc_national"]')
if (await row.count()) {
  await row.first().scrollIntoViewIfNeeded().catch(() => {})
  const pill = row.first().locator('xpath=..').locator('[aria-label="En savoir plus sur cette couche"]')
  if (await pill.count()) { await pill.first().hover().catch(() => {}); await sleep(1000) }
  await p.screenshot({ path: OUT + 'i_couche.png', clip: { x: 70, y: 60, width: 620, height: 700 } })
  console.log('i_couche OK')
} else console.log('  parc_national INTROUVABLE dans le drawer')

// 3) page Sources cliente
await p.locator('[data-rail="sources"]').first().click().catch(() => {})
await p.waitForSelector('[data-source-row]', { timeout: 30000 }).catch(() => console.log('sources rows timeout'))
await sleep(1200)
await p.screenshot({ path: OUT + 'sources.png' })
console.log('sources OK, rows =', await p.locator('[data-source-row]').count())

// 4) Copilote (surface + bloc livrable/journal si présent — inchangé, conservé)
await p.locator('[data-rail="copilote"]').first().click().catch(() => {})
await sleep(2000)
await p.screenshot({ path: OUT + 'copilote.png' })
console.log('copilote OK')

// 5) fiche du réservoir « BD TOPO IGN » (id 17) dans Données → pastilles de couches
await p.locator('[data-rail-admin]').first().click().catch(() => {})
await sleep(2000)
await p.locator('[data-admin-section="donnees"]').first().click().catch(() => {})
await sleep(1500)
await p.evaluate(() => { window.location.hash = 'admin=1&cx=reservoir:17'; window.dispatchEvent(new HashChangeEvent('hashchange')) })
await p.waitForFunction(() => /BD TOPO IGN/.test(document.body.innerText) && !document.body.innerText.includes('Chargement…'), { timeout: 20000 }).catch(() => console.log('reservoir load timeout'))
await sleep(1500)
// APRÈS : la carte « Couches carte alimentées » est en bas de la colonne droite → l'amener à l'écran.
const cch = p.getByRole('heading', { name: /Couches carte alimentées/ })
if (await cch.count()) { await cch.first().scrollIntoViewIfNeeded().catch(() => {}); await sleep(600) }
await p.screenshot({ path: OUT + 'reservoir_bdtopo.png' })
console.log('reservoir OK')

await br.close()
console.log('DONE', LABEL)
