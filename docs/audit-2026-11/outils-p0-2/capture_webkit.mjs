// OUTILS-P0-2 — captures WebKit par point (preuve d'écran). Lance l'app (vite 10800 / uvicorn 7280)
// AVANT. WebKit via playwright 1.49.1 (= navigateur webkit-2104 ; le playwright 1.62 du front ne
// supporte pas WebKit sur macOS 13 arm64). Usage : node docs/audit-2026-11/outils-p0-2/capture_webkit.mjs
import pw from '/tmp/pwwk/node_modules/playwright/index.js'
const { webkit } = pw

const BASE = 'http://localhost:10800/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-estimer3/docs/audit-2026-11/outils-p0-2'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const APPT = '97411000HI0215'
const TERRAIN_HG = '97409000AK0804'        // hors gamme (> 21 M€ avant)
const TERRAIN_NC = '97409000AK1204'        // zone non constructible (A)
const ZONE = '97411000BZ1065'

async function ouvrirModule(page, module) {
  await page.evaluate((m) => { window.__labuse.togglePanel?.(true); window.__labuse.setModule(m) }, module)
  await sleep(800)
}

// tape un IDU dans le champ ParcelInput de l'outil (combobox `data-<attr>`), attend la suggestion
// (role=option) et la clique → sélectionne la parcelle.
async function choisirParcelle(page, attr, idu) {
  const champ = page.locator(`input[data-${attr}]`).first()
  await champ.waitFor({ timeout: 20000 })
  await champ.click()
  await champ.fill(idu)
  await sleep(3200)
  const opt = page.getByRole('option').first()
  await opt.waitFor({ timeout: 20000 })
  await opt.click()
  await sleep(2000)
}

async function estimer(page, idu, nom, { surface, pieces, decoch } = {}) {
  await ouvrirModule(page, 'analyser-annonce')
  // la boîte parcelle (EntreeParcelle) peut rester remplie d'un passage précédent → on la vide.
  const vider = page.locator('[data-entree-vider]')
  if (await vider.count()) { await vider.first().click(); await sleep(600) }
  await choisirParcelle(page, 'entree-parcelle', idu)
  // attendre que l'estimation se charge (section « Valeur estimée » / « Prix au m² », role=status).
  await page.locator('section[role="status"]').first().waitFor({ timeout: 40000 })
  await sleep(2000)
  if (surface) {
    const s = page.locator('[data-estimer-surface]')
    await s.waitFor({ timeout: 30000 }); await s.fill(String(surface)); await s.press('Enter'); await sleep(1800)
  }
  if (pieces) {
    const pb = page.locator('[data-estimer-pieces]')
    if (await pb.count()) { await pb.nth(pieces).click(); await sleep(1800) }
  }
  if (decoch) {
    const chks = page.locator('section input[type="checkbox"]')
    if (await chks.count()) { await chks.first().click(); await sleep(2200) }
  }
  await sleep(1500)
  await page.screenshot({ path: `${OUT}/${nom}.png`, fullPage: true })
  console.log('✓', nom + '.png')
}

async function main() {
  const browser = await webkit.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') console.log('  [console.error]', m.text().slice(0, 160)) })

  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => !!window.__labuse, null, { timeout: 30000 })
  // bannière cookies : refuser les tiers (sinon elle recouvre le bas de l'écran)
  const refuser = page.getByRole('button', { name: /Refuser les tiers/i })
  if (await refuser.count()) { await refuser.first().click().catch(() => {}) }
  await sleep(1200)

  // P1 + P4 — Estimer (appartement) : pièces saisies + vente décochée + phrase sous fourchettes
  await estimer(page, APPT, 'p1-p4-estimer-appartement', { surface: 62, pieces: 1, decoch: true })
  // P2 — Terrain HORS GAMME : pas de total, repère €/m² + ventes + raison
  await estimer(page, TERRAIN_HG, 'p2-terrain-hors-gamme')
  // P2 — Terrain NON CONSTRUCTIBLE : pas de valeur à bâtir, raison dite
  await estimer(page, TERRAIN_NC, 'p2-terrain-non-constructible')

  // P3 — Étude de zone : prix du cercle (N ventes · période) + secteur à part + annonces renommées
  await ouvrirModule(page, 'etude-zone')
  await choisirParcelle(page, 'zone-point', ZONE)
  await page.locator('[data-zone-rayon="2"]').click(); await sleep(400)
  await page.getByRole('button', { name: /Lire la zone/i }).click()
  // le calcul de zone (DVF/cercle) prend quelques secondes ; l'étape 2 (sections) apparaît ensuite.
  // La section « Immobilier » est repliée par défaut et ne rend ses enfants qu'une fois ouverte.
  const immo = page.getByRole('button', { name: /Immobilier/i })
  await immo.waitFor({ timeout: 45000 })
  await immo.click()
  await page.locator('[data-zone-prix-cercle]').waitFor({ state: 'visible', timeout: 20000 })
  await sleep(2000)
  await page.screenshot({ path: `${OUT}/p3-etude-zone-cercle.png`, fullPage: true })
  console.log('✓ p3-etude-zone-cercle.png')

  await browser.close()
  console.log('\nTerminé.')
}

main().catch((e) => { console.error('ÉCHEC', String(e).slice(0, 300)); process.exit(1) })
