// communes-tableau — captures : tableau Communes complet (7 colonnes), tri vérifié sur 2 colonnes,
// baromètre allégé (sans « Prix par commune »). Usage : BASE=http://127.0.0.1:8000/socle/ node …
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } })
page.setDefaultTimeout(30000)
const shot = async (n, note) => { await page.waitForTimeout(500); await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`) }
const ouvrir = async (k) => {
  const drawer = page.locator('[data-outil-group]').first()
  if (!(await drawer.isVisible().catch(() => false))) await page.locator('button[title="Outils"]').click()
  await page.locator(`[data-outil="${k}"]`).click(); await page.waitForTimeout(1000)
}
// lit l'ordre des communes sous le tri courant (1re colonne)
const ordre = async () => (await page.locator('[data-o6-row]').allInnerTexts()).map((t) => t.split('\n')[0].trim()).slice(0, 6)
const colVals = async (k) => (await page.locator(`[data-o6-cell="${k}"]`).allInnerTexts()).slice(0, 8)

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.locator('button[title="Outils"]').click()
  await page.locator('[data-outil-group]').first().waitFor()

  await ouvrir('communes')
  await page.locator('[data-o6-row]').first().waitFor()
  const nRows = await page.locator('[data-o6-row]').count()
  const nCols = await page.locator('[data-o6-tri]').count()
  await shot('01-tableau-complet', `${nRows} communes · ${nCols} colonnes triables (défaut = stock ↓)`)

  // TRI #1 — €/m² ancien (décroissant), vérifie que l'ordre change et est bien décroissant
  await page.locator('[data-o6-tri="prix_ancien"]').click(); await page.waitForTimeout(400)
  const ordreAncien = await ordre()
  const valsAncien = (await colVals('prix_ancien')).map((s) => Number(s.replace(/[^\d]/g, '')) || null).filter((v) => v != null)
  const decroissantAncien = valsAncien.every((v, i) => i === 0 || valsAncien[i - 1] >= v)
  await shot('02-tri-ancien', `tri €/m² ancien ↓ — ${ordreAncien[0]} en tête · décroissant=${decroissantAncien}`)

  // TRI #2 — Vélocité, vérifie que l'ordre change encore
  await page.locator('[data-o6-tri="velocite"]').click(); await page.waitForTimeout(400)
  const ordreVelo = await ordre()
  const valsVelo = (await colVals('velocite')).map((s) => Number(s.replace(',', '.').replace(/[^\d.]/g, '')) || null).filter((v) => v != null)
  const decroissantVelo = valsVelo.every((v, i) => i === 0 || valsVelo[i - 1] >= v)
  await shot('03-tri-velocite', `tri Vélocité ↓ — décroissant=${decroissantVelo}`)

  console.log('  tri change l’ordre (ancien≠velo) :', JSON.stringify(ordreAncien) !== JSON.stringify(ordreVelo) ? '✓' : '✗')
  console.log('  €/m² ancien décroissant :', decroissantAncien ? '✓' : '✗')
  console.log('  Vélocité décroissante :', decroissantVelo ? '✓' : '✗')
  const body = await page.locator('body').innerText()
  console.log('  colonnes ancien+neuf présentes :', /€ anc/.test(body) && /€ neuf/.test(body) ? '✓' : '✗')
  console.log('  plus de « Composite » :', !/Composite/i.test(body) ? '✓' : '✗ (encore là)')

  // baromètre allégé
  await ouvrir('barometre'); await page.waitForTimeout(500)
  const baro = await page.locator('body').innerText()
  console.log('  baromètre sans « Prix par commune » :', !/Prix par commune/.test(baro) ? '✓' : '✗')
  console.log('  baromètre garde « DVF par trimestre » :', /trimestre/i.test(baro) ? '✓' : '✗')
  console.log('  baromètre garde « Rapport PDF » :', /Rapport PDF/.test(baro) ? '✓' : '✗')
  await shot('04-barometre-allege', 'baromètre : trimestres + PDF, sans prix par commune')
} catch (e) {
  console.error('ÉCHEC:', String(e).slice(0, 300)); await page.screenshot({ path: `${OUT}/ZZ-echec.png` }).catch(() => {}); process.exitCode = 1
} finally { await browser.close() }
