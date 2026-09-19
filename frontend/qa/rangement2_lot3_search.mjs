// FICHE-RANGEMENT-2 Lot 3 — vérifie la recherche « dans tout » : une requête ouvre tous les
// tiroirs (forceOpen) + les <details>, et surligne (CSS.highlights) en place.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-rangement2/lot3-search/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
for (const [key, idu, q] of [['constrained', '97410000AN0347', 'PLU'], ['simple', '97422000AK0924', 'égout']]) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('pageerror', String(e).slice(0, 120)))
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const explore = p.getByText('Explorer la carte', { exact: false })
  if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
  await sleep(1500)
  await p.evaluate((idu) => window.__labuse.select(idu), idu)
  await p.waitForFunction((idu) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(idu) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1500)
  // ouvrir la recherche (loupe de l'en-tête) + taper la requête
  await p.locator('.fiche-v6 button[title="Rechercher dans cette fiche"]').click().catch(() => {})
  await sleep(300)
  await p.locator('[data-fiche-search]').fill(q)
  await sleep(1500)
  const state = await p.evaluate(() => {
    const box = document.querySelector('.fiche-v6')
    const drawers = [...box.querySelectorAll('[data-drawer]')]
    const openDrawers = drawers.filter((d) => d.querySelector('.t-open')).map((d) => d.getAttribute('data-drawer'))
    const detailsOpen = [...box.querySelectorAll('details')].filter((d) => d.open).length
    const detailsTotal = box.querySelectorAll('details').length
    const HL = (CSS && CSS.highlights) ? CSS.highlights.get('fiche-search') : null
    const count = HL ? HL.size : -1
    const countTxt = box.querySelector('[data-fiche-search-count]')?.textContent || ''
    return { drawers: drawers.length, openDrawers: openDrawers.length, detailsOpen, detailsTotal, hlRanges: count, countTxt }
  })
  console.log(`${key} q=${q} ::`, JSON.stringify(state))
  await p.locator('.fiche-v6').first().screenshot({ path: OUT + `${key}_search_${q}.png` }).catch(() => {})
  await ctx.close().catch(() => {})
}
await br.close()
console.log('DONE')
