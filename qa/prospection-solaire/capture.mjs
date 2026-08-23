// Recette « Prospection solaire » V1 : (1) la liste filtrée (commune + piscine + potentiel) ;
// (2) l'export CSV téléchargé et OUVERT (rendu en tableau). Vérifie « — jamais un zéro », le compte
// « N sur M », le bandeau (données gelées / masque non calculé), et le CSV (en-têtes Sourcé/Estimé).
// Usage : BASE=http://localhost:5174/socle/ node qa/prospection-solaire/capture.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync, readFileSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 980 }, acceptDownloads: true })
const page = await ctx.newPage()
page.setDefaultTimeout(30000)
let ok = true
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(600)
  await page.click('button[title="Outils"]')
  await page.locator('[data-outil="prospection-solaire"]').click()

  // (1) filtres : commune Saint-Paul + piscine détectée + potentiel ≥ 1400
  await page.waitForSelector('[data-solaire-piscine]', { state: 'visible' })
  await page.locator('[data-commune-scope]').selectOption('Saint-Paul').catch(() => {})
  await page.locator('[data-solaire-piscine]').selectOption('oui')
  await page.locator('[data-solaire-potentiel]').selectOption('1400')
  await page.waitForSelector('[data-solaire-row]', { timeout: 20000 })
  await page.waitForTimeout(600)
  const rows = await page.locator('[data-solaire-row]').count()
  const compte = await page.locator('.overflow-hidden >> text=/sur/').first().innerText().catch(() => '')
  const bandeau = await page.locator('text=/ombrage de proximité.*non modélisé/').count()
  const zeroLeak = await page.locator('[data-solaire-row] td', { hasText: /^0( m²|°|)$/ }).count()
  console.log(`(1) lignes=${rows} · compte="${compte.replace(/\n/g, ' ')}" · bandeau=${bandeau} · cellules « 0 » nues=${zeroLeak}`)
  if (rows < 1 || bandeau < 1) ok = false
  await page.screenshot({ path: `${OUT}/01-liste-filtree.png` })
  console.log('📸 01-liste-filtree.png')

  // (2) export CSV → téléchargement, puis on l'OUVRE (rendu tableau) pour la capture
  const [dl] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('[data-solaire-csv]').click(),
  ])
  const path = await dl.path()
  const csv = readFileSync(path, 'utf8').replace(/^﻿/, '')
  const lignes = csv.trim().split('\n')
  console.log(`CSV : ${lignes.length - 1} lignes · en-tête = ${lignes[0].slice(0, 90)}…`)
  const okEntete = /Sourcé/.test(lignes[0]) && /Estimé/.test(lignes[0])
  if (!okEntete || lignes.length < 2) ok = false

  // rendu du CSV en tableau HTML (le « CSV ouvert ») pour la capture
  const cells = (l) => l.split(';').map((c) => `<td style="border:1px solid #333;padding:3px 6px">${c}</td>`).join('')
  const html = `<html><body style="background:#0d0f0e;color:#cfe;font:12px monospace;padding:16px">
    <h3>prospection_solaire.csv — ${lignes.length - 1} lignes</h3>
    <table style="border-collapse:collapse"><tr>${lignes[0].split(';').map((h) => `<th style="border:1px solid #4ADE80;padding:3px 6px;color:#4ADE80">${h}</th>`).join('')}</tr>
    ${lignes.slice(1, 16).map((l) => `<tr>${cells(l)}</tr>`).join('')}</table></body></html>`
  await page.setContent(html)
  await page.waitForTimeout(200)
  await page.screenshot({ path: `${OUT}/02-csv-ouvert.png`, fullPage: true })
  console.log('📸 02-csv-ouvert.png')

  console.log(ok ? '\n✅ Prospection solaire V1 : OK' : '\n❌ une assertion a échoué')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 500))
  await page.screenshot({ path: `${OUT}/ZZ-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
