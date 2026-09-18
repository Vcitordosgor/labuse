// FICHE-COUCHES-4 lot 2 — captures cimetiere/vefa_neuf/piscine. node qa/fiche_couches4_lot2.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/fiche-couches4/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const CLIP = { x: 1010, y: 0, width: 430, height: 1000 }
const CASES = [
  { kind: 'cimetiere', idu: '97413000CM0130', drawer: 'Risques et protections', needle: 'Cimetière à' },
  { kind: 'vefa_neuf', idu: '97415000AB0001', drawer: 'Marché et secteur', needle: 'logement neuf (VEFA)' },
  { kind: 'piscine_cosia', idu: '97423000AB0198', drawer: 'Dispositifs territoriaux', needle: 'Piscine détectée' },
]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
for (const c of CASES) {
  let done = false
  for (let attempt = 0; attempt < 5 && !done; attempt++) {
    const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
    p.on('console', () => {}); p.on('pageerror', () => {})
    await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForFunction(() => !!window.__labuse && !!window.__labuse_map, { timeout: 60000 })
    const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
    await sleep(2500); await p.evaluate((i) => window.__labuse.select(i), c.idu)
    await p.waitForFunction((i) => { const bx = document.querySelector('.fiche-v6'); return bx && bx.textContent.includes(i) && /couches? évaluées?/.test(bx.textContent) }, c.idu, { timeout: 30000 }).catch(() => {})
    await sleep(2000)
    await p.getByText(c.drawer, { exact: false }).first().click({ timeout: 4000 }).catch(() => {})
    await sleep(1600)
    const vis = await p.evaluate((n) => { const bx = document.querySelector('.fiche-v6'); if (!bx || !bx.textContent.includes(n)) return false; const el = [...bx.querySelectorAll('*')].find((e) => (e.textContent || '').includes(n) && e.querySelectorAll('*').length < 5); if (el) el.scrollIntoView({ block: 'center' }); return true }, c.needle)
    if (vis) { await sleep(500); await p.screenshot({ path: OUT + `lot2_${c.kind}.png`, clip: CLIP }); console.log(c.kind, 'CAPTURED attempt', attempt); done = true }
    else console.log(c.kind, 'attempt', attempt, 'not visible')
    await p.close()
  }
}
await br.close()
