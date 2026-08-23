// #1 — le geste manquant : « Créer une veille sur cette recherche » depuis les FILTRES, puis la veille
// remonte au volet Critères (même niveau que Parcelles/Secteurs). BASE=http://localhost:5174/socle/
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'
const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome' })
const page = await br.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)
let ok = true
try {
  // filtre NON-opinion (surface) → nActifs>0 sans allumer l'analyse (le compteur + bouton restent visibles)
  await page.goto('about:blank')
  await page.goto(BASE + '#f=1&smin=1000', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1000)
  // ouvrir le tiroir Filtres si replié
  if ((await page.locator('[data-filtres-toggle]').getAttribute('aria-expanded')) !== 'true')
    await page.locator('[data-filtres-toggle]').click()
  const tous = page.getByText('Tous les filtres', { exact: false })
  if (await tous.count()) await tous.first().click().catch(() => {})
  await page.waitForSelector('[data-creer-veille]', { state: 'visible', timeout: 15000 })
  const btn = await page.locator('[data-creer-veille]').innerText()
  console.log('(a) bouton présent :', JSON.stringify(btn))
  // amener le bouton dans le viewport et cadrer le bas des filtres (compteur + bouton)
  await page.locator('[data-creer-veille]').scrollIntoViewIfNeeded()
  await page.waitForTimeout(400)
  await page.screenshot({ path: `${OUT}/01-bouton-veille-filtres.png` })   // viewport : bouton en contexte, bas des filtres
  console.log('📸 01-bouton-veille-filtres.png')

  // clic → crée la veille + ouvre Veille › Critères
  await page.locator('[data-creer-veille]').click()
  await page.waitForSelector('[data-volet-criteres]', { state: 'visible', timeout: 10000 })
  await page.waitForTimeout(800)
  // les 3 volets au même niveau (pills) + la veille créée listée
  const volets = await page.locator('[data-volet]').allInnerTexts()
  const criteresActif = await page.locator('[data-volet="criteres"]').count()
  const veilles = await page.locator('[data-volet-criteres] a[href^="/socle/"]').count()
  console.log('(b) volets (même niveau) :', volets.join(' · '), '· critères listés :', veilles)
  if (btn.indexOf('veille') < 0 || criteresActif !== 1) ok = false
  await page.locator('[data-surveillance-panel]').screenshot({ path: `${OUT}/02-veille-criteres.png` }).catch(async () => { await page.screenshot({ path: `${OUT}/02-veille-criteres.png` }) })
  console.log('📸 02-veille-criteres.png')
  console.log(ok ? '\n✅ #1 OK' : '\n❌ #1 : assertion échouée')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 400))
  await page.screenshot({ path: `${OUT}/zz-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await br.close()
}
