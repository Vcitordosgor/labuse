// ETUDE-PLAFOND-1 (point 3) — CE QUE L'ÉCRAN AFFICHE pendant un calcul long (> 30 s).
// On déclenche une analyse (Saint-André) et on capture l'OVERLAY de calcul `data-etude-calcul`
// tel qu'il est AUJOURD'HUI : la roue « Calcul en cours, jusqu'à une minute ». Aucun changement
// d'écran — simple constat, capture à l'appui.
import pw from '/Users/openclaw/labuse-restore-k/node_modules/playwright-core/index.js'
const { webkit } = pw
const OUT = 'docs/audit-2026-11/etude-plafond-1'
const BASE = 'http://localhost:6170/socle/'   // vite lie ::1, pas 127.0.0.1
const log = (...a) => console.log('[cap]', ...a)
const SANDRE = ['97409000AX0255', '97409000AX0256']

async function main() {
  const b = await webkit.launch()
  const page = await (await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })).newPage()
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1200)

  // wizard jusqu'à l'analyse
  await page.evaluate((ids) => window.__labuse.ouvrirEtude(ids), SANDRE)
  await page.waitForSelector('[data-etude-parcelle-row]', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(1200)
  await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(500)
  await page.click('[data-etude-type="social"]'); await page.waitForTimeout(1500)
  await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(1200)
  for (const [t, n] of [['T2', 8], ['T3', 6], ['T1', 4]]) { const i = page.locator(`[data-etude-count="${t}"]`); await i.fill(String(n)); await i.dispatchEvent('input'); await page.waitForTimeout(150) }

  // ANALYSE : on lance puis on capture l'overlay de calcul PENDANT qu'il tourne.
  await page.getByRole('button', { name: /Analyser mon projet/ }).click()
  await page.waitForSelector('[data-etude-calcul]', { timeout: 10000 })
  await page.waitForTimeout(1500)   // laisse l'overlay bien posé (> 30 s n'y change rien : même écran)
  const texte = (await page.locator('[data-etude-calcul]').innerText().catch(() => '')).replace(/\s+/g, ' ').trim()
  log('texte de l\'overlay d\'attente :', JSON.stringify(texte))
  await page.screenshot({ path: `${OUT}/01-ecran-attente-calcul.png` })
  log('shot 01-ecran-attente-calcul')

  // on laisse l'analyse aboutir proprement (ne pas tuer le processus serveur en plein calcul)
  await page.waitForSelector('[data-recit], [data-variante-absente]', { timeout: 120000 }).catch(() => {})
  await b.close()
  log('TERMINÉ')
}
main().catch((e) => { console.error(String(e).slice(0, 300)); process.exit(1) })
