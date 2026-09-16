// COUCHES-TUYAU-1 — captures navigateur (Chrome installé, canal 'chrome' de Playwright).
// Preuve : le tuyau rend chaque couche (île / commune / rue) ; parité ancienne (GeoJSON, toggles
// du panneau « Couches ») ↔ nouvelle (tuyau) côte à côte ; Le Port en vue commune (rien en mer) ;
// temps d'affichage réel de SUP en vue île.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const APP_URL = process.env.URL || 'http://localhost:5247/socle/'
const OUT = new URL('../captures/', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const VUES = {
  ile:     { center: [55.53, -21.13], zoom: 9.4 },
  stpaul:  { center: [55.29, -20.99], zoom: 12.4 },
  leport:  { center: [55.30, -20.94], zoom: 12.4 },
  rue:     { center: [55.4505, -20.8790], zoom: 16.2 },
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function attendreCarte(page) {
  await page.waitForFunction(() => !!window.__labuse_map, { timeout: 60000 })
  const btn = page.getByText('Explorer la carte', { exact: false })
  if (await btn.count().catch(() => 0)) await btn.first().click().catch(() => {})
  await sleep(1500)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 30000 }).catch(() => {})
  await sleep(800)
}
async function allerA(page, vue) {
  await page.evaluate((v) => window.__labuse_map.jumpTo({ center: v.center, zoom: v.zoom }), vue)
  await sleep(500)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 30000 }).catch(() => {})
  await sleep(900)
}
async function tousTuyau(page, on) {
  await page.evaluate((v) => {
    const m = window.__labuse_map
    for (const l of m.getStyle().layers) if (l.id.startsWith('tuyau-')) m.setLayoutProperty(l.id, 'visibility', v ? 'visible' : 'none')
  }, on)
  await sleep(300)
}
async function tuyauSeul(page, kind) {
  await page.evaluate((k) => {
    const m = window.__labuse_map
    for (const l of m.getStyle().layers) if (l.id.startsWith('tuyau-')) m.setLayoutProperty(l.id, 'visibility', l.id.startsWith(`tuyau-${k}-`) ? 'visible' : 'none')
  }, kind)
  await sleep(400)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 20000 }).catch(() => {})
  await sleep(500)
}
// ancienne couche : le bouton [data-layer=key] du panneau « Couches » ; on l'active (état = pastille mint)
async function ancienSeul(page, keys, cible) {
  for (const k of keys) {
    const b = page.locator(`[data-layer="${k}"]`)
    if (!(await b.count().catch(() => 0))) continue
    const on = await b.first().evaluate((el) => !!el.querySelector('.bg-mint'))
    const veut = k === cible
    if (on !== veut) await b.first().click().catch(() => {})
  }
  await sleep(500)
  await page.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 20000 }).catch(() => {})
  await sleep(700)
}
async function shot(page, nom) { await page.screenshot({ path: `${OUT}${nom}.png` }); console.log('  →', nom + '.png') }

const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1000'] })
const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } })
console.log('chargement', APP_URL)
await page.goto(APP_URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await attendreCarte(page)
console.log('carte prête')

// 1) vue ÎLE, tout le tuyau (tout allumé dès l'île, aucun « Zoomez »)
await tousTuyau(page, true)
await allerA(page, VUES.ile)
await shot(page, 'ile_tout_le_tuyau')

// 2) couches NOUVELLES au panneau (pas d'ancienne) : icpe (points), tri_zone (polygones emboîtés),
//    construction_lineaire (murs de soutènement, lignes) — 3 échelles
for (const kind of ['icpe', 'tri_zone', 'construction_lineaire']) {
  await tuyauSeul(page, kind)
  for (const [nom, v] of [['ile', VUES.ile], ['commune', VUES.stpaul], ['rue', VUES.rue]]) { await allerA(page, v); await shot(page, `neuf_${kind}_${nom}`) }
}

// 3) PARITÉ ancienne ↔ nouvelle (couches présentes des deux côtés) : SUP, aléa inondation, zonage PLU
const PARITE = [
  { kind: 'sup', old: 'sup', vue: VUES.stpaul },
  { kind: 'alea_inondation', old: 'alea_inondation', vue: VUES.stpaul },
  { kind: 'plu_gpu_zone', old: 'zonage', vue: VUES.stpaul },
]
const OLD_KEYS = PARITE.map((p) => p.old)
for (const { kind, old, vue } of PARITE) {
  // nouvelle (tuyau seul)
  await ancienSeul(page, OLD_KEYS, null)   // éteindre toutes les anciennes de démo
  await tuyauSeul(page, kind)
  await allerA(page, vue)
  await shot(page, `parite_${kind}_NEUF`)
  // ancienne (GeoJSON du panneau)
  await tousTuyau(page, false)
  await ancienSeul(page, OLD_KEYS, old)
  await allerA(page, vue)
  await shot(page, `parite_${kind}_ANCIEN`)
}

// 4) Le Port en vue commune, SUP (tuyau) seul : rien en mer
await ancienSeul(page, OLD_KEYS, null)
await tuyauSeul(page, 'sup')
await allerA(page, VUES.leport)
await shot(page, 'leport_commune_sup_rien_en_mer')

// 5) temps d'affichage réel de SUP en vue île
await tuyauSeul(page, 'sup')
const t = await page.evaluate(async (v) => {
  const m = window.__labuse_map
  m.jumpTo({ center: [55.75, -21.35], zoom: 9.4 }); await new Promise(r => setTimeout(r, 1000))
  const t0 = performance.now()
  m.jumpTo({ center: v.center, zoom: v.zoom })
  await new Promise((res) => { const c = () => { if (m.areTilesLoaded()) res(); else m.once('idle', c) }; m.once('idle', c) })
  return performance.now() - t0
}, VUES.ile)
console.log(`SUP vue île — temps d'affichage réel : ${Math.round(t)} ms`)
await shot(page, 'sup_ile_timing')

await browser.close()
console.log('OK captures dans', OUT)
