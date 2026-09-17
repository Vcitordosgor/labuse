// COUCHES-RECETTE-2 — captures navigateur réelles (Chrome/Playwright), stack :8055/:5255.
// Tranches : node recette2_couches.mjs <groupe>  (groupe = A|B|C|D|all).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const URL = 'http://localhost:5255/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/recette2/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const V = {
  ile: [55.53, -21.13, 9.2], stpaul: [55.29, -20.99, 12.4], stdenis: [55.448, -20.884, 12.6],
  rueSD: [55.462, -20.905, 16.4], tele: [55.4388, -20.8883, 14.6], stpierre: [55.478, -21.34, 12.4],
}
const groupe = process.argv[2] || 'all'
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000', '--disable-logging', '--log-level=3'] })
async function page() {
  const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
  p.on('console', () => {}); p.on('pageerror', () => {})
  await p.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
  const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
  await sleep(3500)
  return p
}
async function show(p, kinds) { await p.evaluate((ks) => { const m = {}; for (const k of ks) m[k] = true; m.limites_communes = true; window.__labuse.setTuyauActives(m) }, kinds); await sleep(700) }
async function go(p, v) { let z = 0; for (let i = 0; i < 6 && Math.abs(z - v[2]) > 0.3; i++) { await p.evaluate(([lon, lat, zz]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: zz }), v); await sleep(1000); z = await p.evaluate(() => window.__labuse_map.getZoom()) } await p.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 40000 }).catch(() => {}); await sleep(2200) }
async function shot(p, n) { await p.screenshot({ path: OUT + n + '.png' }); console.log('  →', n) }

if (groupe === 'A' || groupe === 'all') {
  const p = await page()
  await show(p, ['piscine_cosia']); await go(p, V.rueSD); await shot(p, 'A_piscines_1dot')
  await show(p, ['sis', 'casias']); await go(p, V.stpaul); await shot(p, 'A_casias_sis')
  await show(p, ['tcsp']); await go(p, V.stdenis); await shot(p, 'A_tcsp_stations')
  await p.close()
}
if (groupe === 'B' || groupe === 'all') {
  const p = await page()
  // panneau (un seul en-tête, DA partagée) — crop du panneau gauche
  await go(p, V.stpaul)
  await p.screenshot({ path: OUT + 'B_panneau_da.png', clip: { x: 0, y: 0, width: 340, height: 1000 } }); console.log('  → B_panneau_da')
  // légende 5 couches
  await show(p, ['ppr', 'znieff', 'sar', 'tcsp', 'dpu']); await go(p, V.stpaul); await shot(p, 'B_legende_5')
  // message zoom (zonage parcelle en île)
  await show(p, ['zonage_parcelle']); await go(p, V.ile); await shot(p, 'B_zoom_hint')
  await p.close()
}
if (groupe === 'C' || groupe === 'all') {
  const p = await page()
  // voile inactif (que Repères) vs actif (une couche)
  await p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
  await go(p, V.stpaul); await shot(p, 'C_voile_inactif')
  await show(p, ['ppr']); await go(p, V.stpaul); await shot(p, 'C_voile_actif')
  // clic commune (attenuation) — sélectionne St-Denis via le store
  await p.evaluate(() => window.__labuse.setCommune('Saint-Denis')); await sleep(1500); await go(p, V.stdenis); await shot(p, 'C_clic_commune')
  await p.evaluate(() => window.__labuse.setCommune(null)); await sleep(500)
  // fond clair + 2 couches
  await show(p, ['ppr', 'znieff'])
  const bm = p.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first(); await bm.click().catch(() => {}); await sleep(400)
  await p.getByText('Clair', { exact: false }).first().click().catch(() => {}); await sleep(1200)
  await p.mouse.click(900, 500); await sleep(300); await go(p, V.stpaul); await shot(p, 'C_clair_2couches')
  await p.close()
}
if (groupe === 'D' || groupe === 'all') {
  const p = await page()
  await show(p, ['dpu']); await go(p, V.stdenis); await shot(p, 'D_dpu')
  await show(p, ['friche']); await go(p, V.stpaul); await shot(p, 'D_friches')
  await show(p, ['sup']); await go(p, V.ile); await shot(p, 'D_sup_ile')
  await show(p, ['sup']); await go(p, V.stdenis); await shot(p, 'D_sup_commune')
  await show(p, ['telepherique']); await go(p, V.tele); await shot(p, 'D_telepherique_payanke')
  await show(p, ['amenite_bpe']); await go(p, V.stdenis); await shot(p, 'D_bpe_labels')
  await p.close()
}
await br.close()
console.log('OK', groupe)
