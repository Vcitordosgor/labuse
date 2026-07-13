// AUDIT M6 §1.7 — cohérence app ↔ exports (LECTURE SEULE, aucune écriture).
// Lit ce que l'ÉCRAN affiche pour les parcelles témoins (liste brûlantes + fiches),
// capture les écrans, et imprime les valeurs pour comparaison avec les exports.
//
// Usage : node qa/audit_m6_exports.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../reports/m6-audit/exports-samples'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

// ── 1. Liste filtrée « brûlantes » (île entière) : compteur + première ligne ──
await page.goto(BASE + '#f=1&tv=brulante', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.screenshot({ path: `${OUT}/ui_liste_brulantes.png` })
const listText = await page.locator('[data-results], main').first().innerText().catch(() => '')
console.log('--- LISTE brûlantes (extrait écran) ---')
console.log(listText.split('\n').slice(0, 30).join('\n'))

// ── 2. Fiche de la brûlante n°1 (97423000AB1908) via l'omnibox ──
async function ficheDe(idu, shot) {
  await page.locator('[data-omnibox]').fill(idu)
  await page.waitForTimeout(1800)
  // clic sur la suggestion qui porte l'IDU
  const sugg = page.locator(`text=${idu.slice(8)}`).first()
  await sugg.click({ timeout: 8000 }).catch(async () => {
    await page.keyboard.press('Enter')
  })
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/${shot}` })
  const fiche = await page.locator('aside, [data-fiche], main').last().innerText().catch(() => '')
  console.log(`--- FICHE ${idu} (extrait écran) ---`)
  console.log(fiche.split('\n').slice(0, 40).join('\n'))
}
await ficheDe('97423000AB1908', 'ui_fiche_brulante_AB1908.png')
await ficheDe('97421000AV0615', 'ui_fiche_ecartee_AV0615.png')

await browser.close()
console.log('captures →', OUT)
