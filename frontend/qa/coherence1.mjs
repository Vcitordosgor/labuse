// COHERENCE-1 — captures des endroits où s'affiche un compte de couches / sources.
// node qa/coherence1.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/coherence1/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1500)
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) { await explore.first().click().catch(() => {}); await sleep(2000) }

// 1) CLIENT — carte : 3 couches actives → la légende du tuyau (aucun compteur « N couches »)
for (const k of ['ppr', 'zonage_parcelle', 'parc_national']) { await p.evaluate((kk) => window.__labuse.toggleTuyau(kk), k); await sleep(500) }
await sleep(1500)
await p.screenshot({ path: OUT + 'client_map_legend.png', clip: { x: 360, y: 60, width: 1080, height: 900 } })
console.log('client_map_legend OK')

// 2) CLIENT — page Sources (94 sources · Toutes 94 · compteurs par catégorie)
await p.locator('[data-rail="sources"]').first().click().catch(() => {})
await p.waitForSelector('[data-source-row]', { timeout: 30000 }).catch(() => {})
await sleep(1200)
await p.screenshot({ path: OUT + 'client_sources.png' })
console.log('client_sources OK, rows =', await p.locator('[data-source-row]').count())

// 3) ADMIN — Données / Circuit : Résumé (KPI 60/94 réservoirs, reste 94)
await p.locator('[data-rail-admin]').first().click().catch(() => {})
await sleep(2000)
await p.locator('[data-admin-section="donnees"]').first().click().catch(() => {})
await p.waitForFunction(() => !document.body.innerText.includes('Circuit — chargement'), { timeout: 30000 }).catch(() => {})
await sleep(1500)
await p.screenshot({ path: OUT + 'admin_resume.png' })
console.log('admin_resume OK')

// 4) ADMIN — compteur (clic KPI) : 94 réservoirs + « La carte » (BD TOPO = kinds spatial_layers)
const kpi = p.locator('.kpi.lien').first()
if (await kpi.count()) { await kpi.click().catch(() => {}) }
// attendre le contenu du compteur (pas « Chargement… »)
await p.waitForFunction(() => /à jour et vérifiés/.test(document.body.innerText), { timeout: 20000 }).catch(() => console.log('compteur load timeout'))
await sleep(1200)
await p.screenshot({ path: OUT + 'admin_compteur_top.png' })   // haut : « 94 réservoirs »
// bas : la section « La carte » (libellé précisé) + ligne BD TOPO (11 kinds spatial_layers)
const carte = p.getByRole('heading', { name: /La carte : chaque réservoir/ })
if (await carte.count()) { await carte.first().scrollIntoViewIfNeeded().catch(() => {}); await sleep(800) }
await p.screenshot({ path: OUT + 'admin_compteur_carte.png' })
console.log('admin_compteur_carte OK')

// 5) ADMIN — fiche réservoir BD TOPO (Couches carte alimentées · 8) via deep-link
await p.evaluate(() => { window.location.hash = 'admin=1&cx=reservoir:17'; window.dispatchEvent(new HashChangeEvent('hashchange')) })
await p.waitForFunction(() => /BD TOPO IGN/.test(document.body.innerText) && !document.body.innerText.includes('Chargement…'), { timeout: 20000 }).catch(() => {})
await sleep(1500)
const cch = p.getByRole('heading', { name: /Couches carte alimentées/ })
if (await cch.count()) { await cch.first().scrollIntoViewIfNeeded().catch(() => {}); await sleep(600) }
await p.screenshot({ path: OUT + 'admin_reservoir_bdtopo.png' })
console.log('admin_reservoir_bdtopo OK')

await br.close()
console.log('DONE')
