// RECETTE-12 A — PROBE (reproduction) du garde Financier. Front :5199 (/socle/), API :8031.
// Objectif : constater en VRAI navigateur si, bailleur 5500 persisté, on atteint « Questionnaire
// enregistré » avec « Ouvrir le Dossier financier » actif. On NE corrige pas ici — on reproduit.
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/captures-recette-12/', import.meta.url).pathname
const IDU = '97411000EL0157'

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 200)) })
const wait = (ms) => page.waitForTimeout(ms)
const shot = async (name) => { await page.screenshot({ path: `${OUT}${name}.png` }); console.log('CAPTURE', name) }
const seen = async (re) => (await page.content()).match(re) ? 'OUI' : 'non'

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await page.evaluate((i) => window.__labuse.select(i), IDU)
await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }).catch(() => {})
await wait(1200)

// ouvrir le Financier
await page.click('[data-banquier-btn]').catch(() => {})
await page.waitForSelector('[data-financier-questionnaire]', { timeout: 10000 }).catch(() => {})
await wait(400)
// choisir construction si l'écran 0 est là
if (await page.$('[data-usage="construction"]')) { await page.click('[data-usage="construction"]'); await wait(600) }

const nEcrans = await page.evaluate(() => {
  const btns = document.querySelectorAll('[data-financier-etapes] [data-etape]')
  return btns.length
})
console.log('N écrans =', nEcrans)

// SCÉNARIO 1 : cliquer « Continuer » écran par écran, observer si ça bloque
console.log('--- SCÉNARIO 1 : Continuer pas-à-pas ---')
for (let i = 0; i < (nEcrans || 4) + 1; i++) {
  const etapeTxt = await page.locator('[data-financier-questionnaire] h2').first().textContent().catch(() => '?')
  const cont = await page.$('button:has-text("Continuer")')
  const enr = await page.$('button:has-text("Enregistrer")')
  console.log(`écran affiché="${etapeTxt}" · Continuer=${!!cont} · Enregistrer=${!!enr}`)
  if (enr) {
    await enr.click(); await wait(900)
    console.log('  → clic Enregistrer · garde surlignée=', await seen(/data-financier-garde/),
      '· fini(Questionnaire enregistré)=', await seen(/Questionnaire enregistré/),
      '· bouton doc=', await seen(/data-financier-doc/))
    break
  }
  if (cont) { await cont.click(); await wait(700) }
  else break
}
await shot('A-probe-scenario1-fin')

// SCÉNARIO 2 : sauter directement au DERNIER écran via la barre d'étapes, puis Enregistrer
console.log('--- SCÉNARIO 2 : saut barre d’étapes → Enregistrer ---')
await page.evaluate(() => {
  const btns = document.querySelectorAll('[data-financier-etapes] [data-etape]')
  if (btns.length) btns[btns.length - 1].click()
})
await wait(500)
const enr2 = await page.$('button:has-text("Enregistrer")')
console.log('sur dernier écran · Enregistrer=', !!enr2)
if (enr2) { await enr2.click(); await wait(900) }
console.log('  → garde surlignée=', await seen(/data-financier-garde/),
  '· fini=', await seen(/Questionnaire enregistré/),
  '· bouton doc=', await seen(/data-financier-doc/))
await shot('A-probe-scenario2-fin')

// état final : capture le contenu clé
const finiMaintenant = await seen(/Questionnaire enregistré/)
console.log('RÉSULTAT : atteint « Questionnaire enregistré » =', finiMaintenant)

await browser.close()
console.log('DONE')
