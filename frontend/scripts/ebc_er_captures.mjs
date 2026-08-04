/**
 * Dette #10 — captures de revue EBC / ER (drapeaux d'information sur la fiche).
 *
 * PRÉREQUIS (opérateur, cf. express01_captures.mjs) :
 *   API  : LABUSE_DEV_MODE=1 PYTHONPATH=src ~/miniforge3/envs/labusedb/bin/python \
 *            -m uvicorn labuse.api.app:app --lifespan off
 *   Front: cd frontend && npm run dev
 * LANCEMENT (depuis frontend/) :
 *   PHASE=apres node scripts/ebc_er_captures.mjs      # avec le badge (working tree)
 *   PHASE=avant node scripts/ebc_er_captures.mjs      # sans le badge (Fiche.tsx stashé)
 *
 * Pilotage via window.__labuse (App.tsx). Capture l'aside fiche entière pour chaque parcelle
 * réelle du run servi. Best-effort : repli pleine page si un sélecteur manque.
 */
import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'

const BASE = process.env.BASE_URL || 'http://localhost:5173/socle/'
const PHASE = process.env.PHASE || 'apres'
const OUT = process.env.OUT || path.resolve('..', 'reports', 'train-tech', 'ebc_er')
const STEP_TIMEOUT = Number(process.env.STEP_TIMEOUT || 15000)
// Parcelles réelles du run servi q_v8_calibre :
//  - EBC + ER (deux badges)         : 97418000AT1740 (EBC ~26 %, ER sans n°)
//  - ER numéroté (« n°26 »)         : 97407000AI1886
const CIBLES = [
  ['ebc_er', process.env.IDU_EBC_ER || '97418000AT1740'],
  ['er_numero', process.env.IDU_ER_NUM || '97407000AI1886'],
]
const log = (...a) => console.log('[ebc_er]', ...a)

async function main() {
  await mkdir(OUT, { recursive: true })
  const browser = await chromium.launch({ headless: true, channel: 'chrome' })
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })
  const page = await context.newPage()
  page.on('console', (m) => { if (m.type() === 'error') log('page-error:', m.text().slice(0, 120)) })
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => !!window.__labuse, null, { timeout: STEP_TIMEOUT })
    .catch(() => log('⚠ window.__labuse absent'))

  const results = []
  for (const [nom, idu] of CIBLES) {
    const name = `${PHASE}_${nom}_${idu}`
    try {
      // page fraîche par parcelle : évite un fiche.lines résiduel de la parcelle précédente.
      await page.goto(BASE, { waitUntil: 'networkidle' })
      await page.waitForFunction(() => !!window.__labuse, null, { timeout: STEP_TIMEOUT }).catch(() => {})
      await page.evaluate((idu) => { window.__labuse?.setView('cartes'); window.__labuse?.select(idu) }, idu)
      await page.waitForSelector('[data-fiche-idu]', { timeout: STEP_TIMEOUT })
      // attendre que les lignes de cascade (donc les prescriptions) soient chargées.
      await page.waitForFunction(() => {
        const el = document.querySelector('[data-fiche-idu]')
        return el && document.body.innerText.length > 0
      }, null, { timeout: STEP_TIMEOUT }).catch(() => {})
      await page.waitForTimeout(2800)
      const aside = page.locator('aside:has([data-fiche-idu])').first()
      const file = path.join(OUT, `${name}.png`)
      await aside.screenshot({ path: file })
      const badges = await page.locator('[data-prescriptions-badges]').count()
      results.push({ name, ok: true, badges, file })
      log(`✓ ${file} (blocs badges: ${badges})`)
    } catch (e) {
      const file = path.join(OUT, `${name}__fallback.png`)
      await page.screenshot({ path: file, fullPage: true }).catch(() => {})
      results.push({ name, ok: false, err: String(e).slice(0, 140), file })
      log(`⚠ ${name} échec: ${String(e).slice(0, 90)}`)
    }
  }
  await browser.close()
  log('──── récap', PHASE, '────')
  for (const r of results) log(`${r.ok ? '✓' : '⚠'} ${r.name} badges=${r.badges ?? '-'} ${r.file}`)
}
main().catch((e) => { console.error(e); process.exit(1) })
