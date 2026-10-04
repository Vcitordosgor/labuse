// RECETTE-1e — captures « APRÈS » de toute la recette (état mergé H1→H16 + H13.3 + B).
// Un écran par outil (entrée refondue : pattern F, « Méthode et limites », etc.) + quelques fiches.
// Chromium headful (channel chrome) = vrai GPU, carte rendue.  node frontend/qa/recette1e_walkthrough_captures.mjs
import pkg from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
import { mkdirSync } from 'node:fs'

const BASE = 'http://127.0.0.1:5895/socle/'
const OUT = new URL('../../docs/audit-2026-09/RECETTE-1/captures-recette-1e/', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })
const IDU_SP = '97415000CV1186'   // Saint-Paul (témoin recette)
const IDU_SD = '97411000BZ1065'   // Saint-Denis (témoin recette)

const browser = await chromium.launch({ headless: false, channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error' && !/40[0-4]/.test(m.text())) console.error('PAGE-ERR', m.text().slice(0, 140)) })
const shot = async (name) => {
  try { await page.screenshot({ path: `${OUT}${name}.png`, timeout: 8000, animations: 'disabled' }); console.log('CAPTURE', name) }
  catch (e) { await page.screenshot({ path: `${OUT}${name}.png`, timeout: 8000, animations: 'disabled' }).catch(() => console.log('SHOT FAIL', name, String(e).slice(0, 50))) }
}
const wait = (ms) => page.waitForTimeout(ms)
const openOutil = async (key) => { await page.evaluate((k) => { window.__labuse.select(null); window.__labuse.setModule(k) }, key); await wait(1800) }

await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForFunction(() => window.__labuse != null && window.__labuse_map != null, { timeout: 30000 })
await wait(2500)
await shot('00-carte-accueil')

// ── Outils de la recette (un écran d'entrée chacun) ──
const OUTILS = [
  ['H1', 'plu'], ['H2', 'permis'], ['H3', 'communes'], ['H4', 'patrimoine'],
  ['H5', 'assemblage'], ['H6', 'comparer'], ['H8', 'etude-zone'], ['H9', 'temps'],
  ['H11', 'gabarit'], ['H12', 'taxe-amenagement'], ['H13', 'prospection-solaire'],
  ['H14', 'blocs-fonciers'], ['H15', 'successions'], ['H16', 'courriers'],
]
for (const [h, key] of OUTILS) {
  await openOutil(key)
  await shot(`${h}-outil-${key}`)
}

// ── H10 Faisabilité : dans la fiche (sélection d'une parcelle témoin) ──
await page.evaluate(() => window.__labuse.setModule(null))
await page.evaluate((i) => window.__labuse.select(i), IDU_SD)
await wait(2500)
await shot('H10-fiche-ouverte')
// onglet Faisabilité si présent
await page.locator('text=/Faisabilit/i').first().click().catch(() => {})
await wait(1500)
await shot('H10-fiche-faisabilite')

// ── H7 « Méthode et limites » : ouvrir le pied d'un outil (Taxe) ──
await page.evaluate(() => window.__labuse.select(null))
await openOutil('taxe-amenagement')
await page.locator('text=/Méthode et limites/i').first().click().catch(() => {})
await wait(900)
await shot('H7-methode-et-limites')

await browser.close()
console.log('DONE walkthrough')
