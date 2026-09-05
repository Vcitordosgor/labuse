// RETOURS-13 Lot 1 — captures AVANT (état de la branche à la recette de Vic du 05/09).
// Cadrages du mandat : Ortho IGN île entière (cadre par défaut), fond IGN et clair au même
// cadrage, menu Couches déplié, aléas (hachures + pas de rouge + contours sur ortho).
// Lancer depuis frontend/ : CHROME=<exe> node ../qa/retours13_lot1_avant.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-13/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'avant'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (name) => { await page.screenshot({ path: `${OUT}/${name}-${SUFFIX}.png` }); console.log('  shot', name, SUFFIX) }
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2500)   // tuiles
  await page.mouse.click(400, 860)  // referme le menu (clic sur le backdrop)
  await page.waitForTimeout(300)
}
const toggleLayer = async (key) => { await page.click(`[data-layer="${key}"]`); await page.waitForTimeout(1800) }
const zoomIn = async (n, x = 720, y = 450) => {
  for (let i = 0; i < n; i++) { await page.mouse.dblclick(x, y); await page.waitForTimeout(900) }
}

// ── R1 — la mer, île entière (cadre par défaut à l'ouverture) sur Ortho IGN / Plan IGN / Clair ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await basemap('Ortho IGN')
await page.waitForTimeout(3500)
await shot('R1-ortho-ile')
await basemap('Plan IGN')
await page.waitForTimeout(2000)
await shot('R1-plan-ile')
await basemap('Clair')
await page.waitForTimeout(1500)
await shot('R1-clair-ile')

// ── R3 — menu Couches déplié (les familles, dont réseaux) ──
await basemap('Sombre')
const drawer = page.locator('[data-couches-drawer]')
if (!(await drawer.count())) { await page.click('[data-couches-toggle]'); await page.waitForTimeout(500) }
// défiler jusqu'à la famille réseaux
await drawer.evaluate((el) => { el.scrollTop = el.scrollHeight * 0.55 })
await page.waitForTimeout(300)
await shot('R3-couches-reseaux')

// ── R6/R7 — aléa mouvement de terrain, fond sombre, île + zoom (hachures, teintes, légende) ──
await toggleLayer('alea_mvt')
await page.click('[data-legend-toggle]').catch(() => {})
await page.waitForTimeout(600)
await shot('R6-alea-mvt-ile-sombre')
// zoom sur l'ouest (Saint-Paul / Mafate — beaucoup d'aléas)
await zoomIn(4, 620, 420)
await shot('R7-alea-mvt-zoom-sombre')

// ── R8 — mêmes aléas sur ORTHO (contours) à 2 zooms ──
await basemap('Ortho IGN')
await page.waitForTimeout(2500)
await shot('R8-alea-ortho-zoom1')
await zoomIn(2, 720, 450)
await shot('R8-alea-ortho-zoom2')

// ── R6 — aléa inondation (légende) ──
await toggleLayer('alea_mvt')
await toggleLayer('alea_inondation')
await basemap('Sombre')
await page.waitForTimeout(1200)
await shot('R6-alea-inondation-ile-sombre')

console.log('erreurs page:', JSON.stringify(errors.slice(0, 6)))
await browser.close()
