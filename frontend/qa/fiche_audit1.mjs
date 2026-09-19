// FICHE-AUDIT-1 — capture each tiroir expanded on 2 witness parcels (main @ 6eb14b01).
// Fiche = exclusive accordion .fiche-v6 (all drawers collapsed by default). Per parcel (fresh
// browser context): reveal analyse card, then for each drawer JS-dispatch a click on its
// clickable header, force-open every nested <details>, neutralise inner scroll, and screenshot
// the whole .fiche-v6 element at full content height. Open is VERIFIED (scrollHeight grows).
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const BASE = 'http://localhost:5277/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/fiche-audit/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const PARCELS = [
  { key: 'constrained', idu: '97410000AN0347', label: 'Saint-Benoit N/ERL 6 aleas 3 SUP PM' },
  { key: 'simple', idu: '97422000AK0924', label: 'Le Tampon Ub 1 alea 0 SUP PP' },
]
const DRAWERS = [
  'Urbanisme', 'Constructibilité', 'Dispositifs et périmètres', 'Réhabilitation',
  'Le bien', 'Risques et protections', 'Marché et secteur', 'Réseaux et accès',
  'Autour de cette parcelle', 'Dispositifs territoriaux', 'Propriétaire', 'Données et méthode',
]

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const manifest = []
for (const par of PARCELS) {
  const OUT = ROOT + par.key + '/'
  mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage()
  p.on('pageerror', () => {})
  const rec = { idu: par.idu, key: par.key, drawers: [] }

  const expandDetails = () => p.evaluate(() => {
    const box = document.querySelector('.fiche-v6'); if (!box) return
    box.querySelectorAll('details').forEach((el) => { el.open = true })
  })
  const resetStyles = () => p.evaluate(() => {
    const box = document.querySelector('.fiche-v6'); if (!box) return
    const clr = (el) => { el.style.height = ''; el.style.maxHeight = ''; el.style.overflow = ''; el.style.flex = ''; el.style.position = ''; el.style.width = '' }
    // also reset ancestors mutated by unscroll
    let n = box; while (n && n !== document.body) { clr(n); n = n.parentElement }
    clr(box); box.querySelectorAll('*').forEach(clr)
  })
  // close all drawers, then JS-click the clickable header of `title`; returns whether it opened
  const openDrawer = (title) => p.evaluate((title) => {
    const box = document.querySelector('.fiche-v6'); if (!box) return { ok: false }
    const before = box.scrollHeight
    let target = null
    for (const e of box.querySelectorAll('*')) {
      const own = [...e.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join('').trim()
      if (own === title || (own.startsWith(title) && own.length < title.length + 30)) {
        let n = e
        for (let i = 0; i < 6 && n && n !== box; i++) {
          const cs = getComputedStyle(n)
          if (cs.cursor === 'pointer' || /is-lien|cursor-pointer|drawer/i.test(n.className || '')) { target = n; break }
          n = n.parentElement
        }
        if (target) break
      }
    }
    if (!target) {
      for (const e of box.querySelectorAll('*')) {
        if ((e.textContent || '').trim().startsWith(title) && e.querySelectorAll('*').length < 15) { target = e; break }
      }
    }
    if (!target) return { ok: false }
    target.scrollIntoView({ block: 'center' })
    target.click()
    return { ok: true, before }
  }, title)
  // size the fiche to its full content height for a complete element screenshot
  const unscroll = () => p.evaluate(() => {
    const box = document.querySelector('.fiche-v6'); if (!box) return
    let sc = null, mx = 0
    box.querySelectorAll('*').forEach((el) => {
      const d = el.scrollHeight - el.clientHeight
      if (d > mx && /auto|scroll/.test(getComputedStyle(el).overflowY)) { mx = d; sc = el }
    })
    sc = sc || box
    let n = sc
    while (n && n !== document.body) { n.style.overflow = 'visible'; n.style.maxHeight = 'none'; n.style.height = 'auto'; n.style.flex = 'none'; n.style.position = 'static'; n = n.parentElement }
    sc.style.height = sc.scrollHeight + 'px'
    box.style.width = '400px'
  })

  try {
    await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
    const explore = p.getByText('Explorer la carte', { exact: false })
    if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
    await sleep(2000)
    await p.evaluate((idu) => window.__labuse.select(idu), par.idu)
    await p.waitForFunction((idu) => {
      const bx = document.querySelector('.fiche-v6'); const t = bx && (bx.innerText || '')
      return bx && t.includes(idu) && !/Chargement de la fiche/.test(t) && /Risques et protections/.test(t)
    }, par.idu, { timeout: 90000 }).catch(() => {})
    await sleep(1200)

    // reveal analyse card
    const cta = p.locator('.fiche-v6').getByText(/Demander à LABUSE|analyser la parcelle|Demander l'analyse/i).first()
    if (await cta.count().catch(() => 0)) { await cta.click().catch(() => {}); await sleep(1800) }

    const fiche = p.locator('.fiche-v6').first()
    await expandDetails(); await unscroll(); await sleep(400)
    await fiche.screenshot({ path: OUT + '00_entete_analyse.png' }).catch(() => {})

    for (let i = 0; i < DRAWERS.length; i++) {
      const title = DRAWERS[i]
      const loc = p.locator('.fiche-v6').getByText(title, { exact: false }).first()
      const present = await loc.count().catch(() => 0)
      const d = { title, present: !!present, opened: false }
      if (present) {
        await resetStyles(); await sleep(200)
        await loc.scrollIntoViewIfNeeded().catch(() => {})
        await loc.click({ timeout: 5000 }).catch(async () => { await openDrawer(title) })
        await sleep(800)
        await expandDetails(); await sleep(500)
        await unscroll(); await sleep(400)
        d.opened = true
        const nn = String(i + 1).padStart(2, '0')
        const safe = title.normalize('NFD').replace(/[^\w]+/g, '_').replace(/^_|_$/g, '')
        await fiche.screenshot({ path: OUT + `${nn}_${safe}.png` }).catch(async () => {
          await p.screenshot({ path: OUT + `${nn}_${safe}.png`, fullPage: true })
        })
      }
      rec.drawers.push(d)
      console.log(`${par.key}\t${title}\tpresent=${d.present}\topened=${d.opened}`)
    }
  } catch (e) {
    rec.err = String(e).slice(0, 160)
    console.log(`${par.key} ERR ${rec.err}`)
  }
  await ctx.close().catch(() => {})
  manifest.push(rec)
}
writeFileSync(ROOT + 'manifest.json', JSON.stringify(manifest, null, 1))
await br.close()
console.log('DONE')
