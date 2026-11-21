// ETUDE-FICHE-1 — captures restantes : sous-sol, lotissement, cas limites.
import pw from '/Users/openclaw/labuse-restore-k/node_modules/playwright-core/index.js'
const { webkit } = pw
const OUT = 'docs/audit-2026-11/etude-fiche-1/captures'
const log = (...a) => console.log('[cap]', ...a)

async function main() {
  const browser = await webkit.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') log('PAGE-ERR', m.text().slice(0, 140)) })
  await page.goto('http://127.0.0.1:10100/socle/', { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1200)

  const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png`, fullPage: true }).then(() => log('shot', n))
  const ouvrir = async (idus) => { await page.evaluate((ids) => window.__labuse.ouvrirEtude(ids), idus); await page.waitForTimeout(900) }
  const valide = async () => { await page.waitForSelector('[data-etude-parcelle-row], .text-coral', { timeout: 20000 }).catch(() => {}); await page.waitForTimeout(1200) }
  const continuer = async () => { await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(500) }
  const type = async (k) => { await page.click(`[data-etude-type="${k}"]`); await page.waitForTimeout(1600) }
  const setCount = async (t, n) => { const i = page.locator(`[data-etude-count="${t}"]`); await i.fill(String(n)); await i.dispatchEvent('input'); await page.waitForTimeout(150) }
  const analyser = async () => {
    await page.getByRole('button', { name: /Analyser mon projet/ }).click()
    await page.waitForSelector('[data-recit], [data-variante-absente]', { timeout: 90000 }).catch(() => {})
    await page.waitForTimeout(2500)
  }
  const recharge = async () => { await page.reload({ waitUntil: 'domcontentloaded' }); await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 }); await page.waitForTimeout(1000) }

  // 13 — SOUS-SOL (Étang-Salé, social). Sous-sol disponible (pas de PPR).
  const ETANG = ['97404000AW0099', '97404000AW0451', '97404000AW0624', '97404000AW0625']
  await ouvrir(ETANG); await valide(); await continuer(); await type('social'); await continuer()
  await page.waitForTimeout(1500)
  await setCount('T2', 10); await setCount('T3', 6)
  const ss = page.locator('[data-statio-etape3="sous_sol"]')
  if (await ss.count() && await ss.isEnabled()) { await ss.click(); await page.waitForTimeout(1200) }
  else log('sous-sol indisponible sur cette assiette')
  await shot('13-type-social-sous-sol-etape3')
  await analyser(); await shot('13-type-social-sous-sol-resultat')
  await recharge()

  // 14-17 — LOTISSEMENT (Saint-Leu AC261+262+264 ; AC263 absent du cadastre)
  const SLEU = ['97413000AC0261', '97413000AC0262', '97413000AC0264']
  await ouvrir(SLEU); await valide(); await shot('14-lotissement-etape1')
  await continuer(); await type('lotissement'); await shot('15-lotissement-etape2')
  await continuer(); await page.waitForTimeout(1200); await shot('16-lotissement-etape3')
  await analyser(); await shot('17-lotissement-resultat')
  await recharge()

  // 20-21 — DÉPASSEMENT (Saint-André, social, T4×60)
  const SANDRE = ['97409000AX0255', '97409000AX0256']
  await ouvrir(SANDRE); await valide(); await continuer(); await type('social'); await continuer()
  await page.waitForTimeout(1500)
  await setCount('T4', 60)
  await page.waitForTimeout(1500) // laisser la jauge « dépassement » s'afficher
  await shot('20-depassement-etape3')
  await analyser(); await shot('21-depassement-resultat')
  await recharge()

  // 22 — PARCELLES NON CONTIGUËS (communes différentes)
  await ouvrir(['97404000AW0099', '97411000DL0247']); await valide()
  await shot('22-non-contigues-etape1')

  await browser.close()
  log('TERMINÉ')
}
main().catch((e) => { console.error(String(e).slice(0, 300)); process.exit(1) })
