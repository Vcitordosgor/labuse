// FILTRE-NETTOYAGE — captures du panneau Filtre (avant/après selon LABEL).
// Usage : LABEL=apres BASE=http://127.0.0.1:8000/socle/ node qa/filtre-nettoyage/captures.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const LABEL = process.env.LABEL || 'apres'
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } })
page.setDefaultTimeout(30000)
try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  // ouvrir la section Filtres du panneau gauche
  await page.locator('[data-filtres-toggle]').click().catch(() => {})
  await page.waitForTimeout(800)
  // sélectionner quelques communes pour montrer la forme courte « 12/24 »
  const cps = page.locator('[data-communes-filtre] button')
  const n = await cps.count()
  for (let i = 0; i < Math.min(12, n); i++) await cps.nth(i).click().catch(() => {})
  await page.waitForTimeout(600)
  const panel = page.locator('[data-communes-filtre]').locator('xpath=ancestor::div[contains(@class,"overflow")][1]')
  const target = (await panel.count()) ? panel.first() : page.locator('body')
  await target.screenshot({ path: `${OUT}/panneau-${LABEL}.png` }).catch(async () => {
    await page.screenshot({ path: `${OUT}/panneau-${LABEL}.png`, fullPage: false })
  })
  console.log(`📸 panneau-${LABEL} — sections 1–4`)
  // #5 — le bloc d'actions (Voir / Analyser / Réinitialiser regroupés)
  const reset = LABEL === 'apres' ? '[data-reinitialiser]' : '[data-appel], .border-danger-line'
  await page.locator(reset).first().scrollIntoViewIfNeeded().catch(() => {})
  await page.waitForTimeout(400)
  const appel = page.locator('[data-appel]')
  if (await appel.count()) await appel.first().screenshot({ path: `${OUT}/actions-${LABEL}.png` }).catch(() => {})
  console.log(`📸 actions-${LABEL} — bloc d'actions`)
  // textual assertions (après uniquement)
  if (LABEL === 'apres') {
    const body = await page.locator('body').innerText()
    const checks = {
      'commune 12/24 (forme courte)': /\b12\/24\b/.test(body),
      'Succession dans les signaux': /Succession/.test(body),
      'section « Le bien »': /Le bien/.test(body),
      'phrase zonage retirée': !/Une famille = toutes ses zones/.test(body),
      'plus de « X communes sur 24 »': !/communes sur 24/.test(body),
    }
    for (const [k, v] of Object.entries(checks)) console.log(`  ${v ? '✓' : '✗'} ${k}`)
  }
} catch (e) {
  console.error('ÉCHEC:', String(e).slice(0, 300))
  await page.screenshot({ path: `${OUT}/ZZ-echec-${LABEL}.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
