// §5 — PLU compact : les communes en procédure sont REPLIÉES sous un bandeau cliquable
// « ⚠ N communes en procédure PLU ». Prouve : (a) collapsé par défaut (bandeau, 0 carte visible) ;
// (b) clic → déplie les N cartes, chacune avec type, date et bouton « Simuler ».
// Usage : BASE=http://localhost:5174/socle/ node qa/lot-ui/s5-plu-procedure.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)
const shot = async (n, note) => { await page.waitForTimeout(400); await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`) }

let ok = true
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(600)
  await page.click('button[title="Outils"]')
  await page.locator('[data-outil="plu"]').click()
  await page.locator('[data-plu-voie="procchg"]').click()

  // (a) bandeau replié par défaut : 0 carte visible, le bandeau dit le compte
  await page.waitForSelector('[data-procchg-banner]', { state: 'visible', timeout: 15000 })
  const banner = await page.locator('[data-procchg-banner]').innerText()
  const cartesCollapse = await page.locator('[data-procchg-commune]').count()
  const expandedA = await page.locator('[data-procchg-banner]').getAttribute('aria-expanded')
  const m = banner.match(/(\d+)\s+communes?\s+en\s+procédure/i)
  const n = m ? Number(m[1]) : 0
  console.log(`(a) bandeau="${banner.replace(/\n/g, ' ')}" · N=${n} · cartes visibles=${cartesCollapse} (doit=0) · aria-expanded=${expandedA}`)
  if (n < 1 || cartesCollapse !== 0 || expandedA !== 'false') ok = false
  await shot('s5-01-banner-collapse', 'bandeau replié (compact) — ⚠ N communes en procédure PLU')

  // (b) clic → déplie les N cartes, chacune avec bouton Simuler
  await page.locator('[data-procchg-banner]').click()
  await page.waitForSelector('[data-procchg-commune]', { state: 'visible', timeout: 5000 })
  const cartes = await page.locator('[data-procchg-commune]').count()
  const simuler = await page.locator('[data-procchg-simuler]').count()
  const expandedB = await page.locator('[data-procchg-banner]').getAttribute('aria-expanded')
  const carte0 = await page.locator('[data-procchg-commune]').first().innerText()
  console.log(`(b) déplié : cartes=${cartes} (=N=${n}) · boutons Simuler=${simuler} · aria-expanded=${expandedB}`)
  console.log(`    carte[0] contient type+date+simuler ? "${carte0.replace(/\n/g, ' | ').slice(0, 140)}"`)
  if (cartes !== n || simuler < n || expandedB !== 'true') ok = false
  await shot('s5-02-banner-unfold', 'déplié : les N cartes (type, date, bouton Simuler)')

  console.log(ok ? '\n✅ §5 PLU compact : OK' : '\n❌ §5 : au moins une assertion a échoué')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 500))
  await page.screenshot({ path: `${OUT}/s5-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
