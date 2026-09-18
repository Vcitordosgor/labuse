// COUCHES-REGISTRE-2 lot 2 — capture du « i » enrichi (source · millésime · date de contrôle + prose)
// de 5 couches de familles différentes, dont une « jamais contrôlé ». node qa/registre2_i.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-registre2/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
// (famille, kind) — sup/ppr/bpe/parc ont une date ; limites_communes = jamais contrôlé (seed)
const CIBLES = [
  ['urbanisme', 'sup'], ['risques', 'ppr'], ['equipements', 'amenite_bpe'],
  ['environnement', 'parc_national'], ['reperes', 'limites_communes'],
]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(2500)
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const e = await toggle.first().getAttribute('aria-expanded'); if (e !== 'true') await toggle.first().click().catch(() => {}) }
// attendre que /map/couches-info soit résolu (le bloc source/millésime/date n'apparaît qu'après)
await p.waitForFunction(async () => { try { const r = await fetch('/map/couches-info'); const j = await r.json(); return !!j.sup } catch { return false } }, { timeout: 20000 }).catch(() => {})
await sleep(2500)
for (const [fam, kind] of CIBLES) {
  const row = p.locator(`[data-couches-drawer] [data-layer="${kind}"]`)
  if (!(await row.count().catch(() => 0))) { console.log(`[${kind}] ligne absente`); continue }
  await row.first().scrollIntoViewIfNeeded().catch(() => {})
  await sleep(200)
  const pill = row.first().locator('xpath=..').locator('[aria-label="En savoir plus sur cette couche"]')
  await pill.first().hover().catch(() => {})
  await sleep(500)
  const tip = p.locator('[role="tooltip"]')
  const txt = (await tip.count().catch(() => 0)) ? await tip.first().innerText().catch(() => '') : ''
  const controle = /jamais contrôlé/.test(txt) ? 'JAMAIS' : (/contrôlé le/.test(txt) ? 'DATÉ' : '?')
  console.log(`[${fam}/${kind}] contrôle=${controle} | ${JSON.stringify(txt).slice(0, 200)}`)
  const box = await row.first().locator('xpath=..').boundingBox().catch(() => null)
  if (box) await p.screenshot({ path: OUT + `${kind}_i.png`, clip: { x: Math.max(0, box.x - 30), y: Math.max(0, box.y - 150), width: 400, height: 210 } }).catch(() => {})
  await p.mouse.move(1250, 300); await sleep(150)
}
await br.close()
console.log('OK registre2_i')
