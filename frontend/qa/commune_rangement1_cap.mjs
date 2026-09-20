// COMMUNE-RANGEMENT-1 — preuve APRÈS : cartes touchées dépliées sur 2 témoins.
// Lot 1 tendance → carte marche · Lot 2 parc social → carte population · Lot 4 (robinet, visuel inchangé) → carte zfang-frr.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = process.env.BASE || 'http://localhost:5299/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/commune-rangement1/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const COMMUNES = [{ key: 'saint-denis', nom: 'Saint-Denis' }, { key: 'cilaos', nom: 'Cilaos' }]
const CARDS = ['marche', 'population', 'zfang-frr']
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1500,1100'] })
for (const { key, nom } of COMMUNES) {
  const OUT = ROOT + key + '/'; mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1500, height: 1100 }, deviceScaleFactor: 2 })
  const p = await ctx.newPage(); p.on('pageerror', () => {})
  await p.goto(BASE + `#f=1&v=1&c=${encodeURIComponent(nom)}`, { waitUntil: 'domcontentloaded' })
  await p.reload({ waitUntil: 'domcontentloaded' })
  await p.waitForSelector('[data-contexte-btn]', { timeout: 30000 }); await sleep(800)
  await p.locator('[data-contexte-btn]').click()
  await p.waitForSelector('[data-contexte-panel] details[data-acc="marche"]', { timeout: 20000 }); await sleep(1800)
  await p.evaluate(() => document.querySelector('[data-contexte-panel]').querySelectorAll('details').forEach((d) => { d.open = true }))
  // la tendance vient d'une requête SÉPARÉE (mu-marche) ; on l'attend (soft — sous-seuil = jamais affichée)
  await p.waitForSelector('[data-contexte-panel] >> text=Tendance 12 mois', { timeout: 6000 }).catch(() => {})
  await sleep(600)
  for (const id of CARDS) {
    const el = p.locator(`[data-contexte-panel] details[data-acc="${id}"]`)
    if (await el.count()) { try { await el.scrollIntoViewIfNeeded(); await sleep(120); await el.screenshot({ path: OUT + id + '.png' }); console.log(`${nom} ${id} OK`) } catch (e) { console.log(`${nom} ${id} FAIL`) } }
    else console.log(`${nom} ${id} absente`)
  }
  await ctx.close()
}
await br.close(); console.log('OK — captures/commune-rangement1/')
