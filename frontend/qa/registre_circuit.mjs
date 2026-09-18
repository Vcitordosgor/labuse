// COUCHES-REGISTRE-1 — capture de la page Circuit/Sources (check 4 : la page de détail du
// réservoir liste-t-elle la couche parmi ses robinets ?). node qa/registre_circuit.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-registre/circuit/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
await sleep(1500)
// aller sur la vue Sources (le Circuit)
await p.evaluate(() => window.__labuse.setView('sources'))
await sleep(2500)
await p.waitForSelector('[data-sources-page]', { timeout: 20000 }).catch(() => {})
await p.screenshot({ path: OUT + 'circuit_page.png' })
// deux sources témoins : SUP et OCS GE — capturer la LIGNE de détail (métadonnées)
for (const [needle, tag] of [['SUP', 'sup'], ['OCS GE', 'ocsge'], ['Forêts publiques', 'foret']]) {
  const search = p.locator('[data-sources-search]')
  if (await search.count()) { await search.first().fill(''); await search.first().fill(needle); await sleep(1200) }
  const row = p.locator('[data-source-row]').first()
  if (await row.count()) {
    // le détail liste-t-il des couches/robinets ? on capture la ligne complète
    const txt = await row.innerText().catch(() => '')
    const listeCouches = /couche|robinet|alimente/i.test(txt)
    console.log(`[${tag}] "${needle}" ligne présente | mentionne couches/robinets:`, listeCouches)
    await row.screenshot({ path: OUT + `source_${tag}.png` }).catch(() => {})
  } else {
    console.log(`[${tag}] "${needle}" INTROUVABLE`)
  }
}
await br.close()
console.log('OK circuit')
