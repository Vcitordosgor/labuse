// ETUDE-FICHE-1 — captures WebKit de l'Étude de faisabilité, en action.
// Lecture seule : n'écrit que des PNG sous docs/audit-2026-11/etude-fiche-1/captures/.
// Lancement : node scripts/etude_fiche_captures.mjs
// WebKit via la build 2104 compatible mac13-arm64 (le playwright 1.62 du front a lâché WebKit sur cet OS).
import pw from '/Users/openclaw/labuse-restore-k/node_modules/playwright-core/index.js'
const { webkit } = pw
import { mkdirSync } from 'node:fs'

const BASE = 'http://127.0.0.1:10100/socle/'
const OUT = 'docs/audit-2026-11/etude-fiche-1/captures'
mkdirSync(OUT, { recursive: true })

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const log = (...a) => console.log('[cap]', ...a)

async function shot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png` })
  log('shot', name)
}
// capture pleine hauteur du panneau de l'étude (overlay scrollable)
async function shotFull(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true })
  log('shotFull', name)
}

async function ouvrir(page, idus) {
  await page.evaluate((ids) => window.__labuse.ouvrirEtude(ids), idus)
  // attendre le montage de l'overlay (lazy)
  await page.waitForTimeout(800)
}

async function attendreValidation(page) {
  // étape 1 : attendre qu'au moins une ligne parcelle apparaisse OU message
  await page.waitForSelector('[data-etude-parcelle-row], .text-coral', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(1200)
}

async function continuer(page) {
  const b = page.getByRole('button', { name: /Continuer/ })
  await b.first().click()
  await page.waitForTimeout(500)
}

async function choisirType(page, key) {
  await page.click(`[data-etude-type="${key}"]`)
  await page.waitForTimeout(1500) // charge le régime stationnement + mixité
}

async function setCount(page, type, n) {
  const inp = page.locator(`[data-etude-count="${type}"]`)
  await inp.fill(String(n))
  await inp.dispatchEvent('input')
  await page.waitForTimeout(150)
}

async function analyser(page) {
  const b = page.getByRole('button', { name: /Analyser mon projet/ })
  await b.click()
  // calcul ~15-40s ; attendre la section résultat (recit / controles)
  await page.waitForSelector('[data-recit], [data-variante-absente], text=Contrôles', { timeout: 90000 }).catch(() => {})
  await page.waitForTimeout(2500)
}

async function fermer(page) {
  await page.evaluate(() => window.__labuse.fermerEtude && window.__labuse.fermerEtude()).catch(() => {})
  await page.waitForTimeout(400)
}

async function main() {
  const browser = await webkit.launch()
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    reducedMotion: 'reduce',
  })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') log('PAGE-ERR', m.text().slice(0, 160)) })

  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1500)
  log('app prête')

  // ───────────────────────────────────────────────────────────────────────────
  // PARCOURS PRINCIPAL — Saint-André AX255+256 (cas « 48 logts » des architectes),
  // type « logement social », stationnement aérien. Programme modéré qui tient.
  // ───────────────────────────────────────────────────────────────────────────
  const SANDRE = ['97409000AX0255', '97409000AX0256']

  await ouvrir(page, SANDRE)
  await attendreValidation(page)
  await shotFull(page, '01-etape1-parcelles')

  await continuer(page)
  await shotFull(page, '02-etape2-type-projet')

  await choisirType(page, 'social')
  await shotFull(page, '03-etape2-type-choisi-social')

  await continuer(page)
  await page.waitForTimeout(1500) // jauge
  await setCount(page, 'T2', 8)
  await setCount(page, 'T3', 6)
  await setCount(page, 'T1', 4)
  await shotFull(page, '04-etape3-programme-aerien')

  // écran de calcul (lancer + capture rapide pendant le chargement)
  const bAnalyse = page.getByRole('button', { name: /Analyser mon projet/ })
  await bAnalyse.click()
  await page.waitForTimeout(600)
  await shot(page, '05-calcul-en-cours')
  await page.waitForSelector('[data-recit], [data-variante-absente]', { timeout: 90000 }).catch(() => {})
  await page.waitForTimeout(2500)
  await shotFull(page, '06-resultat-complet-social-aerien')

  // Zoom sur les composants du résultat : plan masse, coupe, contrôles, tableau.
  // On capture par recherche de texte/section.
  for (const [sel, name] of [
    ['svg', '07-resultat-plan-masse'],
  ]) {
    const el = page.locator(sel).first()
    if (await el.count()) { await el.scrollIntoViewIfNeeded().catch(() => {}); await page.waitForTimeout(400); await shot(page, name) }
  }
  // Contrôles (section réglementaire/projet) : scroller vers le bas
  await page.evaluate(() => { const o = document.querySelector('[class*="overflow"]'); })
  // capture plein écran déjà faite (06) ; on ajoute des captures ciblées ensuite via sections

  await fermer(page)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1200)

  // ───────────────────────────────────────────────────────────────────────────
  // LES QUATRE TYPES sur la même assiette (Saint-André), aérien — étape résultat.
  // ───────────────────────────────────────────────────────────────────────────
  async function runType(key, prog, name, statio = 'aerien') {
    await ouvrir(page, SANDRE)
    await attendreValidation(page)
    await continuer(page)
    await choisirType(page, key)
    await continuer(page)
    await page.waitForTimeout(1500)
    for (const [t, n] of prog) await setCount(page, t, n)
    if (statio === 'sous_sol') {
      // bouton sous-sol à l'étape 3
      const bs = page.getByRole('button', { name: /sous-sol|Sous-sol/ })
      if (await bs.count()) { await bs.first().click(); await page.waitForTimeout(500) }
    }
    await shotFull(page, `${name}-etape3`)
    await analyser(page)
    await shotFull(page, `${name}-resultat`)
    await fermer(page)
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
    await page.waitForTimeout(1000)
  }

  await runType('etudiante', [['T1', 12], ['T2', 6]], '10-type-etudiante-aerien')
  await runType('senior', [['T2', 8], ['T3', 4]], '11-type-senior-aerien')
  // social déjà couvert par 06 ; on refait une version type-résultat homogène
  await runType('social', [['T2', 8], ['T3', 6]], '12-type-social-aerien')
  // sous-sol (social) — si disponible
  await runType('social', [['T2', 10], ['T3', 6]], '13-type-social-sous-sol', 'sous_sol')

  // Lotissement — Saint-Leu AC261+262+264 (AC263 absent du cadastre)
  const SLEU = ['97413000AC0261', '97413000AC0262', '97413000AC0264']
  await ouvrir(page, SLEU)
  await attendreValidation(page)
  await shotFull(page, '14-lotissement-etape1')
  await continuer(page)
  await choisirType(page, 'lotissement')
  await shotFull(page, '15-lotissement-etape2')
  await continuer(page)
  await page.waitForTimeout(1200)
  await shotFull(page, '16-lotissement-etape3')
  await analyser(page)
  await shotFull(page, '17-lotissement-resultat')
  await fermer(page)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1000)

  // ───────────────────────────────────────────────────────────────────────────
  // CAS LIMITES
  // ───────────────────────────────────────────────────────────────────────────
  // (a) Programme qui dépasse la capacité — Saint-André, T4×60
  await ouvrir(page, SANDRE)
  await attendreValidation(page)
  await continuer(page)
  await choisirType(page, 'social')
  await continuer(page)
  await page.waitForTimeout(1500)
  await setCount(page, 'T4', 60)
  await shotFull(page, '20-depassement-etape3')
  await analyser(page)
  await shotFull(page, '21-depassement-resultat')
  await fermer(page)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1000)

  // (b) Parcelles non contiguës — Étang-Salé + Saint-Denis (communes différentes)
  await ouvrir(page, ['97404000AW0099', '97411000DL0247'])
  await attendreValidation(page)
  await shotFull(page, '22-non-contigues-etape1')

  await browser.close()
  log('TERMINÉ')
}

main().catch((e) => { console.error(e); process.exit(1) })
