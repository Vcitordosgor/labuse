// FICHE-RANGEMENT-2 Lot 1 — capture the 11 nature sections (+ Réhabilitation) on 2 witnesses AND
// census every data-* marker / FactRow label / Line text across the whole fiche (all drawers opened
// in turn). The census, run on OLD (HEAD) vs NEW (basculement), proves 0 data line is lost.
// Env: CAP=1 → also write per-drawer screenshots ; CENSUS_TAG=new|old → census filename.
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const BASE = process.env.BASE || 'http://localhost:5278/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/fiche-rangement2/'
const TAG = process.env.CENSUS_TAG || 'new'
const CAP = process.env.CAP === '1'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const PARCELS = [
  { key: 'constrained', idu: '97410000AN0347', label: 'Saint-Benoit N/ERL 6 aleas 3 SUP PM' },
  { key: 'simple', idu: '97422000AK0924', label: 'Le Tampon Ub 1 alea 0 SUP PP' },
]
// NEW ids (basculement). OLD tree ids differ; census opens by name-fallback too.
const DRAWERS = [
  { id: 'identite', name: 'Identité' }, { id: 'terrain', name: 'Terrain' }, { id: 'bati', name: 'Bâti' },
  { id: 'urbanisme', name: 'Urbanisme' }, { id: 'risques', name: 'Risques et environnement' },
  { id: 'reseaux', name: 'Réseaux et desserte' }, { id: 'fiscalite', name: 'Fiscalité et dispositifs' },
  { id: 'marche', name: 'Marché' }, { id: 'quartier', name: 'Quartier' }, { id: 'potentiel', name: 'Potentiel' },
  { id: 'simulation', name: 'Simulation' }, { id: 'mode-b', name: 'Réhabilitation' },
]
// OLD tree drawer ids (HEAD 18f4e54e), for census on the pre-basculement layout.
const DRAWERS_OLD = [
  { id: 'regles', name: 'Urbanisme' }, { id: 'faisabilite', name: 'Constructibilité' },
  { id: 'dispositifs', name: 'Dispositifs et périmètres' }, { id: 'mode-b', name: 'Réhabilitation' },
  { id: 'le_bien', name: 'Le bien' }, { id: 'risques', name: 'Risques et protections' },
  { id: 'marche', name: 'Marché et secteur' }, { id: 'viabilisation', name: 'Réseaux et accès' },
  { id: 'autour-zone', name: 'Autour de cette parcelle' }, { id: 'territoire', name: 'Dispositifs territoriaux' },
  { id: 'proprio', name: 'Propriétaire' }, { id: 'confiance', name: 'Données et méthode' },
]
const drawerList = TAG === 'old' ? DRAWERS_OLD : DRAWERS

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const census = {}

// harvest all data-* attribute keys + FactRow labels + Line/row texts currently in the DOM.
const harvest = (p) => p.evaluate(() => {
  const box = document.querySelector('.fiche-v6'); if (!box) return { marks: [], rows: [] }
  const marks = new Set(), rows = new Set()
  box.querySelectorAll('*').forEach((el) => {
    for (const a of el.attributes) if (a.name.startsWith('data-')) marks.add(a.name)
    if (el.classList.contains('f-row')) {
      const l = el.querySelector('.l')?.textContent?.trim()
      if (l) rows.add('factrow:' + l.replace(/\s+/g, ' ').slice(0, 60))
    }
    if (el.classList.contains('l-line') || el.classList.contains('line')) {
      const t = el.textContent?.trim(); if (t) rows.add('line:' + t.replace(/\s+/g, ' ').slice(0, 60))
    }
  })
  return { marks: [...marks], rows: [...rows] }
})

const openById = (p, id) => p.evaluate((id) => {
  const d = document.querySelector(`[data-drawer="${id}"]`); if (!d) return false
  const b = d.querySelector('button.tiroir'); if (!b) return false
  b.scrollIntoView({ block: 'center' }); b.click(); return true
}, id)
const openByName = (p, name) => p.evaluate((name) => {
  const box = document.querySelector('.fiche-v6'); if (!box) return false
  for (const t of box.querySelectorAll('.t-title')) {
    if ((t.textContent || '').trim() === name) { const b = t.closest('button.tiroir'); if (b) { b.scrollIntoView({ block: 'center' }); b.click(); return true } }
  }
  return false
})
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
  const allMarks = new Set(), allRows = new Set(); const drawerRec = []
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
    // reveal analyse card (harvest its markers too)
    const cta = p.locator('.fiche-v6').getByText(/Demander à LABUSE|analyser la parcelle/i).first()
    if (await cta.count().catch(() => 0)) { await cta.click().catch(() => {}); await sleep(1600) }
    await expandDetails(p); await sleep(300)
    let h = await harvest(p); h.marks.forEach((m) => allMarks.add(m)); h.rows.forEach((r) => allRows.add(r))
    if (CAP) { await unscroll(p); await sleep(300); await p.locator('.fiche-v6').first().screenshot({ path: OUT + '00_entete_analyse.png' }).catch(() => {}) }

    for (let i = 0; i < drawerList.length; i++) {
      const { id, name } = drawerList[i]
      await resetStyles(p); await sleep(150)
      let opened = await openById(p, id)
      if (!opened) opened = await openByName(p, name)
      await sleep(700); await expandDetails(p); await sleep(400)
      h = await harvest(p); const before = allMarks.size
      h.marks.forEach((m) => allMarks.add(m)); h.rows.forEach((r) => allRows.add(r))
      const present = await p.evaluate((id) => !!document.querySelector(`[data-drawer="${id}"]`), id)
      drawerRec.push({ id, name, present, opened, newMarks: allMarks.size - before })
      if (CAP && (present || opened)) {
        await unscroll(p); await sleep(300)
        const nn = String(i + 1).padStart(2, '0')
        const safe = name.normalize('NFD').replace(/[^\w]+/g, '_').replace(/^_|_$/g, '')
        await p.locator('.fiche-v6').first().screenshot({ path: OUT + `${nn}_${safe}.png` }).catch(() => {})
      }
      console.log(`${TAG}\t${par.key}\t${name}\tpresent=${present}\topened=${opened}`)
    }
  } catch (e) { console.log(`${par.key} ERR ${String(e).slice(0, 160)}`) }
  census[par.key] = { idu: par.idu, drawers: drawerRec, marks: [...allMarks].sort(), rows: [...allRows].sort() }
  await ctx.close().catch(() => {})
}
mkdirSync(ROOT, { recursive: true })
writeFileSync(ROOT + `census_${TAG}.json`, JSON.stringify(census, null, 1))
await br.close()
console.log('DONE ' + TAG)
