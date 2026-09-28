// KELFONCIER-FIX-2 / FICHE-FIX-4 — capture directe (node playwright) du panneau fiche par section.
// Le MCP navigateur expire à 5 s sur la carte WebGL ; on capture ICI l'élément .fiche-v6 seul.
// Usage : node scripts/kelfix-capture.mjs '<label>' 'idu:tiroir' 'idu:tiroir' ...
//   tiroir = id de tiroir (terrain, bati…) → capture l'élément .fiche-v6 avec ce tiroir ouvert.
//   tiroir = 'full' → capture le VIEWPORT entier (carte + chrome app + fiche), tiroir laissé fermé.
//   ex : node scripts/kelfix-capture.mjs avant-F 97411000BZ1065:terrain 97415000AB0134:full
// Sortie : captures/fiche-fix-4/<label>__<idu>__<tiroir>.png
import pkg from '/Users/openclaw/Desktop/labuse-kelfix/frontend/node_modules/playwright-core/index.js'
const { chromium } = pkg

const BASE = 'http://localhost:5745/socle/'
const [, , label, ...pairs] = process.argv
if (!label || pairs.length === 0) { console.error('args: <label> idu:tiroir ...'); process.exit(2) }

const browser = await chromium.launch({
  executablePath: process.env.HOME + '/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
})
const page = await browser.newPage({ viewport: { width: 1400, height: 1200 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('  [console.error]', m.text().slice(0, 200)) })

for (const pair of pairs) {
  const [idu, tiroir] = pair.split(':')
  await page.goto(`${BASE}#f=1&idu=${idu}`, { waitUntil: 'domcontentloaded' })
  // sélectionne la parcelle + ouvre le tiroir voulu via le store zustand (import dev vite).
  await page.evaluate(async ({ idu, tiroir }) => {
    const m = await import('/socle/src/store/useApp.ts')
    const s = m.useApp.getState()
    s.setView('cartes'); s.select(idu)
    if (tiroir) s.setFicheTiroir(idu, tiroir)
    // révèle le verdict à la demande (les sections commencent sur un bouton « Demander l'analyse »)
    try { s.revelerVerdict(idu) } catch { /* pas de verdict à la demande sur cette build */ }
  }, { idu, tiroir })
  await page.waitForSelector('.fiche-v6', { timeout: 15000 })
  const full = tiroir === 'full'
  // fiche chargée (react-query) ET tiroir ouvert : le corps .t-open n'existe qu'alors.
  if (tiroir && !full) await page.waitForSelector(`[data-drawer="${tiroir}"] .t-open`, { timeout: 15000 }).catch(() => {})
  // en mode 'full', laisser le vol (800 ms) + le chargement des tuiles à destination se poser.
  if (full) { await page.waitForSelector('[data-drawer]', { timeout: 15000 }).catch(() => {}); await page.waitForTimeout(4500) }
  await page.waitForTimeout(1500)
  // l'ouverture du tiroir fait un scrollIntoView(block:'start') qui glisse l'en-tête du tiroir SOUS
  // l'en-tête collant de la fiche (~110 px) → le verdict est masqué. On remonte le scroll d'autant.
  if (tiroir && !full) await page.evaluate((tiroir) => {
    const el = document.querySelector(`[data-drawer="${tiroir}"]`)
    let p = el?.parentElement
    while (p && p.scrollHeight <= p.clientHeight) p = p.parentElement
    if (p) p.scrollTop = Math.max(0, p.scrollTop - 120)
  }, tiroir).catch(() => {})
  await page.waitForTimeout(300)
  const out = `captures/fiche-fix-4/${label}__${idu}__${tiroir}.png`
  if (full) await page.screenshot({ path: out })
  else await page.locator('.fiche-v6').screenshot({ path: out })
  console.log('✓', out)
}

await browser.close()
