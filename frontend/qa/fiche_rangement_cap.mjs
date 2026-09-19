// FICHE-RANGEMENT-1 — capture avant/après des tiroirs touchés, sur les 2 parcelles témoins.
// Usage: node qa/fiche_rangement_cap.mjs <lot> <phase>   (ex: node qa/fiche_rangement_cap.mjs lot1 avant)
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const [lot, phase] = process.argv.slice(2)
if (!lot || !phase) { console.error('usage: <lot> <phase>'); process.exit(1) }
const ROOT = `/Users/openclaw/Desktop/labuse/captures/fiche-rangement/${lot}/${phase}/`
const BASE = 'http://localhost:5277/socle/'

const PARCELS = [
  { key: 'constrained', idu: '97410000AN0347' },
  { key: 'simple', idu: '97422000AK0924' },
]
// tiroirs touchés par les 3 lots (superset) — 00 = en-tête + Analyse
const DRAWERS = ['Urbanisme', 'Constructibilité', 'Le bien', 'Risques et protections',
  'Marché et secteur', 'Réseaux et accès']

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
for (const par of PARCELS) {
  const OUT = ROOT + par.key + '/'
  mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage()
  p.on('pageerror', () => {})
  const expandDetails = () => p.evaluate(() => {
    const b = document.querySelector('.fiche-v6'); if (b) b.querySelectorAll('details').forEach((el) => { el.open = true })
  })
  const resetStyles = () => p.evaluate(() => {
    const box = document.querySelector('.fiche-v6'); if (!box) return
    const clr = (el) => { el.style.height = ''; el.style.maxHeight = ''; el.style.overflow = ''; el.style.flex = ''; el.style.position = ''; el.style.width = '' }
    let n = box; while (n && n !== document.body) { clr(n); n = n.parentElement }
    clr(box); box.querySelectorAll('*').forEach(clr)
  })
  const unscroll = () => p.evaluate(() => {
    const box = document.querySelector('.fiche-v6'); if (!box) return
    let sc = null, mx = 0
    box.querySelectorAll('*').forEach((el) => { const d = el.scrollHeight - el.clientHeight; if (d > mx && /auto|scroll/.test(getComputedStyle(el).overflowY)) { mx = d; sc = el } })
    sc = sc || box; let n = sc
    while (n && n !== document.body) { n.style.overflow = 'visible'; n.style.maxHeight = 'none'; n.style.height = 'auto'; n.style.flex = 'none'; n.style.position = 'static'; n = n.parentElement }
    sc.style.height = sc.scrollHeight + 'px'; box.style.width = '400px'
  })
  try {
    await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
    const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
    await sleep(2000)
    await p.evaluate((idu) => window.__labuse.select(idu), par.idu)
    await p.waitForFunction((idu) => { const b = document.querySelector('.fiche-v6'); const t = b && (b.innerText || ''); return b && t.includes(idu) && !/Chargement de la fiche/.test(t) && /Risques et protections/.test(t) }, par.idu, { timeout: 90000 }).catch(() => {})
    await sleep(1200)
    const cta = p.locator('.fiche-v6').getByText(/Demander à LABUSE|analyser la parcelle/i).first()
    if (await cta.count().catch(() => 0)) { await cta.click().catch(() => {}); await sleep(1800) }
    const fiche = p.locator('.fiche-v6').first()
    await expandDetails(); await unscroll(); await sleep(400)
    await fiche.screenshot({ path: OUT + '00_entete_analyse.png' }).catch(() => {})
    for (let i = 0; i < DRAWERS.length; i++) {
      const title = DRAWERS[i]
      const loc = p.locator('.fiche-v6').getByText(title, { exact: false }).first()
      if (!(await loc.count().catch(() => 0))) { console.log(`${par.key}\t${title}\tABSENT`); continue }
      await resetStyles(); await sleep(200)
      await loc.scrollIntoViewIfNeeded().catch(() => {})
      await loc.click({ timeout: 5000 }).catch(() => {})
      await sleep(800); await expandDetails(); await sleep(400); await unscroll(); await sleep(400)
      const safe = title.normalize('NFD').replace(/[^\w]+/g, '_').replace(/^_|_$/g, '')
      await fiche.screenshot({ path: OUT + `${String(i + 1).padStart(2, '0')}_${safe}.png` }).catch(() => {})
      console.log(`${par.key}\t${title}\tOK`)
    }
  } catch (e) { console.log(`${par.key} ERR ${String(e).slice(0, 120)}`) }
  await ctx.close().catch(() => {})
}
await br.close()
console.log('DONE', lot, phase)
