// COUCHES-STYLE-3 — preuves finales (code réel : voile gris #4E5450, opacité active 0.50).
// Sombre + Clair : Repères seuls (pas de voile) vs thématique cochée (voile gris, thématique ressort).
// Zoom élevé pour la thématique (tuiles petites) → évite le message worker géant qui tue le pipe CDP.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const URL = 'http://localhost:5255/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/style3/final/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const V = [55.2735, -21.0095, 15.6]  // St-Paul, quartier avec PPR
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
async function newPage() {
  const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
  p.on('console', () => {}); p.on('pageerror', () => {})
  await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
  const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
  await sleep(3500)
  return p
}
const jump = async (p) => { for (let i = 0; i < 6; i++) { await p.evaluate(([lon, lat, zz]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: zz }), V); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - V[2]) < 0.3) break } await sleep(2600) }
const veil = (p) => p.evaluate(() => { const m = window.__labuse_map; return { color: m.getPaintProperty('couche-veil', 'background-color'), op: m.getPaintProperty('couche-veil', 'background-opacity') } })
const only = (p) => p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
const withPpr = (p) => p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true, ppr: true }))

async function fond(p, prefix, clair) {
  if (clair) {
    const bm = p.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first()
    await bm.click().catch(() => {}); await sleep(400)
    await p.getByText('Clair', { exact: false }).first().click().catch(() => {}); await sleep(1000)
    await bm.click().catch(() => {}); await sleep(500)  // re-clic sur le bouton fond = referme le menu
  }
  await only(p); await jump(p); console.log(prefix, '/ Repères seuls :', await veil(p)); await p.screenshot({ path: OUT + prefix + '_reperes_seuls.png' })
  await withPpr(p); await jump(p); console.log(prefix, '/ PPR cochée    :', await veil(p)); await p.screenshot({ path: OUT + prefix + '_thematique_ppr.png' })
}

const p1 = await newPage(); await fond(p1, 'sombre', false); await p1.close()
const p2 = await newPage(); await fond(p2, 'clair', true); await p2.close()
await br.close()
console.log('OK final')
