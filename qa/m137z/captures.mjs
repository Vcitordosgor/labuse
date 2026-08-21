// M137-Z — captures de la fusion « Communes » (Marché·Comparateur·Vélocité·Rareté) + les 3 corrections.
// Usage : BASE=http://127.0.0.1:8000/socle/ node qa/m137z/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')
const OUT = new URL('./captures/communes-' + STAMP, import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)
const shot = async (name, note) => {
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
  console.log(`  📸 ${name} — ${note}`)
}
const ouvrir = async (key) => {
  const drawer = page.locator('[data-outil-group]').first()
  if (!(await drawer.isVisible().catch(() => false))) await page.locator('button[title="Outils"]').click()
  await page.locator(`[data-outil="${key}"]`).click()
  await page.waitForTimeout(1200)
}

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.locator('button[title="Outils"]').click()
  await page.locator('[data-outil-group]').first().waitFor()

  // 1 — la table des 24 communes (entrée de l'outil « Communes »)
  await ouvrir('communes')
  await page.locator('[data-o6-row]').first().waitFor()
  const nRows = await page.locator('[data-o6-row]').count()
  await shot('01-table-24-communes', `Table des ${nRows} communes — lignes cliquables (→)`)

  // 2 — clic sur la 1ʳᵉ commune → sa fiche (rareté corrigée + vélocité tranche + marché)
  await page.locator('[data-o6-row]').first().click()
  await page.locator('[data-communes-parcelles]').waitFor()
  await shot('02-fiche-commune', 'Fiche commune — rareté (droit à artificialiser + foncier + caveat), vélocité p25–p75, marché')

  // 3 — vérifs textuelles des 3 corrections dans la fiche
  const body = await page.locator('body').innerText()
  const checks = {
    'stock dit « foncier »': /Foncier repéré/i.test(body),
    'reste ZAN = droit à artificialiser': /Droit à artificialiser restant/i.test(body),
    'tranche p25–p75': /tranche p25/i.test(body),
    'bouton Voir ses parcelles': await page.locator('[data-communes-parcelles]').isVisible(),
  }
  for (const [k, v] of Object.entries(checks)) console.log(`  ${v ? '✓' : '✗'} ${k}`)

  // 4 — retour table + Baromètre : « les N premières sur 24 »
  await page.locator('[data-communes-retour]').click()
  await page.waitForTimeout(500)
  await ouvrir('barometre')
  await shot('03-barometre', 'Baromètre — classement prix « les 8 premières sur 24 » (plus de LIMIT muet)')

  console.log('\nCaptures →', OUT)
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 400))
  await page.screenshot({ path: `${OUT}/ZZ-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
