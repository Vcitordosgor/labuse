// OUTILS-1 — captures de recette + vérification A2 (fiche commune ne crashe pas).
// Sert le build sous /socle/ (backend uvicorn :8000, auth désactivée en local).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = 'docs/OUTILS-1/captures'
fs.mkdirSync(OUT, { recursive: true })

const errors = []
const browser = await chromium.launch({
  executablePath: process.env.CHROME,
  headless: true,
})
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

async function go(hash) {
  await page.goto(BASE + hash, { waitUntil: 'networkidle' })
  await page.waitForTimeout(900)
}
async function shot(name) {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
  console.log('  shot', name)
}
// détection d'un crash de rendu (error boundary / overlay vite)
async function crashText() {
  return await page.evaluate(() => {
    const t = document.body.innerText || ''
    for (const s of ['Une erreur est survenue', 'Something went wrong', 'ErrorBoundary',
                      'Cannot read', 'is not a function', 'undefined is not']) {
      if (t.includes(s)) return s
    }
    return null
  })
}

const report = {}

// B1 — accueil (carte Radar + pied « voir les données »)
await go('')
await shot('01-accueil-B1')
report.accueil_radar = await page.locator('text=Suivre le marché — Radar').count()
report.accueil_sources_lien = await page.locator('[data-accueil-sources]').count()

// A1/B8 — taxe : surface 250 RP + piscine 20
await go('#m=taxe-amenagement')
await page.fill('[data-taxe-field="surface"]', '250').catch(() => {})
await page.check('[data-taxe-check="residence"]').catch(() => {})
await page.fill('[data-taxe-field="piscine"]', '20').catch(() => {})
await page.fill('[data-taxe-field="taux-communal"]', '4').catch(() => {})
await page.waitForTimeout(1200)
await shot('02-taxe-A1B8')
report.taxe_lignes = await page.locator('[data-taxe-ligne]').allInnerTexts().catch(() => [])

// A5 — PLU annuaire bandeau
await go('#m=plu')
await page.waitForTimeout(900)
await shot('03-plu-A5')
report.plu_bandeau = await page.locator('[data-plu-biblio] p').first().innerText().catch(() => null)

// A4 — courrier
await go('#m=courriers')
await shot('04-courrier-A4')

// A2 — communes → fiche commune (ne doit pas crasher)
await go('#m=communes')
await page.waitForTimeout(1000)
await shot('05-communes-A2')
// ouvrir la table (bouton « Comparer/Table » si présent), puis cliquer une fiche
const openTable = page.locator('text=Comparer les 24').first()
if (await openTable.count()) { await openTable.click().catch(() => {}); await page.waitForTimeout(800) }
// clic sur la 1re fiche disponible
let clicked = false
for (const sel of ['text=Ouvrir la fiche', 'text=Fiche →', '[data-commune-fiche]', 'text=Saint-Paul']) {
  const el = page.locator(sel).first()
  if (await el.count()) { await el.click().catch(() => {}); clicked = true; break }
}
await page.waitForTimeout(1200)
await shot('06-communes-fiche-A2')
report.fiche_clicked = clicked
report.fiche_crash = await crashText()

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
