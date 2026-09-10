// RECETTE-12 B1 — PREUVE carte : en mode analyse, seules Priorité + À suivre sont peintes ; les
// « Sans signal » et « Écartée » ne sont plus un aplat gris (opacité nulle), contour au zoom seul.
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/captures-recette-12/', import.meta.url).pathname

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 140)) })
const wait = (ms) => page.waitForTimeout(ms)
const shot = async (n) => { await page.screenshot({ path: `${OUT}${n}.png` }); console.log('CAPTURE', n) }

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await wait(800)
// mode ANALYSE en vue ÎLE (toutes les parcelles en tuiles MVT — là où le voile gris sévissait).
// PAS de setCommune (qui bascule en mode commune GeoJSON) : on reste sur l'île et on VOLE à Saint-Denis.
await page.evaluate(() => {
  window.__labuse.setVerdict(true)
  window.__labuse.setFilters({ ...window.__labuse.getFilters(), analyseLabuse: true })
})
await wait(500)
await page.evaluate(() => window.__labuse.setFlyTo({ center: [55.448, -20.885], zoom: 13.5 }))
await wait(4000)
const opinionInfo = await page.evaluate(() => {
  const f = window.__labuse.getFilters(); return { analyse: f.analyseLabuse, communes: f.communes }
})
console.log('filtres =', JSON.stringify(opinionInfo))
await shot('B1-saint-denis-analyse')

// zoomer (≥ 15) : le contour discret des non-promues apparaît, sans jamais d'aplat gris
await page.evaluate(() => window.__labuse.setFlyTo({ center: [55.448, -20.885], zoom: 16 }))
await wait(3500)
await shot('B1-saint-denis-zoom16')

await browser.close()
console.log('DONE')
