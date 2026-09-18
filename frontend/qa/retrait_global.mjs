// COUCHES-RETRAIT-1 preuve globale — panneau « Couches » complet (56, 12 familles), le panneau
// « Cartes » V1 n'existe plus, une capture par famille avec une couche active.
// node qa/retrait_global.mjs
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-retrait/global/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
// une couche représentative par famille (kind = data-layer)
const PAR_FAMILLE = [
  ['reperes', 'limites_parcelles'], ['urbanisme', 'zonage_parcelle'], ['risques', 'ppr'],
  ['environnement', 'parc_national'], ['foncier', 'sar'], ['fond_de_plan', 'construction_surfacique'],
  ['marche', 'vefa_neuf'], ['patrimoine', 'cimetiere'], ['reseaux', 'ligne_ht'],
  ['equipements', 'amenite_bpe'], ['transport', 'tcsp'], ['dispositifs', 'zfang'],
]
const V = [55.44, -20.9, 13.2]   // Saint-Denis, échelle commune
const CLIP = { x: 360, y: 60, width: 1080, height: 900 }
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
await sleep(3000)
// ouvrir le panneau « Couches »
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const exp = await toggle.first().getAttribute('aria-expanded'); if (exp !== 'true') await toggle.first().click().catch(() => {}) }
await sleep(1000)
// PREUVE 1 : le panneau complet (nb de couches + absence de l'ancien panneau Cartes V1)
const nbCouches = await p.locator('[data-couches-drawer] [data-layer]').count().catch(() => 0)
// l'ancien panneau V1 exposait des libellés comme « Limites parcelles (contour cadastral) » (LAYERS)
const vieuxLabel = await p.getByText('Limites parcelles (contour cadastral)', { exact: false }).count().catch(() => 0)
await p.locator('[data-couches-drawer]').first().screenshot({ path: OUT + 'panneau_couches.png' }).catch(() => p.screenshot({ path: OUT + 'panneau_couches.png' }))
console.log('PANNEAU: data-layer rows =', nbCouches, '| vieux label V1 présent =', vieuxLabel)
// aller à la vue commune
const jump = async () => { for (let i = 0; i < 6; i++) { await p.evaluate(([lon, lat, z]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: z }), V); await sleep(700); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - V[2]) < 0.3) break } await p.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 30000 }).catch(() => {}); await sleep(1500) }
await jump()
// PREUVE 2 : une capture par famille avec une couche active
for (const [fam, kind] of PAR_FAMILLE) {
  const btn = p.locator(`[data-couches-drawer] [data-layer="${kind}"]`)
  let clicked = false
  if (await btn.count()) { await btn.first().scrollIntoViewIfNeeded().catch(() => {}); await btn.first().click().catch(() => {}); clicked = true }
  await sleep(400)
  await p.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 20000 }).catch(() => {})
  await sleep(1200)
  await p.screenshot({ path: OUT + `famille_${fam}_${kind}.png`, clip: CLIP })
  console.log('  famille', fam, '→', kind, clicked ? 'activée' : 'INTROUVABLE')
  if (clicked && await btn.count()) await btn.first().click().catch(() => {})   // éteindre
  await sleep(300)
}
await br.close()
console.log('OK global')
