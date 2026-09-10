// RECETTE-10 — captures (playwright/chromium). Front dev :5199 (/socle/), API :8031.
// Usage : node scripts/_recette10_capture.mjs
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg

const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/captures-recette-10/', import.meta.url).pathname
const IDU = '97411000EL0157'   // Saint-Denis — a du LiDAR mesuré (faîtage 6,9 / égout 3,0)

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 160)) })
const shot = async (name, clip) => { await page.screenshot({ path: `${OUT}${name}.png`, ...(clip ? { clip } : {}) }); console.log('CAPTURE', name) }
const wait = (ms) => page.waitForTimeout(ms)

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })

// ── T10 / T1 — LiDAR sur la fiche parcelle : « Le bien » (faîtage/égout mesurés) + surélévation ──
await page.evaluate((i) => window.__labuse.select(i), IDU)
await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }).catch(() => {})
await wait(1500)
// ouvrir le tiroir « Le bien »
await page.locator('text=/^Le bien$/').first().click().catch(() => {})
await page.waitForSelector('[data-le-bien]', { timeout: 8000 }).catch(() => {})
await wait(700)
try {
  const el = await page.locator('[data-le-bien]').first().boundingBox()
  if (el) await shot('T10-fiche-le-bien-lidar', { x: Math.max(0, el.x - 8), y: Math.max(0, el.y - 44), width: el.width + 16, height: el.height + 60 })
  else await shot('T10-fiche-le-bien-lidar')
} catch { await shot('T10-fiche-le-bien-lidar') }
// la surélévation (T1) — chercher la ligne « limité par le faîtage » (Constructibilité)
await page.locator('text=/Surélévation/i').first().scrollIntoViewIfNeeded().catch(() => {})
await wait(500)
await shot('T1-fiche-surelevation')

// ── T2 — questionnaire Financier : bandeau à l'écran du champ + section « Affiner » ──
await page.click('[data-banquier-btn]').catch(() => {})
await page.waitForSelector('[data-financier-questionnaire]', { timeout: 10000 }).catch(() => {})
await wait(400)
await page.click('[data-usage="construction"]').catch(() => {})
await wait(700)
await shot('T2-questionnaire-bandeau-affiner')
// déplier « Affiner »
await page.click('[data-financier-affiner-toggle]').catch(() => {})
await wait(400)
await shot('T2-questionnaire-affiner-ouvert')
// fermer le questionnaire
await page.keyboard.press('Escape').catch(() => {})
await wait(300)

// ── T8 — fiche commune : les contrôles de vue restent accessibles (décalés) ──
await page.evaluate(() => { window.__labuse.select(null); window.__labuse.setContexteCommune('Saint-Denis') })
await wait(1500)
await shot('T8-fiche-commune-controles-decales')
await page.evaluate(() => window.__labuse.setContexteCommune(null))
await wait(400)

// ── T11 — la phrase chiffrée/datée à côté des paliers ; T12 — commune à 0 priorité ──
// mode ANALYSE (analyseLabuse) : c'est lui qui affiche la ventilation, la phrase backtest et l'encart 0-priorité
await page.evaluate(() => {
  window.__labuse.setVerdict(true)
  window.__labuse.setFilters({ ...window.__labuse.getFilters(), analyseLabuse: true })
})
await wait(400)
// ouvre le volet Résultats de façon DÉTERMINISTE (toggle seulement s'il est fermé), puis re-vérifie
for (let k = 0; k < 3 && !(await page.$('[data-results-panel]')); k++) {
  await page.evaluate(() => window.__labuse.togglePanel()); await wait(500)
}
await wait(400)
// Saint-Paul (a des paliers) → phrase backtest
await page.evaluate(() => window.__labuse.setCommune('Saint-Paul'))
await wait(2500)
await page.waitForSelector('[data-score-backtest]', { timeout: 8000 }).catch(() => {})
await wait(600)
try {
  const el = await page.locator('[data-results-panel]').first().boundingBox()
  if (el) await shot('T11-backtest-phrase', { x: el.x, y: el.y, width: el.width, height: Math.min(520, el.height) })
  else await shot('T11-backtest-phrase')
} catch { await shot('T11-backtest-phrase') }
// Saint-Philippe → 0 priorité expliqué
await page.evaluate(() => window.__labuse.setCommune('Saint-Philippe'))
await wait(2500)
await page.waitForSelector('[data-zero-priorite]', { timeout: 8000 }).catch(() => {})
await wait(400)
try {
  const el = await page.locator('[data-results-panel]').first().boundingBox()
  if (el) await shot('T12-zero-priorite', { x: el.x, y: el.y, width: el.width, height: Math.min(520, el.height) })
  else await shot('T12-zero-priorite')
} catch { await shot('T12-zero-priorite') }

// ── T7 — le segment « Un professionnel a obtenu un permis ici » ──
await page.evaluate(() => window.__labuse.setCommune('Saint-Denis'))
await wait(2000)
await page.locator('text=/obtenu un permis/i').first().scrollIntoViewIfNeeded().catch(() => {})
await wait(500)
await shot('T7-segment-permis-pro')

await browser.close()
console.log('DONE')
