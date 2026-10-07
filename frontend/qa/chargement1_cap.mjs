// CHARGEMENT-1 — captures des 4 écrans EN CHARGEMENT (indicateur unique = points menthe) + le gate
// « ordinateur seulement » sur téléphone et iPad simulés. On FORCE l'état de chargement en retardant
// (~15 s) l'endpoint clé de chaque écran (route Playwright), on ATTEND que l'indicateur apparaisse
// (les gros chunks mettent quelques secondes à se charger), puis on capture pendant le délai.
import { chromium, devices } from 'playwright'

const BASE = 'http://127.0.0.1:6050/socle/'
const OUT = '../captures/chargement1/'   // relatif au CWD (frontend/) → repo/captures/chargement1
const IDU = '97402000AB0003'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// L'indicateur unique visible HORS du coin carte (= le loader de l'écran lui-même).
const LOADER_ECRAN = () =>
  [...document.querySelectorAll('.labuse-dot')].some((d) => !d.closest('[data-carte-loading]'))

const br = await chromium.launch({ channel: 'chrome', headless: true })

async function fraisPage(device) {
  const ctx = await br.newContext(device ?? { viewport: { width: 1460, height: 950 }, deviceScaleFactor: 2 })
  const p = await ctx.newPage(); p.on('pageerror', () => {})
  return { ctx, p }
}
async function entrer(p) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false })
  if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1200)
}
const retarder = (p, re, ms = 15000) =>
  p.route(re, async (route) => { await sleep(ms); route.continue().catch(() => {}) })

// 1) FICHE PARCELLE
{
  const { ctx, p } = await fraisPage()
  await entrer(p)
  await retarder(p, /\/parcels\/97402000AB0003/)
  await p.evaluate((i) => window.__labuse.select(i), IDU)
  await p.waitForFunction(() => /Chargement de la fiche/.test(document.body.innerText), { timeout: 20000 })
  await sleep(300)
  await p.screenshot({ path: `${OUT}1_fiche_parcelle.png` })
  console.log('1 fiche parcelle — loader écran :', await p.evaluate(LOADER_ECRAN))
  await ctx.close()
}

// 2) FICHE COMMUNE (contexte)
{
  const { ctx, p } = await fraisPage()
  await entrer(p)
  await retarder(p, /\/communes\/[^/]+\/contexte/)
  await p.evaluate(() => window.__labuse.setContexteCommune('Saint-Paul'))
  await p.waitForFunction(() => !!document.querySelector('[data-contexte-panel] .labuse-dot'), { timeout: 20000 })
  await sleep(300)
  await p.screenshot({ path: `${OUT}2_fiche_commune.png` })
  console.log('2 fiche commune — loader panneau :', !!(await p.$('[data-contexte-panel] .labuse-dot')))
  await ctx.close()
}

// 3) UN OUTIL (Communes — comparateur)
{
  const { ctx, p } = await fraisPage()
  await entrer(p)
  await retarder(p, /\/communes(\?|$)/)
  await p.evaluate(() => { window.__labuse.setView('cartes'); window.__labuse.setModule('communes') })
  await p.waitForFunction(LOADER_ECRAN, { timeout: 20000 })
  await sleep(300)
  await p.screenshot({ path: `${OUT}3_outil_communes.png` })
  console.log('3 outil communes — loader écran :', await p.evaluate(LOADER_ECRAN))
  await ctx.close()
}

// 4) BILAN (écran de calcul — modèle en chargement)
{
  const { ctx, p } = await fraisPage()
  await entrer(p)
  await p.evaluate(() => window.__labuse.setView('documents'))
  await p.waitForSelector('text=Générer le bilan', { timeout: 12000 }).catch(() => {})
  await p.getByRole('button', { name: /^Bilan/ }).first().click({ timeout: 8000 })
  await p.waitForSelector('[role=dialog]', { timeout: 6000 })
  const champ = p.locator('[role=dialog] input').first()
  await champ.fill(IDU); await champ.press('Enter')
  await p.waitForFunction(() => {
    const b = document.querySelector('[role=dialog] button')
    return [...document.querySelectorAll('[role=dialog] button')].some((x) => /Générer le bilan/i.test(x.textContent || '') && !x.disabled)
  }, { timeout: 15000 })
  await retarder(p, /\/bilan\/[^/]+\/modele/)
  await p.getByRole('button', { name: /Générer le bilan/i }).first().click()
  await p.waitForFunction(() => /Chargement du bilan/.test(document.body.innerText), { timeout: 15000 })
  await sleep(300)
  await p.screenshot({ path: `${OUT}4_bilan.png` })
  console.log('4 bilan — loader modèle :', /Chargement du bilan/.test(await p.evaluate(() => document.body.innerText)))
  await ctx.close()
}

// 5) GATE ordinateur — TÉLÉPHONE simulé
{
  const { ctx, p } = await fraisPage(devices['iPhone 13'])
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForSelector('[data-ecran-ordinateur]', { timeout: 15000 })
  await sleep(400)
  await p.screenshot({ path: `${OUT}5_gate_telephone.png` })
  const txt = await p.evaluate(() => document.body.innerText)
  console.log('5 téléphone — gate :', /disponible sur ordinateur/.test(txt), '| app NON montée :', !(await p.evaluate(() => !!window.__labuse)))
  await ctx.close()
}

// 6) GATE ordinateur — iPad simulé
{
  const ipad = devices['iPad (gen 7)'] ?? devices['iPad Pro 11']
  const { ctx, p } = await fraisPage(ipad)
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForSelector('[data-ecran-ordinateur]', { timeout: 15000 })
  await sleep(400)
  await p.screenshot({ path: `${OUT}6_gate_ipad.png` })
  console.log('6 iPad — gate :', /disponible sur ordinateur/.test(await p.evaluate(() => document.body.innerText)))
  await ctx.close()
}

await br.close()
console.log('— captures dans captures/chargement1/')
