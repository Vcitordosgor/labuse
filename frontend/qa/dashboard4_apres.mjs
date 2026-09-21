// DASHBOARD-4 — captures APRÈS (worktree courant :5335). Chaque section modifiée. Réutilisable :
// node dashboard4_apres.mjs [pilotage|radar|courrier|donnees|comptes|tout]
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5335/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-dash4/captures/dashboard4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const seul = process.argv[2] || 'tout'
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1400,1700'] })
const ctx = await br.newContext({ viewport: { width: 1400, height: 1700 } })
const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('PAGEERR', e.message))
async function go(key) {
  // le rail porte data-admin-section : robuste (le libellé est précédé d'une icône dans le textContent).
  await p.evaluate((k) => { document.querySelector(`aside button[data-admin-section="${k}"]`)?.click() }, key)
}
await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(2000)
if (seul === 'radar' || seul === 'tout') {
  await go('radar'); await sleep(3000)
  const banner = await p.evaluate(() => (document.body.innerText || '').includes('Faits extraits'))
  console.log('Radar — bandeau « Faits extraits » présent ?', banner, '(doit être false)')
  await p.screenshot({ path: OUT + 'lot3-radar-apres.png', fullPage: true }); console.log('capté radar')
}
if (seul === 'courrier' || seul === 'tout') {
  await go('courrier'); await sleep(3000)
  const piste = await p.evaluate(() => /piste\s*#\d/i.test(document.body.innerText || ''))
  console.log('Courrier — « piste #<id global> » présent ?', piste, '(doit être false)')
  await p.screenshot({ path: OUT + 'lot4-courrier-apres.png', fullPage: true }); console.log('capté courrier')
}
if (seul === 'donnees' || seul === 'tout') {
  await go('donnees'); await sleep(9000)
  await p.screenshot({ path: OUT + 'lot2-donnees-apres.png', fullPage: true }); console.log('capté donnees')
}
if (seul === 'comptes' || seul === 'tout') {
  await go('licences'); await sleep(3000)
  await p.screenshot({ path: OUT + 'lot5-comptes-apres.png', fullPage: true }); console.log('capté comptes')
}
await br.close(); console.log('DONE apres')
