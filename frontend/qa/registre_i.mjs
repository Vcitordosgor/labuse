// COUCHES-REGISTRE-1 — capture du « i » de chaque couche du tuyau (56). node qa/registre_i.mjs
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-registre/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
await sleep(2500)
// la liste des kinds depuis le plan
const kinds = await p.evaluate(async () => {
  const r = await fetch('/map/tuyau/couches'); const d = await r.json()
  return d.couches.map((c) => ({ kind: c.kind, famille: c.famille, extrus: c.geometrie === 'extrusion', groupe: c.groupe || null }))
})
// ouvrir « Couches »
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const e = await toggle.first().getAttribute('aria-expanded'); if (e !== 'true') await toggle.first().click().catch(() => {}) }
await sleep(1000)
const log = []
for (const { kind, famille, extrus, groupe } of kinds) {
  const row = p.locator(`[data-couches-drawer] [data-layer="${kind}"]`)
  const present = await row.count().catch(() => 0)
  if (!present) { log.push({ kind, famille, panel: false, raison: extrus ? 'hors panneau (bâti 3D)' : (groupe ? `fusionné (${groupe})` : 'absent du panneau'), i: '' }); continue }
  await row.first().scrollIntoViewIfNeeded().catch(() => {})
  await sleep(150)
  // le « i » = pastille sœur dans la même ligne (le div parent du bouton data-layer)
  const pill = row.first().locator('xpath=..').locator('[aria-label="En savoir plus sur cette couche"]')
  const hasPill = await pill.count().catch(() => 0)
  if (!hasPill) { log.push({ kind, famille, panel: true, raison: 'pas de pastille i', i: '' }); continue }
  await pill.first().hover().catch(() => {})
  await sleep(400)
  const tip = p.locator('[role="tooltip"]')
  const txt = (await tip.count().catch(() => 0)) ? await tip.first().innerText().catch(() => '') : ''
  // capture : la ligne + son tooltip (zone autour)
  const box = await row.first().locator('xpath=..').boundingBox().catch(() => null)
  if (box) await p.screenshot({ path: OUT + `${kind}_i.png`, clip: { x: Math.max(0, box.x - 20), y: Math.max(0, box.y - 120), width: 380, height: 180 } }).catch(() => {})
  else await pill.first().screenshot({ path: OUT + `${kind}_i.png` }).catch(() => {})
  const src = /source|IGN|DEAL|INSEE|OSM|Géorisques|GPU|INPN|Cerema|EDF|BD TOPO|ONF|ANCT|DGAC|CoSIA|GTFS|Légifrance|Carmen|ODS|Région/i.test(txt)
  const mill = /millésime|\b(19|20)\d\d\b/i.test(txt)
  const ctrl = /dernier contrôle|dernier controle|vérifié le|contrôlé le/i.test(txt)
  log.push({ kind, famille, panel: true, i: txt.replace(/\n/g, ' ¶ ').slice(0, 220), montre_source: src, montre_millesime: mill, montre_date_controle: ctrl })
  // dé-hover
  await p.mouse.move(1200, 300); await sleep(120)
}
writeFileSync(OUT + '_i_log.json', JSON.stringify(log, null, 1))
const ok = log.filter((l) => l.panel && l.montre_source && l.montre_millesime && l.montre_date_controle).length
console.log('captures i:', log.filter((l) => l.panel).length, '| absents panneau:', log.filter((l) => !l.panel).map((l) => l.kind).join(','))
console.log('« i » complets (source+millésime+date contrôle):', ok, '/56')
console.log('montrent source:', log.filter((l) => l.montre_source).length, '| millésime:', log.filter((l) => l.montre_millesime).length, '| date contrôle:', log.filter((l) => l.montre_date_controle).length)
await br.close()
console.log('OK registre_i')
