// FICHE-FIX-5 (Lot A) — capture de la CARTE en navigateur VISIBLE (headless:false) : le WebGL sans
// écran ne rastérise pas. Sélectionne une parcelle (via le store) et capture le viewport : la
// parcelle doit être zoomée + détourée du liseré blanc.
// Usage : node scripts/kelfix-map.mjs <label> <idu> [click]
//   'click' : au lieu du store, simule un CLIC carte au centre visible après un pré-zoom.
import pkg from '/Users/openclaw/Desktop/labuse-kelfix/frontend/node_modules/playwright-core/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5745/socle/'
const [, , label, idu, mode] = process.argv
if (!label || !idu) { console.error('args: <label> <idu> [click]'); process.exit(2) }

// headless:false hang au screenshot (pas de session d'affichage active pour composer) → on reste en
// headless : le Chromium 1217 rastérise le WebGL via SwiftShader ici (les fonds de carte sortent).
const browser = await chromium.launch({
  executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
})
const page = await browser.newPage({ viewport: { width: 1400, height: 950 }, deviceScaleFactor: 1 })
page.on('console', (m) => { if (m.type() === 'error') console.error('  [err]', m.text().slice(0, 160)) })
await page.goto(`${BASE}#f=1&idu=${idu}`, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('.maplibregl-canvas', { timeout: 20000 }).catch(() => {})
await page.waitForTimeout(2500)

if (mode === 'click') {
  // pré-zoom sur la parcelle SANS ouvrir la fiche (focus), puis clic au centre du viewport.
  await page.evaluate(async (idu) => {
    const m = await import('/socle/src/store/useApp.ts'); const s = m.useApp.getState()
    s.setView('cartes'); s.select(null); s.focusParcelle?.(idu, { fiche: false })
  }, idu)
  await page.waitForTimeout(3500)
  // clic au point central de la zone carte visible (gauche du panneau)
  await page.mouse.click(500, 460)
  await page.waitForTimeout(3500)
} else {
  await page.evaluate(async (idu) => {
    const m = await import('/socle/src/store/useApp.ts'); const s = m.useApp.getState()
    s.setView('cartes'); s.select(idu)
  }, idu)
  await page.waitForTimeout(4000)
}

const out = `captures/fiche-fix-4/map-${label}__${idu}.png`
await page.screenshot({ path: out })
console.log('✓', out)
// dump l'état des couches de sélection pour diagnostic
const diag = await page.evaluate(() => {
  const w = window
  const maps = w.__mapForDiag
  return maps ? 'map exposée' : 'no diag hook'
}).catch(() => 'eval ko')
console.log('diag:', diag)
await browser.close()
