// OUTILS-6 — captures de recette de la fiche commune (accordéons, C1/C2, passerelles).
// Build servi sous /socle/ (uvicorn :8000, auth désactivée en local). CHROME = chromium-1217.
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/OUTILS-6/captures'
fs.mkdirSync(OUT, { recursive: true })

const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log('  shot', n) }
const report = {}

await page.goto(BASE + '#m=communes', { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
// éviter que l'état d'accordéon d'un run précédent (localStorage) fausse la capture « défaut »
await page.evaluate(() => localStorage.removeItem('labuse.fiche.acc'))
await page.click('[data-communes-porte="comparaison"]')
await page.waitForSelector('[data-o6-row]', { timeout: 15000 })
await page.waitForTimeout(600)

// 01 — le comparateur (référence C2 : colonne « ancien » des 24 communes)
report.table_rows = await page.locator('[data-o6-row]').count()
await shot('01-comparateur-table-C2')

// ouvrir la fiche Saint-Paul depuis la table ; attendre que la donnée soit servie (accordéons rendus)
await page.click('[data-o6-row][title="Saint-Paul"]')
await page.waitForSelector('[data-contexte-panel]', { timeout: 10000 })
await page.waitForSelector('[data-acc]', { timeout: 20000 })
await page.waitForTimeout(800)
report.fiche_ouverte = await page.locator('[data-contexte-panel]').count()

// 02 — fiche par défaut (foncier + marché + outils ouverts ; le reste fermé porte son chiffre-clé)
await shot('02-fiche-defaut-accordeons')
report.chiffres_cles = await page.locator('[data-acc-cle]').allInnerTexts().catch(() => [])
report.header = await page.locator('[data-contexte-panel]').innerText().then(t => t.slice(0, 240)).catch(() => null)

// 03 — tous les accordéons ouverts (fiche entière)
const summaries = await page.locator('[data-acc] > summary').all()
for (const s of summaries) { const open = await s.evaluate(el => el.parentElement.open); if (!open) await s.click().catch(() => {}) }
await page.waitForTimeout(500)
await shot('03-fiche-tout-ouvert')
report.zonage = await page.locator('[data-acc="foncier"]').innerText().then(t => {
  const m = [...t.matchAll(/\b([UAN]{1,2})\s+([\d,]+)\s*%/g)].map(x => [x[1], parseFloat(x[2].replace(',', '.'))])
  return { parts: m, somme: Math.round(m.reduce((s, x) => s + x[1], 0) * 10) / 10 }
}).catch(() => null)

// 04 — la section passerelles (outils pré-remplis + compteurs)
await page.locator('[data-acc="outils"]').scrollIntoViewIfNeeded().catch(() => {})
await page.waitForTimeout(300)
await shot('04-fiche-passerelles')
report.passerelles = await page.locator('[data-acc="outils"] [data-passerelle]').allInnerTexts().catch(() => [])

// 05 — une passerelle ouvre l'outil AVEC la commune (Densifier)
const densif = page.locator('[data-acc="outils"] [data-passerelle]', { hasText: 'Densifier' })
if (await densif.count()) {
  await densif.first().click().catch(() => {})
  await page.waitForTimeout(1500)
  report.densifier_ouvre_commune = await page.locator('body').innerText().then(t => t.includes('Saint-Paul')).catch(() => false)
  report.fiche_fermee = (await page.locator('[data-contexte-panel]').count()) === 0
  await shot('05-passerelle-densifier-commune')
}

report.errors = errors.slice(0, 8)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
