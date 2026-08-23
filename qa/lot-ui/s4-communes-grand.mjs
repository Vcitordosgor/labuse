// §4 — la table « Les 24 communes » s'ouvre en SECTION FLOTTANTE plein écran (patron ex-Comparateur).
// Prouve : (a) ouvrir l'outil Communes ouvre la table en grand (overlay) ; (b) cliquer une commune
// ouvre sa FICHE dans le panneau (overlay fermé) ; (c) l'onglet « Évolution » reste DANS le panneau
// (pas d'overlay) ; (d) revenir sur « Les 24 » rouvre l'overlay.
// Usage : BASE=http://localhost:5174/socle/ node qa/lot-ui/s4-communes-grand.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)
const shot = async (n, note) => { await page.waitForTimeout(500); await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`) }
const nOverlay = () => page.locator('[data-communes-table-panel]').count()

let ok = true
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(600)
  await page.click('button[title="Outils"]')
  await page.locator('[data-outil="communes"]').click()

  // (a) la table s'ouvre en grand (overlay plein écran)
  await page.waitForSelector('[data-communes-table-panel]', { state: 'visible', timeout: 15000 })
  await page.locator('[data-o6-row]').first().waitFor({ state: 'visible' })
  const rows = await page.locator('[data-communes-table-panel] [data-o6-row]').count()
  console.log(`(a) overlay table ouvert=${await nOverlay()} · lignes communes=${rows}`)
  if (rows < 20) ok = false
  await shot('s4-01-table-grand', 'les 24 communes en grand (section flottante)')

  // (b) cliquer une commune → fiche DANS le panneau, overlay fermé
  await page.locator('[data-communes-table-panel] [data-o6-row]').first().click()
  await page.waitForSelector('[data-communes-retour]', { state: 'visible', timeout: 10000 })
  await page.waitForSelector('[data-communes-table-panel]', { state: 'detached', timeout: 5000 }).catch(() => {})
  const overlayApresClic = await nOverlay()
  const ficheParcelles = await page.locator('[data-communes-parcelles]').count()
  console.log(`(b) clic commune → fiche (bouton parcelles=${ficheParcelles}) · overlay=${overlayApresClic} (doit=0)`)
  if (overlayApresClic !== 0 || ficheParcelles < 1) ok = false
  await shot('s4-02-fiche-panneau', 'fiche commune DANS le panneau (overlay fermé)')

  // (c) retour à la table (l'overlay se rouvre) → on le FERME (patron modal) → le panneau montre les
  // onglets → « Évolution » s'affiche DANS le panneau (aucun overlay).
  await page.locator('[data-communes-retour]').click()
  await page.waitForSelector('[data-communes-table-panel]', { state: 'visible', timeout: 8000 })
  await page.locator('[data-communes-table-panel] button[aria-label="Fermer"]').click()
  await page.waitForSelector('[data-communes-table-panel]', { state: 'detached', timeout: 5000 }).catch(() => {})
  await page.waitForSelector('[data-communes-vue="evolution"]', { state: 'visible' })
  await page.locator('[data-communes-vue="evolution"]').click()
  await page.waitForTimeout(900)
  const overlayEvol = await nOverlay()
  console.log(`(c) onglet Évolution : overlay=${overlayEvol} (doit=0, reste dans le panneau)`)
  if (overlayEvol !== 0) ok = false
  await shot('s4-03-evolution-panneau', 'onglet Évolution reste dans le panneau (pas d\'overlay)')

  // (d) revenir sur « Les 24 » → l'overlay se rouvre
  await page.locator('[data-communes-vue="table"]').click()
  await page.waitForSelector('[data-communes-table-panel]', { state: 'visible', timeout: 8000 })
  console.log(`(d) retour « Les 24 » → overlay=${await nOverlay()} (doit=1)`)
  if ((await nOverlay()) !== 1) ok = false

  console.log(ok ? '\n✅ §4 Communes en grand : OK' : '\n❌ §4 : au moins une assertion a échoué')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 500))
  await page.screenshot({ path: `${OUT}/s4-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
