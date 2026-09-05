// RETOURS-13 — captures aléas R6/R7/R8 (avant/après selon PHASE), attente RÉELLE de la réponse
// (l'endpoint georisque_alea met ~15 s — cause des captures vides du premier passage).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-13/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

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
  await page.waitForTimeout(2500)
  await page.mouse.click(400, 860)
  await page.waitForTimeout(300)
}
const jumpTo = async (lon, lat, zoom) => {
  await page.evaluate(([x, y, z]) => window.__labuse_map.jumpTo({ center: [x, y], zoom: z }), [lon, lat, zoom])
  await page.waitForTimeout(2200)
}

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
const drawer = page.locator('[data-couches-drawer]')
if (!(await drawer.count())) { await page.click('[data-couches-toggle]'); await page.waitForTimeout(500) }

// activer l'aléa mvt et ATTENDRE la réponse (jusqu'à 40 s)
const resp = page.waitForResponse((r) => r.url().includes('kind=georisque_alea'), { timeout: 40000 })
await page.click('[data-layer="alea_mvt"]')
await resp
await page.waitForTimeout(2500)
await page.click('[data-legend-toggle]').catch(() => {})
await page.waitForTimeout(600)

// R6 — île entière, sombre, légende dépliée
await shot('R6-alea-mvt-ile-sombre')
// R7 — zoom sur le cirque de Salazie / Grand Îlet (aléas denses), fond sombre
await jumpTo(55.44, -21.03, 12.6)
await shot('R7-alea-mvt-zoom-sombre')
// R7 — même cadrage sur les 3 autres fonds
await basemap('Clair'); await shot('R7-alea-mvt-zoom-clair')
await basemap('Ortho IGN'); await page.waitForTimeout(2500); await shot('R7-alea-mvt-zoom-ortho')
await basemap('Plan IGN'); await page.waitForTimeout(2000); await shot('R7-alea-mvt-zoom-plan')

// R8 — contours au zoom : 2 zooms × ortho puis IGN (petit zoom = pas de contour, grand = contour)
await basemap('Ortho IGN'); await page.waitForTimeout(1500)
await jumpTo(55.44, -21.03, 12)
await shot('R8-alea-ortho-z12')
await jumpTo(55.44, -21.03, 15)
await shot('R8-alea-ortho-z15')
await basemap('Plan IGN'); await page.waitForTimeout(1500)
await jumpTo(55.44, -21.03, 12)
await shot('R8-alea-plan-z12')
await jumpTo(55.44, -21.03, 15)
await shot('R8-alea-plan-z15')
await basemap('Sombre')
await jumpTo(55.44, -21.03, 15)
await shot('R8-alea-sombre-z15')

// R6 — inondation (île, sombre) : bascule des couches
await page.click('[data-layer="alea_mvt"]')
await page.click('[data-layer="alea_inondation"]')
await page.waitForTimeout(3000)
await jumpTo(55.53, -21.11, 10)
await shot('R6-alea-inondation-sombre')

console.log('erreurs page:', JSON.stringify(errors.slice(0, 6)))
await browser.close()
