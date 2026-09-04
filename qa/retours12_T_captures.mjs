// RETOURS-12 — recette navigateur du LOT T (base réelle, backend :8000, /socle/, auth locale off).
// Preuve T1 (référence courte BW0917 → désambiguïsation), + captures T3 (rail), T4 (en-têtes
// collants), T6 (chips au survol). Lancer depuis frontend/ pour résoudre `playwright`.
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-12/captures'
fs.mkdirSync(OUT, { recursive: true })

const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const results = {}
async function shot(name) { await page.screenshot({ path: `${OUT}/${name}.png` }); console.log('  shot', name) }

try {
  // ── T1 — Étudier un bien : référence cadastrale courte BW0917 → liste de désambiguïsation ──
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
  // ouvrir le tiroir Outils puis l'outil « Étudier un bien »
  await page.click('[data-rail="outils"]')
  await page.waitForTimeout(400)
  await page.click('[data-outil="scoreur-adresse"]')
  await page.waitForTimeout(600)
  const champ = page.locator('[data-etudier-adresse]')
  await champ.fill('BW0917')
  await champ.press('Enter')
  await page.waitForTimeout(1200)
  const cands = page.locator('[data-parcelinput-candidat]')
  const n = await cands.count()
  results.T1_candidats = n
  results.T1_communes = []
  for (let i = 0; i < n; i++) results.T1_communes.push((await cands.nth(i).innerText()).replace(/\s+/g, ' ').trim())
  await shot('T1-etudier-BW0917-desambiguisation')

  // T1 — forme alternative « BW 917 » (normalisation) doit rendre la même chose
  await champ.fill('')
  await champ.fill('BW 917')
  await champ.press('Enter')
  await page.waitForTimeout(1000)
  results.T1_candidats_forme2 = await page.locator('[data-parcelinput-candidat]').count()

  // ── T3/T4/T6 — Communes : table « 24 communes » (en-tête collant, survol) ──
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await page.click('[data-rail="outils"]'); await page.waitForTimeout(300)
  const communesBtn = page.locator('[data-outil="communes"]')
  if (await communesBtn.count()) { await communesBtn.click(); await page.waitForTimeout(1200); await shot('T4-communes-table') }

  // ── Rail visible sur plusieurs vues (T3) ──
  await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(500)
  await shot('T3-rail-carte')
  await page.click('[data-rail="crm"]').catch(() => {}); await page.waitForTimeout(800)
  await shot('T3-rail-crm')
} catch (e) {
  results.erreur = String(e)
} finally {
  results.pageerrors = errors.slice(0, 20)
  fs.writeFileSync(`${OUT}/T-recette.json`, JSON.stringify(results, null, 2))
  console.log(JSON.stringify(results, null, 2))
  await browser.close()
}
