// FICHE-RANGEMENT-2 Lot 4 — captures §4 Urbanisme (grammaire filet unique) + §7 Fiscalité (TVA
// une seule fois). + census : compte les occurrences de « 8,5 » dans §7 (doit être 1).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-rangement2/lot4/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const openById = (p, id) => p.evaluate((id) => { const d = document.querySelector(`[data-drawer="${id}"]`); const b = d?.querySelector('button.tiroir'); if (b) { b.scrollIntoView({ block: 'center' }); b.click(); return true } return false }, id)
const unscroll = (p) => p.evaluate(() => { const box = document.querySelector('.fiche-v6'); if (!box) return; let sc = null, mx = 0; box.querySelectorAll('*').forEach((el) => { const d = el.scrollHeight - el.clientHeight; if (d > mx && /auto|scroll/.test(getComputedStyle(el).overflowY)) { mx = d; sc = el } }); sc = sc || box; let n = sc; while (n && n !== document.body) { n.style.overflow = 'visible'; n.style.maxHeight = 'none'; n.style.height = 'auto'; n.style.flex = 'none'; n.style.position = 'static'; n = n.parentElement } sc.style.height = sc.scrollHeight + 'px'; box.style.width = '400px' })
for (const [key, idu] of [['constrained', '97410000AN0347'], ['simple', '97422000AK0924']]) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } })
  const p = await ctx.newPage(); p.on('pageerror', (e) => console.log('pageerror', String(e).slice(0, 120)))
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const explore = p.getByText('Explorer la carte', { exact: false }); if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
  await sleep(1500)
  await p.evaluate((idu) => window.__labuse.select(idu), idu)
  await p.waitForFunction((idu) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(idu) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1500)
  for (const [id, label] of [['urbanisme', '04_Urbanisme'], ['fiscalite', '07_Fiscalite']]) {
    await openById(p, id); await sleep(700)
    p.evaluate(() => document.querySelector('.fiche-v6')?.querySelectorAll('details').forEach((d) => { d.open = true }))
    await sleep(300); await unscroll(p); await sleep(300)
    await p.locator('.fiche-v6').first().screenshot({ path: OUT + `${key}_${label}.png` }).catch(() => {})
    // re-close before next (accordion exclusive) by re-opening handled by openById next iter
    await p.evaluate((id) => { const b = document.querySelector(`[data-drawer="${id}"] button.tiroir`); b?.click() }, id)
    await sleep(200)
  }
  const fisc = await p.evaluate(() => {
    const d = document.querySelector('[data-drawer="fiscalite"]')
    const b = d?.querySelector('button.tiroir'); b?.click()
    return null
  })
  void fisc
  // count « 8,5 » in §7 (must be 1)
  await openById(p, 'fiscalite'); await sleep(500)
  const n85 = await p.evaluate(() => { const t = (document.querySelector('[data-drawer="fiscalite"]')?.innerText || ''); return (t.match(/8,5/g) || []).length })
  const nTVA = await p.evaluate(() => { const t = (document.querySelector('[data-drawer="fiscalite"]')?.innerText || ''); return (t.match(/TVA/g) || []).length })
  console.log(`${key} §7 « 8,5 » ×${n85} · « TVA » ×${nTVA}`)
  await ctx.close().catch(() => {})
}
await br.close(); console.log('DONE')
