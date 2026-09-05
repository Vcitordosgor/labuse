// RETOURS-13 Lot 2 — recette navigateur + captures (R10-R18), états de survol compris.
// PHASE=avant|apres. Lancer depuis frontend/ (copie locale).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-13/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })
const shot = async (name) => { await page.screenshot({ path: `${OUT}/${name}-${SUFFIX}.png` }); console.log('  shot', name, SUFFIX) }
const outil = async (key) => {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  await page.click('[data-rail="outils"]')
  await page.waitForTimeout(500)
  await page.click(`[data-outil="${key}"]`)
  await page.waitForTimeout(1200)
}

// ── R10 — menu « Toute l'île » : survol de « voir la fiche → » (jaune) ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await page.getByRole('button', { name: /Toute l/ }).first().click()
await page.waitForTimeout(700)
const ficheBtns = page.locator('[data-fiche-commune]')
if (await ficheBtns.count()) {
  await ficheBtns.nth(4).hover()
  await page.waitForTimeout(400)
}
await shot('R10-communes-voir-fiche-hover')
await page.keyboard.press('Escape')

// ── R11/R13 — outil Communes : tableau 24 communes (survol ligne + Fiche →) ──
await outil('communes')
await page.click('[data-communes-porte="comparaison"]').catch(() => page.click('button:has-text("Comparaison communes")'))
await page.waitForTimeout(2500)
const rows = page.locator('[data-o6-row]')
if (await rows.count()) { await rows.nth(2).hover(); await page.waitForTimeout(300) }
await shot('R11-communes-table-survol')
// survol du « Fiche → » de la même ligne
const ficheSpan = rows.nth(2).locator('text=Fiche →')
if (await ficheSpan.count()) { await ficheSpan.hover(); await page.waitForTimeout(300) }
await shot('R11-communes-fiche-hover')
await shot('R13-24communes-modale')
await page.keyboard.press('Escape').catch(() => {})
await page.mouse.click(30, 860)
await page.waitForTimeout(500)

// ── R13 — évolution du marché (modale en grand) + R12 (bloc Radar) ──
await outil('communes')
await page.click('button:has-text("Évolution du marché")')
await page.waitForTimeout(3000)
await shot('R13-evolution-modale')
await page.mouse.click(30, 860)
await page.waitForTimeout(400)

// ── R14 — acquisitions : Voir plus + chips d'années ──
await outil('communes')
await page.click('button:has-text("Acquisitions récentes")')
await page.waitForTimeout(700)
await page.selectOption('[data-acq-commune]', { label: 'Saint-Paul' }).catch(async () => {
  await page.selectOption('[data-acq-commune]', { index: 14 })
})
await page.waitForTimeout(3500)
await shot('R14-acquisitions')

// ── R15 — écran d'entrée PLU : survol carte « Annuaire PLU » ──
await outil('plu')
const voie = page.locator('[data-plu-voie]').first()
if (await voie.count()) { await voie.hover(); await page.waitForTimeout(400) }
await shot('R15-plu-entree-hover')

// ── R16/R18 — Scan patrimoine : chips exemples (survol) puis liste repliée ──
await outil('patrimoine')
const ex = page.locator('[data-scan-exemple]').first()
if (await ex.count()) { await ex.hover(); await page.waitForTimeout(400) }
await shot('R16-scan-exemples-hover')
// R18 : résoudre CBO → bandeau + bouton, liste repliée ?
await page.click('[data-scan-exemple="nom"]').catch(() => {})
await page.waitForTimeout(3000)
await shot('R18-scan-apres-resolution')
const voirParcelles = page.locator('[data-scan-voir-parcelles]')
if (await voirParcelles.count()) {
  await voirParcelles.click()
  await page.waitForTimeout(1500)
  await shot('R18-scan-liste-ouverte')
}

// ── R17 — SIREN bleu souligné (fiche du scan : le SIREN est dans l'encart) ──
await shot('R17-scan-siren')

console.log('erreurs page:', JSON.stringify(errors.slice(0, 8)))
await browser.close()
