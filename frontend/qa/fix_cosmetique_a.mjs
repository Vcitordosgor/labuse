// FIX COSMÉTIQUE A — loading mauve sur les 4 outils lents (délai réseau injecté pour figer l'état).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 950 } })
// ralentir les 4 endpoints outils de ~2,5 s pour capturer le loading
await p.route(/\/(modules\/(bailleur|promesses)|moteurs\/(simulplu|zan))/, async (route) => {
  await new Promise((r) => setTimeout(r, 2500)); route.continue()
})
async function grab(mod, file, prep) {
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
  if (prep) await prep()
  await p.evaluate((m) => window.__labuse.setModule(m), mod)
  if (mod === 'simulplu') { // il faut sélectionner une zone pour déclencher le fetch
    await p.waitForSelector('button:has-text("→ U")', { timeout: 8000 })
    await p.locator('button:has-text("→ U")').first().click()
  }
  // attendre l'indicateur de chargement (points mauves)
  await p.waitForSelector('.labuse-dot', { timeout: 8000 })
  await p.waitForTimeout(400)
  const label = await p.evaluate(() => (document.querySelector('[role=status]')?.textContent || '').trim())
  console.log(`${mod}: loading visible, label = "${label}"`)
  await p.locator('aside').first().screenshot({ path: `${OUT}/${file}` })
}
await grab('bailleur', 'fixA-loading-bailleur.png')
await grab('promesses', 'fixA-loading-promesses.png')
await grab('zan', 'fixA-loading-zan.png')
await grab('simulplu', 'fixA-loading-simulplu.png', async () => { await p.evaluate(() => window.__labuse.setCommune('Saint-Denis')) })
await b.close()
console.log('captures A OK')
