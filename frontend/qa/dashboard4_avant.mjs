// DASHBOARD-4 — captures AVANT (worktree pristine 3d96bf05 sur :5336, même backend). Un écran par lot :
// Pilotage · Comptes · Circuit(Données) · Radar · Courrier. Preuve de l'état de départ.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5336/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1700'] })
const ctx = await br.newContext({ viewport: { width: 1400, height: 1700 } })
const p = await ctx.newPage(); p.on('pageerror', () => {})
async function ecran(section, nom, attendre) {
  await p.evaluate((k) => { document.querySelector(`aside button[data-admin-section="${k}"]`)?.click() }, section)
  await sleep(attendre)
  await p.screenshot({ path: `${OUT}${nom}-avant.png`, fullPage: true })
  console.log('capté', nom)
}
await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(2500)
await p.screenshot({ path: `${OUT}lot1-pilotage-avant.png`, fullPage: true }); console.log('capté pilotage')
await ecran('licences', 'lot5-comptes', 2500)
await ecran('donnees', 'lot2-donnees', 9000)
await ecran('radar', 'lot3-radar', 3000)
await ecran('courrier', 'lot4-courrier', 3000)
await br.close(); console.log('DONE avant')
