// Score V (Phase 4) — captures Playwright 375 / 768 / 1440 (mandat §7) :
//   1. fiche parcelle avec le panneau « Pourquoi ce score » OUVERT (une Brûlante 🔥 si possible)
//   2. vue liste triée par V décroissant (badges V + 🔥 + brûlantes visibles)
//   3. vue carte avec badges (liseré Brûlantes + pastille V au zoom)
// Usage : BASE=http://127.0.0.1:8010/socle/ OUT=../reports/score-v/screenshots node qa/score_v_shots.mjs
// Prérequis : labuse api lancée, parcel_v_score peuplée. L'IDU cible est lu en SQL (une
// Brûlante de la commune de test), pas codé en dur.
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../reports/score-v/screenshots'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// Une Brûlante (sinon la plus forte V des chaudes) + sa commune — cible des captures.
const row = sql(`
  SELECT p.commune || '|' || p.idu FROM parcel_v_score v
  JOIN parcels p ON p.idu = v.parcelle_id
  JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = 'q_v2'
  WHERE d.matrice_statut = 'chaude' AND v.v_score IS NOT NULL
  ORDER BY v.v_score DESC LIMIT 1`)
const [COMMUNE, IDU] = row.split('|')
console.log(`cible : ${IDU} (${COMMUNE})`)

const failures = []
const assert = (cond, name) => {
  if (cond) console.log(`  ✓ ${name}`)
  else { failures.push(name); console.log(`  ✗ ${name}`) }
}

const browser = await chromium.launch()
for (const width of [1440, 768, 375]) {
  const height = width === 375 ? 780 : 900
  const page = await browser.newPage({ viewport: { width, height } })
  page.on('console', (m) => { if (m.type() === 'error') console.log(`  [console:${width}] ${m.text()}`) })

  // 1) LISTE triée V (mode commune, verdict affiché)
  await page.goto(`${BASE}#f=1&v=1&c=${encodeURIComponent(COMMUNE)}`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForSelector('text=chaudes', { timeout: 30000 })
  await page.waitForTimeout(2500)
  assert(await page.locator('text=triés par V').first().isVisible().catch(() => false),
    `tri par défaut V visible @${width}`)
  await page.screenshot({ path: `${OUT}/liste_triee_v_${width}.png` })

  // 2) FICHE avec panneau « Pourquoi ce score » ouvert
  await page.goto(`${BASE}#f=1&v=1&c=${encodeURIComponent(COMMUNE)}`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(1500)
  await page.evaluate((idu) => { window.location.hash = `#f=1&v=1&c=${encodeURIComponent('__C__')}&p=${idu}` }, IDU)
  // sélection directe via la recherche (l'omnibox ouvre la fiche par IDU)
  const box = page.locator('[data-omnibox]')
  if (await box.count()) {
    await box.fill(IDU)
    await box.press('Enter')
    await page.waitForTimeout(2500)
  }
  const scoreV = page.locator('[data-score-v]').first()
  assert(await scoreV.isVisible().catch(() => false), `bloc Vendabilité visible @${width}`)
  await scoreV.click().catch(() => {})           // déplie « Pourquoi ce score »
  await page.waitForTimeout(600)
  assert(await page.locator('text=POURQUOI CE SCORE').first().isVisible().catch(() => false),
    `panneau signaux ouvert @${width}`)
  await page.screenshot({ path: `${OUT}/fiche_panneau_v_${width}.png` })

  // 3) CARTE zoomée sur la parcelle (badges V / liseré Brûlante)
  await page.keyboard.press('Escape')
  await page.waitForTimeout(800)
  await page.screenshot({ path: `${OUT}/carte_badges_v_${width}.png` })
  await page.close()
}
await browser.close()
console.log(failures.length ? `✗ ${failures.length} échec(s) : ${failures.join(', ')}` : '✓ captures OK')
process.exit(failures.length ? 1 : 0)
