// COUCHES-RECETTE-1 — captures navigateur réelles (Chrome via Playwright), stack dédié :8055/:5255.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const URL = 'http://localhost:5255/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/recette1/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const VUES = {
  ile:      { center: [55.53, -21.13], zoom: 9.2 },
  stdenis:  { center: [55.448, -20.884], zoom: 12.6 },
  stpaul:   { center: [55.29, -20.99], zoom: 12.4 },
  saintemarie: { center: [55.53, -20.94], zoom: 12.6 },
  leport:   { center: [55.30, -20.94], zoom: 12.4 },
  rue:      { center: [55.4505, -20.8790], zoom: 16.2 },
}
async function attendre(page) {
  await page.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
  const b = page.getByText('Explorer la carte', { exact: false })
  if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
  await sleep(1800)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 60000 }).catch(() => {})
  await sleep(600)
}
async function aller(page, v) {
  await page.evaluate((vv) => window.__labuse_map.jumpTo({ center: vv.center, zoom: vv.zoom }), v)
  await sleep(500)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 40000 }).catch(() => {})
  await sleep(1400)
}
async function montrer(page, kinds) {
  await page.evaluate((ks) => {
    const m = {}; for (const k of ks) m[k] = true
    // Repère léger pour le contexte : les LIMITES COMMUNES (24). PAS limites_parcelles (431 k → le
    // semis fait exploser le transport CDP de Playwright, artefact de harnais connu).
    m['limites_communes'] = true
    window.__labuse.setTuyauActives(m)
  }, kinds)
  await sleep(700)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 40000 }).catch(() => {})
  await sleep(900)
}
async function shot(page, nom) { await page.screenshot({ path: OUT + nom + '.png' }); console.log('  →', nom) }
async function prise(page, kinds, nom, vue) {
  try { await montrer(page, kinds); await aller(page, vue); await shot(page, nom) }
  catch (e) { console.log('  ✗', nom, String(e.message || e).split('\n')[0]) }
}

// tranche : node _recette1.mjs <from> <to>  (from>0 → saute les preuves mandat, ne fait que les couches)
const FROM = parseInt(process.argv[2] || '0', 10)
const TO = parseInt(process.argv[3] || '999', 10)
const browser = await chromium.launch({ channel: 'chrome', headless: true,
  args: ['--window-size=1440,1000', '--disable-logging', '--log-level=3', '--disable-extensions'] })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on('console', () => {}); page.on('pageerror', () => {})
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await attendre(page)
console.log('carte prête (tranche', FROM, '-', TO, ')')

if (FROM === 0) {
// ─── PREUVES MANDAT ───
// 1) panneau (Repères en tête) — crop du panneau gauche (en vue commune : parcelles bornées)
await aller(page, VUES.stpaul)
await page.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
await sleep(1200)
await page.locator('[data-tuyau-section]').screenshot({ path: OUT + 'panneau_reperes.png' }).catch(async () => { await shot(page, 'panneau_reperes_full') })
console.log('  → panneau_reperes')

// 2) légende accordéon, 5 couches actives
await prise(page, ['ppr', 'znieff', 'tcsp', 'sar', 'alea_mvt'], 'legende_accordeon_5', VUES.stpaul)

// 3) ortho + voile + 3 couches
try {
  await montrer(page, ['ppr', 'znieff', 'tcsp'])
  // bascule fond ortho via la barre d'outils
  const bm = page.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first()
  await bm.click().catch(() => {})
  await sleep(400)
  await page.getByText('Ortho IGN', { exact: false }).first().click().catch(() => {})
  await sleep(1800)
  await aller(page, VUES.stpaul)
  await shot(page, 'ortho_voile_3couches')
  // repasser en sombre
  await bm.click().catch(() => {}); await sleep(300)
  await page.getByText('Sombre', { exact: false }).first().click().catch(() => {}); await sleep(800)
} catch (e) { console.log('  ✗ ortho', String(e.message || e).split('\n')[0]) }
} // fin preuves mandat

// ─── PAR COUCHE MODIFIÉE : île + commune ───
const COUCHES = [
  ['limites_communes', VUES.ile, VUES.stdenis],
  ['endiguement', VUES.ile, VUES.leport],
  ['telepherique', VUES.stdenis, VUES.rue],
  ['tcsp', VUES.ile, VUES.stdenis],
  ['sar', VUES.ile, VUES.stpaul],
  ['ppr', VUES.ile, VUES.stpaul],
  ['bruit_route', VUES.ile, VUES.stpaul],
  ['alea_mvt', VUES.ile, VUES.stpaul],
  ['znieff', VUES.ile, VUES.stpaul],
  ['parc_national', VUES.ile, VUES.stpaul],
  ['tri_zone', VUES.ile, VUES.stpaul],
  ['cimetiere', VUES.ile, VUES.stdenis],
  ['sup', VUES.ile, VUES.stpaul],
  ['zonage_parcelle', VUES.stpaul, VUES.rue],
]
const ZONAGE = [['stdenis', VUES.stdenis], ['stpaul', VUES.stpaul], ['saintemarie', VUES.saintemarie]]
let i = 0
for (const [k, vIle, vCom] of COUCHES) {
  if (i >= FROM && i < TO) {
    await prise(page, [k], `couche_${k}_ile`, vIle)
    await prise(page, [k], `couche_${k}_commune`, vCom)
  }
  i++
}
// zonage par parcelle (calibré) sur 3 communes (étiquettes) — indices après COUCHES
for (const [nom, v] of ZONAGE) {
  if (i >= FROM && i < TO) await prise(page, ['zonage_parcelle'], `zonage_parcelle_${nom}`, v)
  i++
}

await browser.close()
console.log('OK captures')
