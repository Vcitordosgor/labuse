// M13 LOT E — captures de preuve (E1, E2, E3).
// Base http://127.0.0.1:8034/socle/ · build servi depuis frontend/dist de CE worktree.
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8034/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-af62c131e12fa9682/qa/m13/E'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } })
const page = await ctx.newPage()
page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERR:', m.text()) })

async function openProjets() {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await sleep(600)
  await page.locator('button[title="Projets"]').first().click()
  await sleep(800)
}

// ─── E1 : « À trier » PEUPLÉE juste après le lancement de la recherche ───
// On ouvre le projet E1-PREUVE (créé côté API, VIDE avant ouverture). Le parcours de « Lancer la
// recherche » persiste projet + propose : à l'arrivée dans la vue 3 colonnes, « À trier » est pleine.
async function e1() {
  await openProjets()
  // ouvrir le projet « E1-PREUVE » depuis la liste (clic sur son nom)
  await page.locator('[data-projet-nom]', { hasText: 'E1-PREUVE' }).first().click()
  // attendre que « À trier » soit peuplée (compteur > 0)
  await page.waitForFunction(() => {
    const c = document.querySelector('[data-kanban-count="proposee"]')
    return c && Number(c.textContent) > 0
  }, { timeout: 15000 })
  await sleep(600)
  const n = await page.locator('[data-proposee-row]').count()
  console.log('E1 · rangs À trier visibles:', n)
  await page.screenshot({ path: `${OUT}/e1_a_trier_peuplee.png` })
}

// ─── E2 : la PHRASE remplace « + Chercher plus » ───
async function e2() {
  // toujours dans le kanban : vérifier absence du bouton + présence de la phrase
  const btn = await page.locator('[data-kanban-chercher]').count()
  const phrase = await page.locator('[data-kanban-enrichir]').first().textContent()
  console.log('E2 · bouton chercher (attendu 0):', btn, '| phrase:', JSON.stringify(phrase))
  // cadrer le header (phrase visible)
  const header = page.locator('[data-projet-kanban] > div').first()
  await header.screenshot({ path: `${OUT}/e2_phrase.png` })
}

await e1()
await e2()

await browser.close()
console.log('DONE E1+E2')
