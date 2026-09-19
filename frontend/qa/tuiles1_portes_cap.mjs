// FICHE-TUILES-OUTILS-1 Lot 2 — audit des portes (lecture seule). Clique chaque porte de la fiche
// et capture l'outil ouvert, en vérifiant que la PARCELLE est en contexte (idu ou commune présents).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-tuiles-outils1/portes/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
// porte : {key, parcel, drawer (id du tiroir à ouvrir, ou null), sel (sélecteur du bouton)}
const AN = '97410000AN0347', AK = '97422000AK0924'
const PORTES = [
  { key: 'patrimoine', parcel: AN, drawer: 'identite', sel: '[data-porte="patrimoine"]' },
  { key: 'spf-courrier', parcel: AK, drawer: 'identite', sel: '[data-porte="spf-letter"]' },
  { key: 'plu-annuaire', parcel: AN, drawer: 'urbanisme', sel: '[data-porte="annuaire"]' },
  { key: 'plu-verif-procedure', parcel: AN, drawer: 'urbanisme', sel: '[data-porte="verif-procedure"]' },
  { key: 'risques', parcel: AN, drawer: 'risques', sel: '[data-porte="risques"]' },
  { key: 'taxe-fiscalite§7', parcel: AK, drawer: 'fiscalite', sel: '[data-porte="taxe-amenagement-outil"]' },
  { key: 'marche-commune', parcel: AN, drawer: 'marche', sel: '[data-porte="marche"]' },
  { key: 'taxe-marche§8', parcel: AN, drawer: 'marche', sel: '[data-porte="taxe-amenagement"]' },
  { key: 'secteur-opp', parcel: AN, drawer: 'marche', sel: '[data-secteur-opp]' },
  { key: 'comparer', parcel: AN, drawer: 'marche', sel: '[data-porte="comparer"]' },
  { key: 'temps', parcel: AN, drawer: 'marche', sel: '[data-porte="temps"]' },
  { key: 'faisabilite', parcel: AN, drawer: 'simulation', sel: '[data-porte="faisabilite-outil"]' },
  { key: 'calculette', parcel: AN, drawer: 'simulation', sel: '[data-porte="calculette"]' },
  { key: 'assemblage', parcel: AN, drawer: 'simulation', sel: '[data-porte="assemblage-outil"]' },
  { key: 'export-courrier', parcel: AN, drawer: null, sel: '[data-courrier-tile]' },
  { key: 'export-temps', parcel: AN, drawer: null, sel: '[data-temps-tile]' },
]
const tokens = { [AN]: ['97410000AN0347', 'benoit', 'benoît'], [AK]: ['97422000AK0924', 'tampon'] }
async function loadFiche(p, idu) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1200); await p.evaluate((i) => window.__labuse.select(i), idu)
  await p.waitForFunction((i) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(i) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1400)
}
for (const po of PORTES) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage()
  p.on('pageerror', () => {})
  let ctxFound = null
  try {
    await loadFiche(p, po.parcel)
    if (po.drawer) { await p.evaluate((id) => document.querySelector(`[data-drawer="${id}"] button.tiroir`)?.click(), po.drawer); await sleep(500) }
    const el = p.locator(po.sel).first()
    await el.scrollIntoViewIfNeeded().catch(() => {})
    await el.click({ timeout: 6000 })
    await sleep(1800)   // laisse l'outil s'ouvrir + charger
    const body = (await p.evaluate(() => document.body.innerText || '')).toLowerCase()
    ctxFound = tokens[po.parcel].some((t) => body.includes(t.toLowerCase()))
    await p.screenshot({ path: `${OUT}${po.key}.png` })
  } catch (e) { ctxFound = `ERR ${String(e).slice(0, 60)}` }
  console.log(`${po.key}\tparcelle=${po.parcel}\tcontexte=${ctxFound}`)
  await ctx.close()
}
await br.close(); console.log('DONE')
