// ETUDE-FIABLE-1 — captures « après » du parcours Étude. WebKit (build 2104 compatible mac13).
import pw from '/Users/openclaw/labuse-restore-k/node_modules/playwright-core/index.js'
const { webkit } = pw
const OUT = 'docs/audit-2026-11/etude-fiable-1/captures'
const BASE = 'http://127.0.0.1:6170/socle/'
const log = (...a) => console.log('[cap]', ...a)

async function main() {
  const b = await webkit.launch()
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
  const page = await ctx.newPage()
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 })
  await page.waitForTimeout(1200)
  const shot = (n) => page.screenshot({ path: `${OUT}/${n}.png`, fullPage: true }).then(() => log('shot', n))
  const ouvrir = async (ids) => { await page.evaluate((i) => window.__labuse.ouvrirEtude(i), ids); await page.waitForTimeout(900) }
  const valide = async () => { await page.waitForSelector('[data-etude-parcelle-row], .text-coral', { timeout: 20000 }).catch(() => {}); await page.waitForTimeout(1200) }
  const continuer = async () => { await page.getByRole('button', { name: /Continuer/ }).first().click(); await page.waitForTimeout(500) }
  const type = async (k) => { await page.click(`[data-etude-type="${k}"]`); await page.waitForTimeout(1600) }
  const setCount = async (t, n) => { const i = page.locator(`[data-etude-count="${t}"]`); await i.fill(String(n)); await i.dispatchEvent('input'); await page.waitForTimeout(150) }
  const analyser = async () => { await page.getByRole('button', { name: /Analyser mon projet/ }).click(); await page.waitForSelector('[data-recit], [data-variante-absente]', { timeout: 90000 }).catch(() => {}); await page.waitForTimeout(2500) }
  const recharge = async () => { await page.reload({ waitUntil: 'domcontentloaded' }); await page.waitForFunction(() => window.__labuse && window.__labuse.ouvrirEtude, null, { timeout: 30000 }); await page.waitForTimeout(1000) }

  // 01 — L'Étang-Salé : compteur 27 (C3/R4) + « meilleure capacité trouvée » (C1)
  await ouvrir(['97404000AW0099', '97404000AW0451', '97404000AW0624', '97404000AW0625'])
  await valide(); await continuer(); await type('social'); await continuer()
  await page.waitForTimeout(1500); await setCount('T2', 23); await setCount('T3', 6)
  await analyser(); await shot('01-etang-sale-apres-compteur27-meilleure-capacite')
  await recharge()

  // 02 — Saint-André : résultat avec « meilleure capacité trouvée » (C1)
  await ouvrir(['97409000AX0255', '97409000AX0256'])
  await valide(); await continuer(); await type('social'); await continuer()
  await page.waitForTimeout(1500); await setCount('T2', 8); await setCount('T3', 6); await setCount('T1', 4)
  await analyser(); await shot('02-saint-andre-apres-meilleure-capacite')

  await b.close(); log('TERMINÉ')
}
main().catch((e) => { console.error(String(e).slice(0, 300)); process.exit(1) })
