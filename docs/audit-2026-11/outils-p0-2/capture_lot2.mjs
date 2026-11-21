// OUTILS-P0-2 recette Lot 2 — captures cadrées sur l'élément, avant/après. App vite 10800 / uvicorn 7280.
// node docs/audit-2026-11/outils-p0-2/capture_lot2.mjs <avant|apres>
import pw from '/tmp/pwwk/node_modules/playwright/index.js'
const { webkit } = pw
const SUF = process.argv[2] || 'apres'
const BASE = 'http://localhost:10800/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-estimer3/docs/audit-2026-11/outils-p0-2'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const BH = '97411000BH0309'   // appartement (12 ventes)
const ID = '97411000ID0002'   // immeuble multi-logements
const BN = '97422000BN2939'   // terrain nu (Tampon)
const AK = '97409000AK1204'   // terrain non constructible (zone A)
const ZONE = '97411000BZ1065'

async function ouvrir(page, module) { await page.evaluate((m) => { window.__labuse.togglePanel?.(true); window.__labuse.setModule(m) }, module); await sleep(800) }
async function choisir(page, attr, idu) {
  const v = page.locator('[data-entree-vider]'); if (await v.count()) { await v.first().click().catch(() => {}); await sleep(500) }
  const ch = page.locator(`input[data-${attr}]`).first(); await ch.waitFor({ timeout: 20000 }); await ch.click(); await ch.fill(idu); await sleep(3200)
  const o = page.getByRole('option').first(); await o.waitFor({ timeout: 20000 }); await o.click(); await sleep(3500)
}
async function shot(page, sel, name) {
  try { const el = page.locator(sel).first(); await el.waitFor({ timeout: 8000 }); await el.screenshot({ path: `${OUT}/${SUF}-${name}.png` }); console.log('  ✓', `${SUF}-${name}.png`) }
  catch (e) { console.log('  ✗', name, String(e).slice(0, 70)) }
}

async function main() {
  const b = await webkit.launch(); const c = await b.newContext({ viewport: { width: 1440, height: 1200 }, reducedMotion: 'reduce' }); const page = await c.newPage()
  await page.goto(BASE, { waitUntil: 'domcontentloaded' }); await page.waitForFunction(() => !!window.__labuse, null, { timeout: 30000 })
  const ref = page.getByRole('button', { name: /Refuser les tiers/i }); if (await ref.count()) await ref.first().click().catch(() => {})
  await sleep(1000)

  // P1 — appartement/immeuble sans surface : « Saisissez la surface habitable pour obtenir l'estimation »
  await ouvrir(page, 'analyser-annonce'); await choisir(page, 'entree-parcelle', ID)
  await shot(page, 'section[role="status"]', 'p1-surface-manquante')
  // P2 — options pièces (doit commencer à « 1 »)
  await shot(page, 'section:has([data-estimer-pieces])', 'p2-pieces')
  // P5 — boîte adresse (trait d'union insécable sur la commune)
  await shot(page, '[data-entree-parcelle-choisie]', 'p5-adresse')

  // P9 — appartement avec surface saisie : deux bandes
  await choisir(page, 'entree-parcelle', BH)
  let s = page.locator('[data-estimer-surface]'); if (await s.count()) { await s.fill('62'); await s.press('Enter'); await sleep(2500) }
  await shot(page, 'section[role="status"]', 'p9-deux-bandes')

  // P3 + P6 — terrain : Mesures (pas de « Bâti … au sol ») + ventes retenues (distances « — » en fin)
  await choisir(page, 'entree-parcelle', BN)
  await shot(page, 'section:has-text("Ce que LABUSE a mesuré")', 'p3-mesures-terrain')
  await shot(page, 'section:has-text("Les ventes retenues")', 'p6-ventes-tri')

  // P4 — terrain non constructible : pas de disclaimer, bouton PDF présent (panneau entier)
  await choisir(page, 'entree-parcelle', AK)
  await sleep(1500)
  await shot(page, '[data-analyser-panneau], aside, [class*="panel"]', 'p4-non-constr-full')
  await page.screenshot({ path: `${OUT}/${SUF}-p4-non-constr.png` }); console.log('  ✓', `${SUF}-p4-non-constr.png`)

  // P8 — Étude de zone : bouton rayon « 0,5 km » sur une ligne + vocabulaire
  await ouvrir(page, 'etude-zone'); await choisir(page, 'zone-point', ZONE)
  await shot(page, '[data-zone-rayons]', 'p8-rayon')
  await page.locator('[data-zone-rayon="0.5"]').click().catch(() => {}); await sleep(400)
  await page.getByRole('button', { name: /Lire la zone/i }).click().catch(() => {})
  await page.locator('[data-zone-prix-cercle]').waitFor({ state: 'visible', timeout: 45000 }).catch(() => {})
  await sleep(2000)
  await shot(page, '[data-zone-section="immobilier"]', 'p8-immobilier')

  await b.close(); console.log(`Terminé (${SUF}).`)
}
main().catch((e) => { console.error('ÉCHEC', String(e).slice(0, 200)); process.exit(1) })
