// COUCHES-REGISTRE-2 lot 3 — le sens inverse : le détail d'une source liste les couches qu'elle
// alimente, cliquables vers la carte. node qa/registre2_circuit.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-registre2/circuit/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
await sleep(1500)
await p.evaluate(() => window.__labuse.setView('sources'))
await p.waitForSelector('[data-sources-page]', { timeout: 20000 }).catch(() => {})
await p.waitForSelector('[data-source-couche]', { timeout: 20000 }).catch(() => {})  // les couches sont rendues
await sleep(1000)
// la ligne « BD TOPO IGN » = celle qui porte la couche `cimetiere` (source riche, 8 couches)
const row = p.locator('[data-source-row]').filter({ has: p.locator('[data-source-couche="cimetiere"]') }).first()
const hasCouches = await row.count().catch(() => 0)
const couchesTxt = hasCouches ? await row.locator('[data-source-couches]').first().innerText().catch(() => '') : ''
console.log('BD TOPO — couches listées:', hasCouches ? 'OUI' : 'NON', '|', JSON.stringify(couchesTxt).slice(0, 200))
await row.first().scrollIntoViewIfNeeded().catch(() => {})
await sleep(300)
await row.first().screenshot({ path: OUT + 'source_bd_topo_couches.png' }).catch(() => {})
// clic sur une couche (cimetiere) → doit aller à la carte + l'activer
const couche = row.locator('[data-source-couche="cimetiere"]')
if (await couche.count()) {
  await couche.first().click().catch(() => {})
  await sleep(2500)
  const view = await p.evaluate(() => document.querySelector('[data-sources-page]') ? 'sources' : (document.querySelector('.maplibregl-map') ? 'cartes' : '?'))
  const active = await p.evaluate(() => window.__labuse_map && window.__labuse_map.getLayer && !!document.querySelector('[data-couches-drawer]'))
  console.log('clic cimetiere → vue:', view, '| carte affichée:', view === 'cartes')
  await sleep(1000)
  await p.screenshot({ path: OUT + 'clic_vers_couche.png', clip: { x: 300, y: 60, width: 1100, height: 900 } }).catch(() => {})
} else console.log('bouton couche cimetiere introuvable')
await br.close()
console.log('OK registre2_circuit')
