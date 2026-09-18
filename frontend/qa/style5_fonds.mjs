// COUCHES-STYLE-5 — parcelles du tuyau lisibles par fond. node qa/style5_fonds.mjs <avant|apres>
// 6 captures même viewport/zoom (Sombre/Ortho/Clair) + 1 Ortho zoom élevé (contour se renforce).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'apres'
const URL = 'http://localhost:5255/socle/'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/style5/${PHASE}/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const CENTER = [55.2735, -21.0095]
const Z = 16.2
const ZHAUT = 18.2
const OCEAN = [55.20, -21.02, 11.5]   // vue large, océan à gauche (côte ouest) pour fermer le menu
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(3500)
const jump = async (lon, lat, zz) => { for (let i = 0; i < 6; i++) { await p.evaluate(([a, b, c]) => window.__labuse_map.jumpTo({ center: [a, b], zoom: c }), [lon, lat, zz]); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - zz) < 0.3) break } await sleep(2200) }
const onlyReperes = () => p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
const layerInfo = () => p.evaluate((id) => { const m = window.__labuse_map; const l = m.getLayer(id); if (!l) return 'ABSENT'; const j = (v) => (typeof v === 'object' ? JSON.stringify(v) : v); return { color: j(m.getPaintProperty(id, 'line-color')), width: j(m.getPaintProperty(id, 'line-width')), opacity: j(m.getPaintProperty(id, 'line-opacity')) } }, 'tuyau-limites_parcelles-outline')
async function setFond(optLabel) {
  await jump(...OCEAN)                                   // au large : océan visible pour fermer le menu
  const bm = p.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first()
  await bm.click().catch(() => {}); await sleep(400)
  await p.getByText(optLabel, { exact: true }).first().click().catch(() => {}); await sleep(1000)
  await p.mouse.click(180, 320); await sleep(200)        // clic océan (haut-gauche à z11,5) = ferme le menu
  await p.mouse.move(720, 500); await sleep(300)
}
async function shot(fond, lon, lat, zz, tag) {
  await onlyReperes(); await jump(lon, lat, zz)
  console.log(`${PHASE} / ${fond}${tag || ''} — parcelles:`, JSON.stringify(await layerInfo()))
  await p.screenshot({ path: OUT + fond + (tag || '') + '.png' })
}

await onlyReperes()
await shot('sombre', ...CENTER, Z)                       // fond défaut = Sombre
await setFond('Ortho IGN'); await shot('ortho', ...CENTER, Z); await shot('ortho', ...CENTER, ZHAUT, '_zoom')
await setFond('Clair'); await shot('clair', ...CENTER, Z)
await br.close()
console.log('OK', PHASE)
