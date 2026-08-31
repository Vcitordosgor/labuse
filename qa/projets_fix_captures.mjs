// PROJETS-FIX — captures de recette. Sert le build sous /socle/ (uvicorn :8000, auth locale off).
// Projets en base : 237 (île · pm_privée, vivier 21 273) · 238 (Saint-Denis, vivier 862)
//                   235 (de_zero → état vide F4 « Ajouter des parcelles ») · 236 (zone UB absente → F4 « aucune parcelle »).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = 'docs/PROJETS-FIX/captures'
fs.mkdirSync(OUT, { recursive: true })
const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const wait = (ms) => page.waitForTimeout(ms)
async function shot(name) { await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false }); console.log('  shot', name) }
async function projets() {
  await page.goto(BASE, { waitUntil: 'networkidle' }); await wait(700)
  await page.locator('button[title="Projets"]').click(); await wait(900)
}
async function openRow(hasText) {
  await page.locator('[data-projet-row]', { hasText }).first().click(); await wait(1200)
}
async function openExact(title) {   // 235 « LABUSE TEST » est un préfixe de 237 → titre EXACT
  await page.locator('[data-projet-row]', { has: page.getByText(title, { exact: true }) }).first().click(); await wait(1200)
}

// F3 — ACCUEIL : cartes (titre + étiquette périmètre + « vivier N classé · valeurs · budget » + barre + RETENUES)
await projets()
await shot('01-accueil-F3')

// F2 — PROJET OUVERT pleine largeur (vivier 21 273, kanban 3 colonnes 1.35/1/0.8)
await openRow('LABUSE TEST 2')
await shot('02-kanban-F2-vivier21273')
const vivier237 = await page.locator('[data-kanban-vivier]').first().innerText().catch(() => '')
const colCount = await page.locator('[data-kanban-col]').count()

// F2 bis — le projet Saint-Denis (vivier 862)
await projets(); await openRow('LABUSTRE TEST 3')
await shot('03-kanban-F2-saintdenis862')

// F4 — état vide « projet de zéro » (235 LABUSE TEST)
await projets(); await openExact('LABUSE TEST')
await wait(600)
const deZero = await page.locator('[data-empty-de-zero]').count()
await shot('04-vide-de-zero-F4')

// F4 — état vide « cadrage sans résultat » (236 LABUSTRE TEST 2, zone UB absente de Saint-Denis)
await projets(); await openRow('LABUSTRE TEST 2')
await wait(600)
const cadrageVide = await page.locator('[data-empty-cadrage-vide]').count()
await shot('05-vide-cadrage-F4')

// F1 — WIZARD : le récap affiche le VRAI vivier (r.vivier), plus le total gonflé
await projets()
await page.locator('[data-projet-nouveau]').click(); await wait(500)
await page.locator('[data-projet-porte="vivier"]').click(); await wait(400)
await page.locator('input[data-projet-nom]').first().fill('RECETTE ÎLE').catch(() => {})
await page.locator('[data-projet-suivant]').click(); await wait(300)   // → périmètre
await page.locator('[data-projet-ile]').click(); await wait(300)
await page.locator('[data-projet-suivant]').click(); await wait(300)   // → contexte
await page.locator('[data-projet-suivant]').click(); await wait(300)   // → cadrage
await page.locator('[data-projet-suivant]').click(); await wait(5000)  // → récap (charge le compteur)
const recap = await page.locator('[data-recap-vivier]').innerText().catch(() => '')
await shot('06-wizard-recap-vivier-F1')

// MAQUETTE de référence — §03 (projet ouvert) et §04 (accueil), pour comparaison côte à côte
await page.goto('file://' + process.cwd() + '/docs/maquettes/projets-v3.html', { waitUntil: 'networkidle' })
await wait(500)
await page.locator('h2:has-text("Le projet ouvert")').scrollIntoViewIfNeeded().catch(() => {})
await wait(300); await shot('07-maquette-03-projet-ouvert')
await page.locator('h2:has-text("accueil ajusté")').scrollIntoViewIfNeeded().catch(() => {})
await wait(300); await shot('08-maquette-04-accueil')

const report = { vivier237, colCount, deZero, cadrageVide, recap, errors }
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
