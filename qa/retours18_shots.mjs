// RETOURS-18 — captures accordéon panneau Permis, trois états × deux hauteurs (900 / 560).
// PHASE=avant|apres. Lancer depuis frontend/ : CHROME=<exe> PHASE=apres node ../qa/retours18_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-18/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const errors = []

// panneau = les 320 px de gauche ; on capture l'aside entier (accordéon + total).
const capPanel = async (page, name) => {
  // remettre l'accordéon et la liste EN HAUT (le clic Playwright fait défiler l'élément visé) —
  // on veut l'état d'ouverture réel, pas un défilement d'artefact.
  await page.evaluate(() => {
    document.querySelectorAll('[data-permis-accordeon], [data-permis-bloc="liste"] .overflow-y-auto')
      .forEach((el) => { el.scrollTop = 0 })
  })
  await page.waitForTimeout(200)
  const el = await page.$('aside')
  if (el) { await el.screenshot({ path: `${OUT}/${name}-${SUFFIX}.png` }); console.log('  panel', name) }
}
const openBloc = async (page, id) => {
  const b = await page.$(`[data-permis-bloc-toggle="${id}"]`)
  // n'ouvrir que s'il est replié (aria-expanded=false)
  if (b) { const exp = await b.getAttribute('aria-expanded'); if (exp !== 'true') { await b.click(); await page.waitForTimeout(1200) } }
}

for (const H of [900, 560]) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: H }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => errors.push(`${H}: ${e}`))
  page.on('console', (m) => { if (m.type() === 'error') errors.push(`${H} console: ${m.text()}`) })
  await page.goto(`${BASE}?r18=${H}#m=permis`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  // état 1 — « Filtrer par état » (ouvert par défaut)
  await capPanel(page, `etat-${H}`)
  // état 2 — « Affiner »
  await openBloc(page, 'affiner')
  await capPanel(page, `affiner-${H}`)
  // état 3 — « Voir les permis » (liste pleine hauteur, défilement propre)
  await openBloc(page, 'liste')
  await capPanel(page, `liste-${H}`)
  await ctx.close()
}

fs.writeFileSync(`${OUT}/_errors-${SUFFIX}.txt`, errors.join('\n') || 'aucune')
console.log('ERREURS:', errors.length)
await browser.close()
