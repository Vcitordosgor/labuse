// M13 LOT F — captures de preuve. Playwright chromium (frontend/node_modules/playwright).
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8035/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-a56790ef359b5a0b7/qa/m13/F'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('console', (m) => { if (m.type() === 'error') console.log('  [console.error]', m.text()) })

async function goto(hash = '') {
  await page.goto(BASE + hash, { waitUntil: 'networkidle' })
  await sleep(1200)
}

// ── F1 + F2 : page Sources ────────────────────────────────────────────────
await goto()
// clic sur l'entrée « Sources » du rail
await page.getByText('Sources', { exact: true }).first().click().catch(() => {})
await sleep(1500)
await page.waitForSelector('[data-sources-page]', { timeout: 8000 })
await page.waitForSelector('[data-source-row]', { timeout: 8000 })
await page.screenshot({ path: `${OUT}/f1_sources.png`, fullPage: true })
console.log('✓ f1_sources.png')
// F2 : même page, prouve l'ABSENCE du bloc « Ce que LABUSE mesure »
const preuveGone = await page.locator('[data-sources-preuve]').count()
const blocText = await page.getByText('Ce que LABUSE mesure').count()
console.log(`  F2 : data-sources-preuve=${preuveGone} · texte « Ce que LABUSE mesure »=${blocText} (attendu 0/0)`)
await page.screenshot({ path: `${OUT}/f2_sources_sans_bloc.png`, fullPage: true })
console.log('✓ f2_sources_sans_bloc.png')

// ── F3 : barre de tri ─────────────────────────────────────────────────────
// page neuve pour F3/F4 : repart d'un état propre (évite tout report de la vue Sources).
await page.close()
const page2 = await ctx.newPage()
page2.on('console', (m) => { if (m.type() === 'error') console.log('  [console.error]', m.text()) })
await page2.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
await sleep(3000)
await page2.waitForSelector('[data-sort="rang"]', { timeout: 15000, state: 'attached' })
await page2.waitForSelector('[data-mult-tip]', { timeout: 15000, state: 'attached' }).catch(() => {})
await sleep(1000)
// (le reste du bloc F3 utilise `page2`)
const pageF3 = page2
// 1er résultat sous tri « classement »
const first = async () => (await pageF3.locator('[data-mult-tip]').first().textContent().catch(() => '∅')) ?? '∅'
const firstRang = await first()
// bascule sur « mutation ×N »
await pageF3.locator('[data-sort="mult"]').click()
await sleep(900)
const firstMult = await first()
// options présentes / commune absente
const sorts = await pageF3.locator('[data-sort]').evaluateAll((els) => els.map((e) => e.getAttribute('data-sort')))
const communeGone = await pageF3.locator('[data-sort="commune"]').count()
console.log(`  F3 : options de tri = [${sorts.join(', ')}] · commune=${communeGone} (attendu 0)`)
console.log(`  F3 : 1er (classement)=«${firstRang}» → 1er (mutation ×N)=«${firstMult}»`)
await pageF3.screenshot({ path: `${OUT}/f3_tri.png`, clip: { x: 0, y: 0, width: 480, height: 900 } })
console.log('✓ f3_tri.png')

// ── F4 : Scoreur d'adresse (Outils) ───────────────────────────────────────
await pageF3.goto(BASE, { waitUntil: 'networkidle' })
await sleep(1200)
await pageF3.getByText('Outils', { exact: true }).first().click().catch(() => {})
await sleep(1000)
await pageF3.getByText('Scorer une adresse', { exact: true }).first().click().catch(() => {})
await sleep(1200)
await pageF3.waitForSelector('[data-scoreur-panel]', { timeout: 8000 })
await pageF3.screenshot({ path: `${OUT}/f4_scoreur.png`, fullPage: false })
console.log('✓ f4_scoreur.png')
// autocomplétion ouverte
const addr = pageF3.locator('[data-scoreur-panel] input').first()
await addr.click().catch(() => {})
await addr.type('12 rue', { delay: 60 }).catch(() => {})
await sleep(2000)
await pageF3.screenshot({ path: `${OUT}/f4_scoreur_autocomplete.png`, fullPage: false })
console.log('✓ f4_scoreur_autocomplete.png')

await browser.close()
console.log('DONE')
