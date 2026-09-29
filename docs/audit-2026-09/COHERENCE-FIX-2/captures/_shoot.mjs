// COHERENCE-FIX-2 — captures fiche / Marché / Étude de zone sur 3 témoins.
// Pilote la sélection par le hook d'auto-QA window.__labuse (aucun effet produit).
import pkg from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright-core/index.js'
const { chromium } = pkg

const BASE = 'http://localhost:5895/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-coherence2/docs/audit-2026-09/COHERENCE-FIX-2/captures'
const EXE = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const TEMOINS = [
  ['97411000BZ1065', 'Saint-Denis'],
  ['97415000EO0796', 'Saint-Pierre'],
  ['97402000AB1117', 'Bras-Panon'],
]
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await chromium.launch({ executablePath: EXE })
const ctx = await b.newContext({ viewport: { width: 1440, height: 1600 }, deviceScaleFactor: 1 })
const page = await ctx.newPage()

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => (window).__labuse && (window).__labuse.select, null, { timeout: 20000 })

for (const [idu, ville] of TEMOINS) {
  console.log(`témoin ${idu} (${ville})`)
  await page.evaluate((i) => (window).__labuse.select(i), idu)
  // attend l'overlay fiche puis son CONTENU réel (le bloc « LE MARCHÉ » lazy) — retry select si vide
  let ready = false
  for (let attempt = 0; attempt < 3 && !ready; attempt++) {
    await page.waitForSelector('.fiche-v6', { timeout: 15000 }).catch(() => {})
    ready = await page.locator('.fiche-v6').getByText('LE MARCHÉ', { exact: false }).first().count()
      .then((n) => n > 0).catch(() => false)
    if (!ready) { await page.evaluate((i) => (window).__labuse.select(i), idu); await sleep(3500) }
  }
  await sleep(2500)
  const fiche = page.locator('.fiche-v6').first()
  await fiche.screenshot({ path: `${OUT}/${idu}_1_fiche.png` }).catch((e) => console.log('  fiche:', String(e).slice(0, 60)))
  // Marché : ouvre le tiroir en cliquant sa ligne (le libellé « Marché »), puis capture le détail
  const marcheRow = page.locator('.fiche-v6').getByText('Marché', { exact: true }).first()
  if (await marcheRow.count()) {
    await marcheRow.scrollIntoViewIfNeeded().catch(() => {})
    await marcheRow.click().catch(() => {})
    await sleep(2000)
  }
  const marche = page.locator('#marche, [data-ref-id="marche"], .fiche-v6').first()
  await marche.screenshot({ path: `${OUT}/${idu}_2_marche.png` }).catch((e) => console.log('  marché:', String(e).slice(0, 60)))
  // Étude de zone (mon-secteur) : ouvre l'outil, capture le panneau
  await page.evaluate(() => (window).__labuse.setModule && (window).__labuse.setModule('mon-secteur'))
  await sleep(3000)
  const panel = page.locator('[data-module-panel], .module-panel, aside').last()
  await (await panel.count() ? panel : page).screenshot({ path: `${OUT}/${idu}_3_etude_zone.png` }).catch((e) => console.log('  étude:', String(e).slice(0, 60)))
  await page.evaluate(() => (window).__labuse.setModule && (window).__labuse.setModule(null))
  await sleep(800)
}
await b.close()
console.log('done')
