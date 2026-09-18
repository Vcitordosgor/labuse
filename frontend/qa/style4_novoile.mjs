// COUCHES-STYLE-4 — preuve du RETRAIT du voile : couche-veil n'existe plus, et le fond avec une
// couche thématique cochée est IDENTIQUE au fond Repères seuls (aucun gris). Stack :8055/:5255.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const URL = 'http://localhost:5255/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/style4/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const V = [55.2735, -21.0095, 15.6]  // St-Paul, quartier avec PPR ; zoom élevé = tuiles petites
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(3500)
const jump = async () => { for (let i = 0; i < 6; i++) { await p.evaluate(([lon, lat, zz]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: zz }), V); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - V[2]) < 0.3) break } await sleep(2600) }
const veilExists = () => p.evaluate(() => !!window.__labuse_map.getLayer('couche-veil'))
const only = () => p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
const withPpr = () => p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true, ppr: true }))

await only(); await jump()
console.log('Repères seuls  — couche-veil existe ?', await veilExists())
await p.screenshot({ path: OUT + 'sombre_reperes_seuls.png' })
await withPpr(); await jump()
console.log('PPR cochée     — couche-veil existe ?', await veilExists())
await p.screenshot({ path: OUT + 'sombre_thematique_ppr.png' })

await br.close()
console.log('OK style4')
