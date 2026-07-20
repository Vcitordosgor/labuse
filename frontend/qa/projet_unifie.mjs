// PROJET UNIFIÉ (PJ3+PJ8) — captures des 5 lots sur les vraies données de Vic.
// L1 kanban · L2 drag&drop (+ CRM synchro) · L3 tri Tinder branché · L4 fiches + dédup.
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/socle/'
const API = 'http://127.0.0.1:8010'
const OUT = '../../reports/post-validation/captures-projet'
const NOM = 'Résidence étudiante Saint-Paul'
const wait = (p, ms) => p.waitForTimeout(ms)
const txt = async (loc) => (await loc.innerText()).replace(/\s+/g, ' ').trim()

const b = await chromium.launch()
const page = await b.newPage({ viewport: { width: 1360, height: 880 } })
const errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()) })

async function fresh() {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 15000 })
}
async function openKanban() {
  await page.evaluate(() => window.__labuse.setView('projets'))
  await page.waitForSelector('[data-projets-liste]', { timeout: 10000 })
  const card = page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
  await card.locator('[data-projet-ouvrir]').click()
  await page.waitForSelector('[data-projet-kanban]', { timeout: 15000 })
  await page.waitForSelector('[data-kanban-card]', { timeout: 15000 })
  await wait(page, 800)
}
const ONLY = process.env.ONLY || ''
async function step(name, fn) {
  if (ONLY && !name.includes(ONLY)) return
  try { await fn(); console.log(`OK  ${name}`) }
  catch (e) { console.log(`ERR ${name}: ${String(e).split('\n')[0]}`) }
}

// ── L4 — la LISTE en fiches (mini-compteurs) ──
await step('L4 fiches', async () => {
  await fresh()
  await page.evaluate(() => window.__labuse.setView('projets'))
  await page.waitForSelector('[data-projet-compteurs]', { timeout: 10000 })
  await wait(page, 500)
  await page.screenshot({ path: `${OUT}/L4-fiches.png` })
  console.log('   compteurs Saint-Paul:', await txt(page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}")) [data-projet-compteurs]`)))
})

// ── L1 — la vue kanban unifiée ──
await step('L1 kanban', async () => {
  await fresh(); await openKanban()
  const c = (k) => txt(page.locator(`[data-kanban-count="${k}"]`))
  console.log('   À trier / Retenues / Écartées:', await c('proposee'), '/', await c('retenue'), '/', await c('ecartee'))
  await page.screenshot({ path: `${OUT}/L1-kanban.png` })
})

// ── L2 — drag & drop À trier → Retenues (+ CRM synchro) ──
await step('L2 drag&drop', async () => {
  await fresh(); await openKanban()
  const propBefore = await txt(page.locator('[data-kanban-count="proposee"]'))
  const retBefore = await txt(page.locator('[data-kanban-count="retenue"]'))
  await page.screenshot({ path: `${OUT}/L2-dnd-before.png` })
  const card = page.locator('[data-kanban-col="proposee"] [data-kanban-card]').first()
  const idu = await card.getAttribute('data-kanban-card')
  // CRM avant
  const crmBefore = await (await fetch(`${API}/pipeline`)).json()
  const inCrmBefore = crmBefore.some((e) => e.idu === idu)
  // drag natif HTML5 (Playwright dispatche les bons events)
  await card.dragTo(page.locator('[data-kanban-col="retenue"]'))
  await wait(page, 1500)
  const propAfter = await txt(page.locator('[data-kanban-count="proposee"]'))
  const retAfter = await txt(page.locator('[data-kanban-count="retenue"]'))
  await page.screenshot({ path: `${OUT}/L2-dnd-after.png` })
  const crmAfter = await (await fetch(`${API}/pipeline`)).json()
  const inCrmAfter = crmAfter.some((e) => e.idu === idu)
  console.log(`   ${idu} : À trier ${propBefore}→${propAfter} · Retenues ${retBefore}→${retAfter}`)
  console.log(`   CRM (pipeline) : avant ${inCrmBefore} → après ${inCrmAfter} (synchro auto)`)
})

// ── L3 — tri Tinder branché : Trier les N → décisions → Quitter → kanban à jour ──
await step('L3 tri branché', async () => {
  await fresh(); await openKanban()
  const retBefore = await txt(page.locator('[data-kanban-count="retenue"]'))
  await page.locator('[data-kanban-trier]').click()
  await page.waitForSelector('[data-decision-card]', { timeout: 15000 })
  await wait(page, 2000)
  await page.screenshot({ path: `${OUT}/L3-tinder.png` })
  await page.locator('[data-decision-retenir]').click(); await wait(page, 900)
  await page.locator('[data-decision-ecarter]').click(); await wait(page, 900)
  // Quitter → doit revenir sur le KANBAN (pas la liste)
  await page.locator('[data-parcours-quitter]').click()
  await page.waitForSelector('[data-projet-kanban]', { timeout: 10000 })
  await wait(page, 1200)
  const retAfter = await txt(page.locator('[data-kanban-count="retenue"]'))
  await page.screenshot({ path: `${OUT}/L3-retour-kanban.png` })
  console.log(`   retour du tri → kanban ; Retenues ${retBefore}→${retAfter} (reflète le tri)`)
})

// ── L4 dédup — entretien aux critères d'un projet existant → « Projet identique repris » ──
await step('L4 dédup', async () => {
  await fresh()
  await page.evaluate(() => window.__labuse.setView('ia'))
  await page.waitForSelector('[data-porte-recherche] input', { timeout: 10000 })
  await page.fill('[data-porte-recherche] input', 'logements étudiants à Saint-Paul')
  await page.click('[data-decrire-projet]')
  await page.waitForSelector('[data-entretien-lancer]', { timeout: 30000 })
  await wait(page, 500)
  await page.click('[data-entretien-lancer]')
  await page.waitForSelector('[data-projet-enregistrer]', { timeout: 25000 })
  await page.click('[data-projet-enregistrer]')
  await page.waitForSelector('[data-projet-enregistre]', { timeout: 15000 })
  await wait(page, 600)
  await page.locator('[data-ia-restitution]').screenshot({ path: `${OUT}/L4-dedup.png` })
  console.log('   état enregistrement:', await txt(page.locator('[data-projet-enregistre]')))
})

console.log(`\nconsole errors: ${errs.length}`)
if (errs.length) console.log(errs.slice(0, 6).join('\n'))
await b.close()
console.log('captures projet unifié terminées')
