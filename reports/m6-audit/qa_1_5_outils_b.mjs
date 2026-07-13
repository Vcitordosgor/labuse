// M6 §1.5 — passe B : inventaire (relisible), scoring-v2, programme, assemblage (API lecture),
// bailleur/promesses avec attentes longues. LECTURE SEULE.
import { createRequire } from 'node:module'
const require = createRequire('/Users/openclaw/Desktop/labuse/frontend/qa/_resolve.js')
const { chromium } = require('playwright')

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/reports/m6-audit/captures-1-5'
const report = {}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
let consoleErrors = []
let netErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + e.message))
page.on('response', (r) => { if (r.status() >= 400) netErrors.push(`${r.status()} ${r.url()}`) })
const drain = () => { const c = [...consoleErrors], n = [...netErrors]; consoleErrors = []; netErrors = []; return { console: c, net: n } }

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 45000 })
await page.waitForTimeout(3000)
drain()

// inventaire
await page.locator('nav button[title="Outils"]').click()
await page.waitForTimeout(500)
report.inventaire = await page.evaluate(() => {
  return [...document.querySelectorAll('[data-outil-group]')].flatMap((g) =>
    [...g.querySelectorAll('[data-outil]')].map((b) => ({
      key: b.getAttribute('data-outil'),
      phare: b.getAttribute('data-outil-phare') === '1',
      groupe: g.getAttribute('data-outil-group'),
      texte: b.textContent.trim().replace(/\s+/g, ' ').slice(0, 130),
    })))
})

async function openTool(key, label) {
  if (!(await page.locator('[data-outil]').first().isVisible().catch(() => false))) {
    await page.locator('nav button[title="Outils"]').click()
    await page.waitForTimeout(400)
  }
  await page.locator(`[data-outil="${key}"]`).click()
  await page.waitForTimeout(1500)
  return (await page.locator('aside h2', { hasText: label }).count()) > 0
}
async function close() { await page.locator('aside button[title="Fermer le module"]').click().catch(() => {}); await page.waitForTimeout(300) }

// scoring-v2
{
  const ok = await openTool('scoring-v2', 'Scoring v2')
  await page.waitForTimeout(2500)
  const rows = await page.locator('aside .overflow-y-auto button').count()
  const avert = await page.locator('aside p.shrink-0').innerText().catch(() => 'ABSENT')
  const errs = drain()
  report.scoringV2 = { ok, brulantesAffichees: rows, avertissement: avert.slice(0, 120), ...errs }
  await page.screenshot({ path: `${OUT}/outil_scoring-v2.png` })
  await close()
}

// programme
{
  const ok = await openTool('programme', 'Faisabilité programme')
  await page.getByRole('button', { name: 'Trouver les parcelles' }).click()
  await page.waitForTimeout(12000)
  const t = await page.locator('text=parcelles candidates').innerText().catch(() => 'ABSENT')
  const crit = await page.locator('text=unités → SDP').innerText().catch(() => 'ABSENT')
  const errs = drain()
  report.programme = { ok, candidates: t, criteres: crit, ...errs }
  await page.screenshot({ path: `${OUT}/outil_programme.png` })
  await close()
}

// bailleur (attente longue — endpoint ~20 s île entière)
{
  const ok = await openTool('bailleur', 'Mode bailleur')
  await page.waitForSelector('text=parcelles promues en QPV', { timeout: 40000 })
  await page.waitForTimeout(1000)
  const t = await page.locator('text=parcelles promues en QPV').innerText().catch(() => 'ABSENT')
  const errs = drain()
  report.bailleur = { ok, compteurUI: t, ...errs }
  await page.screenshot({ path: `${OUT}/outil_bailleur.png` })
  await close()
}

// promesses (attente longue)
{
  const ok = await openTool('promesses', 'Promesses mortes')
  await page.waitForSelector('text=promesses mortes', { timeout: 30000 })
  const t = await page.locator('text=promesses mortes').innerText().catch(() => 'ABSENT')
  const errs = drain()
  report.promesses = { ok, compteurUI: t, ...errs }
  await page.screenshot({ path: `${OUT}/outil_promesses.png` })
  await close()
}

// assemblage : UI ouverte + API en lecture (pattern qa_moteurs — clic carte non fiable en headless)
{
  const ok = await openTool('assemblage', 'Assemblage')
  const asm = await (await fetch(new URL('/moteurs/assemblage', BASE).href, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idus: ['97415000BH0283', '97415000BH0122'] }) })).json()
  report.assemblage = { ok, api: { n: asm.n, contigu: asm.contigu, score: asm.score_assemblage, sdp: asm.sdp_cumulee_m2, tiers: (asm.items || []).map((i) => i.tier_v2 ?? i.statut) } }
  await close()
}

console.log(JSON.stringify(report, null, 2))
await browser.close()
