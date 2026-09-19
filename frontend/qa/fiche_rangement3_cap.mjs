// FICHE-RANGEMENT-3 — recompte + captures. Per parcelle, opens each of the 11 drawers, records its
// [data-drawer] innerText + the fiche-wide data-* marker union, and (CAP=1) screenshots each drawer.
// Run before (HEAD 355ac3ff via git stash) vs after → prove: no line lost overall, doublons once.
// Env: CAP=1 → screenshots ; CENSUS_TAG=before|after → census filename.
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const BASE = process.env.BASE || 'http://localhost:5278/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/fiche-rangement3/'
const TAG = process.env.CENSUS_TAG || 'after'
const CAP = process.env.CAP === '1'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const PARCELS = [
  { key: 'constrained', idu: '97410000AN0347' },
  { key: 'simple', idu: '97422000AK0924' },
]
// 11 sections (both before/after have these ids). 'mode-b' only exists as a sibling BEFORE (rangement-2).
const DRAWERS = [
  { id: 'identite', name: 'Identité' }, { id: 'terrain', name: 'Terrain' }, { id: 'bati', name: 'Bâti' },
  { id: 'urbanisme', name: 'Urbanisme' }, { id: 'risques', name: 'Risques et environnement' },
  { id: 'reseaux', name: 'Réseaux et desserte' }, { id: 'fiscalite', name: 'Fiscalité et dispositifs' },
  { id: 'marche', name: 'Marché' }, { id: 'quartier', name: 'Quartier' }, { id: 'potentiel', name: 'Potentiel' },
  { id: 'simulation', name: 'Simulation' }, { id: 'mode-b', name: 'Réhabilitation' },
]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const census = {}
const markerUnion = (p) => p.evaluate(() => {
  const box = document.querySelector('.fiche-v6'); if (!box) return []
  const s = new Set()
  box.querySelectorAll('*').forEach((el) => { for (const a of el.attributes) if (a.name.startsWith('data-')) s.add(a.name) })
  return [...s]
})
const drawerText = (p, id) => p.evaluate((id) => {
  const d = document.querySelector(`[data-drawer="${id}"]`); if (!d) return null
  return (d.innerText || '').replace(/\s+/g, ' ').trim()
}, id)
const openById = (p, id) => p.evaluate((id) => {
  const d = document.querySelector(`[data-drawer="${id}"]`); if (!d) return false
  const b = d.querySelector('button.tiroir'); if (!b) return false
  b.scrollIntoView({ block: 'center' }); b.click(); return true
}, id)
const expandDetails = (p) => p.evaluate(() => document.querySelector('.fiche-v6')?.querySelectorAll('details').forEach((el) => { el.open = true }))
const resetStyles = (p) => p.evaluate(() => {
  const box = document.querySelector('.fiche-v6'); if (!box) return
  const clr = (el) => { el.style.height = ''; el.style.maxHeight = ''; el.style.overflow = ''; el.style.flex = ''; el.style.position = ''; el.style.width = '' }
  let n = box; while (n && n !== document.body) { clr(n); n = n.parentElement }
  clr(box); box.querySelectorAll('*').forEach(clr)
})
const unscroll = (p) => p.evaluate(() => {
  const box = document.querySelector('.fiche-v6'); if (!box) return
  let sc = null, mx = 0
  box.querySelectorAll('*').forEach((el) => { const d = el.scrollHeight - el.clientHeight; if (d > mx && /auto|scroll/.test(getComputedStyle(el).overflowY)) { mx = d; sc = el } })
  sc = sc || box
  let n = sc; while (n && n !== document.body) { n.style.overflow = 'visible'; n.style.maxHeight = 'none'; n.style.height = 'auto'; n.style.flex = 'none'; n.style.position = 'static'; n = n.parentElement }
  sc.style.height = sc.scrollHeight + 'px'; box.style.width = '400px'
})
for (const par of PARCELS) {
  const OUT = ROOT + par.key + '/'
  if (CAP) mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage(); p.on('pageerror', () => {})
  const rec = { idu: par.idu, drawers: {}, markers: [] }
  try {
    await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
    const explore = p.getByText('Explorer la carte', { exact: false })
    if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
    await sleep(2000)
    await p.evaluate((idu) => window.__labuse.select(idu), par.idu)
    await p.waitForFunction((idu) => {
      const bx = document.querySelector('.fiche-v6'); const t = bx && (bx.innerText || '')
      return bx && t.includes(idu) && !/Chargement de la fiche/.test(t)
    }, par.idu, { timeout: 90000 }).catch(() => {})
    await sleep(1500)
    const cta = p.locator('.fiche-v6').getByText(/Demander à LABUSE|analyser la parcelle/i).first()
    if (await cta.count().catch(() => 0)) { await cta.click().catch(() => {}); await sleep(1600) }
    const marks = new Set()
    for (let i = 0; i < DRAWERS.length; i++) {
      const { id, name } = DRAWERS[i]
      await resetStyles(p); await sleep(120)
      const opened = await openById(p, id)
      await sleep(650); await expandDetails(p); await sleep(350)
      ;(await markerUnion(p)).forEach((m) => marks.add(m))
      const txt = await drawerText(p, id)
      if (txt != null) rec.drawers[id] = txt
      if (CAP && opened) {
        await unscroll(p); await sleep(250)
        const nn = String(i + 1).padStart(2, '0')
        const safe = name.normalize('NFD').replace(/[^\w]+/g, '_').replace(/^_|_$/g, '')
        await p.locator('.fiche-v6').first().screenshot({ path: OUT + `${nn}_${safe}.png` }).catch(() => {})
      }
      console.log(`${TAG}\t${par.key}\t${id}\tpresent=${txt != null}`)
    }
    rec.markers = [...marks].sort()
  } catch (e) { console.log(`${par.key} ERR ${String(e).slice(0, 160)}`) }
  census[par.key] = rec
  await ctx.close().catch(() => {})
}
mkdirSync(ROOT, { recursive: true })
writeFileSync(ROOT + `census_${TAG}.json`, JSON.stringify(census, null, 1))
await br.close()
console.log('DONE ' + TAG)
