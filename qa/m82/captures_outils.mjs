// M82 Phase 1 — captures « après » des outils : mauve→vert, scroll Rareté résolu, mots coupés
// Comparateur résolus, Baromètre sans effondrement, bouton Matching sur une ligne.
// Usage : BASE=http://127.0.0.1:8000/socle/ node qa/m82/captures_outils.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')
const OUT = new URL('./captures/outils-' + STAMP, import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)
const shot = async (name, note) => {
  await page.waitForTimeout(700)
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
  console.log(`  📸 ${name} — ${note}`)
}
const ouvrir = async (key) => {
  // s'assurer que le tiroir Outils est ouvert, puis cliquer la carte
  const drawer = page.locator('[data-outil-group]').first()
  if (!(await drawer.isVisible().catch(() => false))) await page.locator('button[title="Outils"]').click()
  await page.locator(`[data-outil="${key}"]`).click()
  await page.waitForTimeout(1200)
}

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.locator('button[title="Outils"]').click()
  await page.locator('[data-outil-group]').first().waitFor()
  await shot('00-page-outils', 'page Outils — accents VERTS (plus de mauve), 3 groupes')

  await ouvrir('scoring-v2'); await shot('01-radar', 'Radar des mutations — ×N et UI en vert, badge copro neutre')
  await ouvrir('o9-rarete'); await shot('02-rarete', 'Rareté — pas de scroll horizontal, colonnes ajustées')
  await ouvrir('o6-comparateur'); await shot('03-comparateur', 'Comparateur — libellés de pondération courts, aucun mot coupé')
  await ouvrir('barometre'); await shot('04-barometre', 'Baromètre — 1er trimestre = 2025T4 (plus d\'effondrement 2026T3)')
  await ouvrir('matching'); await shot('05-matching', 'Matching — bouton RÉEL·SITADEL sur une ligne')
  await ouvrir('division'); await shot('06-division', 'Division — score vert, plus de « (SQL) » au compteur')

  console.log('\nCaptures →', OUT)
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 300))
  await page.screenshot({ path: `${OUT}/ZZ-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
