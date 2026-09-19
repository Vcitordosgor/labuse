// FICHE-RECHERCHE-1 — preuve : pour chaque terme, la LISTE de résultats sous la barre, puis
// l'état APRÈS CLIC (section ouverte + ligne surlignée à l'écran). Capture viewport-clippée à la fiche.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-recherche1/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
// FICHE-RECHERCHE-1 — un témoin PAR TERME, choisi pour que le terme soit RÉELLEMENT rendu sur la
// fiche (la recherche ne trouve que ce qui est affiché) : TCSP = parcelle à ≤ 800 m d'une station
// TCSP ; forêt = parcelle en forêt domaniale ; bruit/DPE/taxe = la parcelle contrainte (St-Benoît).
const TERMS = ['TCSP', 'forêt', 'bruit', 'DPE', 'taxe']
const PAR_TERME = {
  TCSP: [['tcsp', '97411000BL0256'], ['constrained', '97410000AN0347']],
  'forêt': [['foret', '97415000AH0019'], ['constrained', '97410000AN0347']],
  bruit: [['constrained', '97410000AN0347'], ['simple', '97422000AK0924']],
  DPE: [['constrained', '97410000AN0347'], ['simple', '97422000AK0924']],
  taxe: [['constrained', '97410000AN0347'], ['simple', '97422000AK0924']],
}
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })

async function loadFiche(p, idu) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1500)
  await p.evaluate((i) => window.__labuse.select(i), idu)
  await p.waitForFunction((i) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(i) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1500)
}
const clip = async (p) => { const bb = await p.locator('.fiche-v6').boundingBox(); return { x: Math.max(0, bb.x), y: 0, width: bb.width, height: Math.min(1100, bb.height) } }

for (const term of TERMS) {
  let done = false
  for (const [key, idu] of PAR_TERME[term]) {
    const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
    const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('pageerror', String(e).slice(0, 120)))
    await loadFiche(p, idu)
    // ouvrir la loupe + taper
    await p.locator('.fiche-v6 button[title="Rechercher dans cette fiche"]').click().catch(() => {})
    await sleep(300)
    await p.locator('[data-fiche-search]').fill(term)
    await sleep(1400)
    const n = await p.evaluate(() => document.querySelectorAll('[data-fiche-result]').length)
    if (n === 0) { await ctx.close(); continue }   // repli parcelle suivante
    // amener la barre en haut pour voir la liste, puis capture
    await p.evaluate(() => document.querySelector('[data-fiche-search]')?.scrollIntoView({ block: 'start' }))
    await sleep(400)
    await p.screenshot({ path: `${OUT}${term}_1_liste.png`, clip: await clip(p) })
    // choisir le résultat dont le libellé contient le terme (sinon le premier), cliquer
    const idx = await p.evaluate((t) => {
      const btns = [...document.querySelectorAll('[data-fiche-result]')]
      const i = btns.findIndex((b) => (b.innerText || '').toLowerCase().includes(t.toLowerCase()))
      return i >= 0 ? i : 0
    }, term)
    const label = await p.evaluate((i) => (document.querySelectorAll('[data-fiche-result]')[i]?.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70), idx)
    await p.locator('[data-fiche-result]').nth(idx).click()
    await sleep(1200)
    await p.screenshot({ path: `${OUT}${term}_2_clic.png`, clip: await clip(p) })
    console.log(`${term}\t${key} ${idu}\t${n} résultats\tclic #${idx}: « ${label} »`)
    await ctx.close(); done = true; break
  }
  if (!done) console.log(`${term}\tAUCUN RÉSULTAT sur les 2 témoins`)
}
await br.close(); console.log('DONE')
