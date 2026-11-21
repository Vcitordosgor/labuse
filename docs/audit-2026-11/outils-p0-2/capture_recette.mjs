// OUTILS-P0-2 recette — captures WebKit par point. App : vite 10800 / uvicorn 7280 AVANT.
// WebKit via playwright 1.49.1 (webkit-2104). node docs/audit-2026-11/outils-p0-2/capture_recette.mjs
import pw from '/tmp/pwwk/node_modules/playwright/index.js'
const { webkit } = pw
const BASE = 'http://localhost:10800/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-estimer3/docs/audit-2026-11/outils-p0-2'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const TERRAIN_TAMPON = '97422000BN2939'   // dates MM/YYYY, « m² de terrain », « au Tampon », fourchette unique
const APPART = '97411000BH0309'           // 12 ventes (appart) sans terrain + pièces/décoché + phrase
const NON_CONSTR = '97409000AK1204'       // « Pas d'estimation : zone non constructible (A) »
const MULTI = '97411000ID0002'            // champ vide + « dernière vente dans l'immeuble »
const SYMBOLIQUE = '97413000DD1534'       // « cession à 1 €, hors marché »
const MAISON_PORT = '97407000AZ0045'      // « au Port »
const ZONE = '97411000BZ1065'

async function ouvrir(page, module) {
  await page.evaluate((m) => { window.__labuse.togglePanel?.(true); window.__labuse.setModule(m) }, module)
  await sleep(800)
}
async function choisir(page, attr, idu) {
  const champ = page.locator(`input[data-${attr}]`).first()
  await champ.waitFor({ timeout: 20000 })
  await champ.click(); await champ.fill(idu); await sleep(3200)
  const opt = page.getByRole('option').first()
  await opt.waitFor({ timeout: 20000 }); await opt.click(); await sleep(2000)
}
async function estimer(page, idu, nom, { surface, pieces, decoch, attendre } = {}) {
  await ouvrir(page, 'analyser-annonce')
  const vider = page.locator('[data-entree-vider]')
  if (await vider.count()) { await vider.first().click(); await sleep(600) }
  await choisir(page, 'entree-parcelle', idu)
  await page.locator('section[role="status"]').first().waitFor({ timeout: 45000 })
  if (attendre) await page.locator(attendre).first().waitFor({ timeout: 45000 }).catch(() => {})
  await sleep(2000)
  if (surface) { const s = page.locator('[data-estimer-surface]'); await s.fill(String(surface)); await s.press('Enter'); await sleep(1800) }
  if (pieces) { const pb = page.locator('[data-estimer-pieces]'); if (await pb.count()) { await pb.nth(pieces).click(); await sleep(1800) } }
  if (decoch) { const c = page.locator('section input[type="checkbox"]'); if (await c.count()) { await c.first().click(); await sleep(2000) } }
  await sleep(1200)
  await page.screenshot({ path: `${OUT}/${nom}.png`, fullPage: true })
  console.log('✓', nom + '.png')
}

async function main() {
  const browser = await webkit.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1100 }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') console.log('  [err]', m.text().slice(0, 140)) })
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => !!window.__labuse, null, { timeout: 30000 })
  const ref = page.getByRole('button', { name: /Refuser les tiers/i }); if (await ref.count()) await ref.first().click().catch(() => {})
  await sleep(1000)

  await estimer(page, TERRAIN_TAMPON, 'recette-1-3-8-terrain-tampon')       // dates, m² de terrain, fourchette unique, au Tampon
  await estimer(page, APPART, 'recette-2-appartement', { surface: 62, pieces: 1, decoch: true })  // ventes sans terrain, P1/P4
  await estimer(page, NON_CONSTR, 'recette-4-non-constructible', { attendre: '[data-estimer-non-constructible]' })
  await estimer(page, MULTI, 'recette-5-multi-logement')                    // champ vide + indication immeuble
  await estimer(page, SYMBOLIQUE, 'recette-6-symbolique')                   // cession à 1 €, hors marché
  await estimer(page, MAISON_PORT, 'recette-8-maison-au-port')              // « au Port »

  // Zone à 0,5 km (virgule) : secteur « maisons, AAAA–AAAA », fenêtre 36 mois, Immobilier dépliée.
  await ouvrir(page, 'etude-zone')
  await choisir(page, 'zone-point', ZONE)
  await page.locator('[data-zone-rayon="0.5"]').click(); await sleep(400)
  await page.getByRole('button', { name: /Lire la zone/i }).click()
  await page.locator('[data-zone-prix-cercle]').waitFor({ state: 'visible', timeout: 45000 })
  await sleep(2500)
  await page.screenshot({ path: `${OUT}/recette-7-zone-cercle.png`, fullPage: true })
  console.log('✓ recette-7-zone-cercle.png')

  await browser.close(); console.log('\nTerminé.')
}
main().catch((e) => { console.error('ÉCHEC', String(e).slice(0, 300)); process.exit(1) })
