// ETUDE-FIABLE-1 (point 2) — capture « rouvrir une étude » : on ANALYSE une fois (crée la révision),
// puis on ROUVRE via la MÊME action que la bibliothèque (ouvrirEtude(idus, config)) → la révision
// s'affiche SANS relancer le moteur (aucun POST /modules/etude pendant la réouverture), même n° EF.
import pw from '/Users/openclaw/labuse-restore-k/node_modules/playwright-core/index.js'
const { webkit } = pw
const OUT = 'docs/audit-2026-11/etude-fiable-1/captures'
const BASE = 'http://localhost:6170/socle/'   // vite lie ::1 (localhost), pas 127.0.0.1
const log = (...a) => console.log('[cap]', ...a)
const SANDRE = ['97409000AX0255', '97409000AX0256']
const CONFIG = { idus: SANDRE, type_projet: 'social', objectif: 'equilibre', stationnement: 'aerien',
  programme: { mode: 'saisi', lignes: [{ type: 'T2', nombre: 8 }, { type: 'T3', nombre: 6 }, { type: 'T1', nombre: 4 }] } }

async function main() {
  const b = await webkit.launch()
  const page = await (await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })).newPage()
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1200)

  // On CAPTURE la config EXACTE que le front envoie à l'analyse (POST /modules/etude). C'est CELLE que
  // la bibliothèque archive (documents_generes.hypotheses.config) et rejoue à la réouverture : rouvrir
  // avec ce corps = exactement le geste « rouvrir depuis Mes documents ». (CONFIG reste un repli.)
  let corpsAnalyse = null
  page.on('request', (r) => {
    try {
      const p = new URL(r.url()).pathname
      if (r.method() === 'POST' && /\/modules\/etude$/.test(p)) corpsAnalyse = JSON.parse(r.postData() || 'null')
    } catch { /* ignore */ }
  })

  // 1) ANALYSE normale (crée la révision + archive) → on lit le n° EF affiché.
  await page.evaluate((ids) => window.__labuse.ouvrirEtude(ids), SANDRE)
  await page.waitForSelector('[data-etude-parcelle-row]', { timeout: 20000 }).catch(() => {})
  await page.waitForTimeout(1200)
  await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(500)
  await page.click('[data-etude-type="social"]'); await page.waitForTimeout(1500)
  await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(1200)
  for (const [t, n] of [['T2', 8], ['T3', 6], ['T1', 4]]) { const i = page.locator(`[data-etude-count="${t}"]`); await i.fill(String(n)); await i.dispatchEvent('input'); await page.waitForTimeout(150) }
  await page.getByRole('button', { name: /Analyser mon projet/ }).click()
  await page.waitForSelector('[data-recit], [data-variante-absente]', { timeout: 90000 }).catch(() => {})
  await page.waitForTimeout(2000)
  const numAnalyse = await page.locator('[data-num-doc]').first().textContent().catch(() => '')
  log('n° après analyse :', (numAnalyse || '').trim())

  // 2) FERMER, puis ROUVRIR via la même action que la bibliothèque (ouvrirEtude(idus, config)).
  //    On rouvre avec le corps EXACT capturé (= config archivée) ; repli sur CONFIG si non capturé.
  //    On ESPIONNE le réseau : aucun POST /modules/etude (analyse) ne doit partir à la réouverture
  //    (la réouverture appelle /modules/etude/revision-par-config, qui n'est PAS une analyse).
  const cfgRouvrir = corpsAnalyse || CONFIG
  log('rouvre avec la config', corpsAnalyse ? 'CAPTURÉE (front)' : 'repli CONFIG')
  await page.evaluate(() => window.__labuse.fermerEtude && window.__labuse.fermerEtude())
  await page.waitForTimeout(500)
  const posts = []
  page.on('request', (r) => { if (r.method() === 'POST' && /\/modules\/etude$/.test(new URL(r.url()).pathname)) posts.push(r.url()) })
  await page.evaluate((cfg) => window.__labuse.ouvrirEtude(cfg.idus, cfg), cfgRouvrir)
  // la révision s'affiche sans recalcul : on attend le résultat (recit) ou le bouton Relancer.
  await page.waitForSelector('[data-recit], [data-etude-relancer]', { timeout: 30000 }).catch(() => {})
  await page.waitForTimeout(2500)
  const numRouvert = await page.locator('[data-num-doc]').first().textContent().catch(() => '')
  log('n° après réouverture :', (numRouvert || '').trim())
  log('POST /modules/etude pendant la réouverture :', posts.length, '(doit être 0)')
  await page.screenshot({ path: `${OUT}/03-saint-andre-rouvert-bibliotheque.png`, fullPage: true })
  log('shot 03-saint-andre-rouvert-bibliotheque')

  await b.close()
  log('TERMINÉ')
}
main().catch((e) => { console.error(String(e).slice(0, 300)); process.exit(1) })
