// SDP-VERIF-1 phase 2 — captures avant/après des libellés (lecture seule côté app).
// La fiche /parcels/{idu} est MOCKÉE par un dump réel (fiche_AT1066_<phase>.json) : le vrai
// composant Fiche rend les vraies valeurs sans dépendre de l'API (dont le boot self-deadlock).
// Usage : node capture_sdpverif.mjs <avant|apres>
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'

const PHASE = process.argv[2] || 'avant'
const URL = process.env.URL || 'http://localhost:5912/'
const IDU = '97410000AT1066'
const OUT = process.env.CAPDIR || new URL('./', import.meta.url).pathname
const fiche = JSON.parse(readFileSync(`${OUT}fiche_AT1066_${PHASE}.json`, 'utf-8'))
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const page = await browser.newPage({ viewport: { width: 1280, height: 1600 } })

// MOCK de la fiche (et de ses sous-appels lents) ; tout le reste passe au proxy (peut 404 sans gêner).
await page.route(`**/parcels/${IDU}*`, (route) => {
  if (route.request().url().includes('/geojson') || route.request().url().includes('.kmz')) return route.continue()
  route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fiche) })
})

console.log(`[${PHASE}] chargement`, URL)
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
await page.waitForFunction(() => !!(window.__labuse && window.__labuse.select), { timeout: 60000 })

// 1) FILTRE « Emprise bâtie » (le libellé du 29 %) — panneau gauche, sans donnée parcelle.
try {
  // ouvrir le panneau FILTRES (collapsé par défaut), puis « Affiner la recherche »
  const filtres = page.getByText('Filtres', { exact: false })
  if (await filtres.count().catch(() => 0)) { await filtres.first().click().catch(() => {}); await sleep(400) }
  const aff = page.locator('[data-affiner-toggle]')
  if (await aff.count().catch(() => 0)) { await aff.first().click().catch(() => {}); await sleep(500) }
  const bloc = page.getByText('Emprise bâtie', { exact: false }).first()
  if (await bloc.count().catch(() => 0)) {
    await bloc.scrollIntoViewIfNeeded().catch(() => {})
    await sleep(300)
    const box = await bloc.locator('xpath=ancestor::div[1]').boundingBox().catch(() => null)
    await page.screenshot({ path: `${OUT}filtre_emprise_${PHASE}.png`, clip: box ? { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: Math.min(640, box.width + 16), height: box.height + 60 } : undefined })
    console.log('  → filtre_emprise_' + PHASE + '.png')
  } else console.log('  ✗ bloc « Emprise bâtie » introuvable (filtre non ouvert ?)')
} catch (e) { console.log('  ✗ filtre:', String(e.message || e).split('\n')[0]) }

// 2) FICHE — ouvre AT1066, capture le bandeau (tuile « SDP restante ») + §10 Potentiel.
try {
  await page.evaluate((idu) => window.__labuse.select(idu), IDU)
  await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 30000 })
  await sleep(1200)
  const band = page.locator('[data-bandeau-chiffres]').first()
  await band.scrollIntoViewIfNeeded().catch(() => {})
  await band.screenshot({ path: `${OUT}fiche_bandeau_${PHASE}.png` }).catch(async () => {
    await page.screenshot({ path: `${OUT}fiche_bandeau_${PHASE}.png` }) })
  console.log('  → fiche_bandeau_' + PHASE + '.png')
  // §10 Potentiel : ouvrir le tiroir et capturer
  const pot = page.getByText('Potentiel', { exact: false })
  if (await pot.count().catch(() => 0)) {
    await pot.first().scrollIntoViewIfNeeded().catch(() => {})
    await pot.first().click().catch(() => {})
    await sleep(800)
    const drawer = page.locator('#potentiel, [id="potentiel"]').first()
    if (await drawer.count().catch(() => 0)) {
      await drawer.scrollIntoViewIfNeeded().catch(() => {})
      await sleep(300)
      await drawer.screenshot({ path: `${OUT}fiche_potentiel_${PHASE}.png` }).catch(async () => {
        await page.screenshot({ path: `${OUT}fiche_potentiel_${PHASE}.png`, fullPage: true }) })
    } else {
      await page.screenshot({ path: `${OUT}fiche_potentiel_${PHASE}.png`, fullPage: true })
    }
    console.log('  → fiche_potentiel_' + PHASE + '.png')
  }
} catch (e) { console.log('  ✗ fiche:', String(e.message || e).split('\n')[0]) }

await browser.close()
console.log(`[${PHASE}] fait`)
