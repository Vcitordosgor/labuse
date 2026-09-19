// FICHE-SANS-OBJET-1 — preuve : §4 Urbanisme, repli « N sans objet » FERMÉ puis OUVERT sur les 2
// témoins (lignes récupérées), + recherche « forêt » sur 97410000AN0347 qui trouve « Hors forêt publique ».
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-sansobjet1/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const clip = async (p) => { const bb = await p.locator('.fiche-v6').boundingBox(); return { x: Math.max(0, bb.x), y: 0, width: bb.width, height: Math.min(1100, bb.height) } }
async function load(p, idu) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1500); await p.evaluate((i) => window.__labuse.select(i), idu)
  await p.waitForFunction((i) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(i) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1500)
}
for (const [key, idu] of [['constrained', '97410000AN0347'], ['simple', '97422000AK0924']]) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('pageerror', String(e).slice(0, 120)))
  await load(p, idu)
  await p.evaluate(() => { const b = document.querySelector('[data-drawer="urbanisme"] button.tiroir'); b?.click() }); await sleep(700)
  await p.evaluate(() => document.querySelector('[data-urbanisme-sans-objet]')?.scrollIntoView({ block: 'center' })); await sleep(400)
  const summary = await p.evaluate(() => document.querySelector('[data-urbanisme-sans-objet] summary')?.textContent?.trim() || 'ABSENT')
  const open0 = await p.evaluate(() => (document.querySelector('[data-urbanisme-sans-objet]') || {}).open)
  await p.screenshot({ path: `${OUT}${key}_1_replie_ferme.png`, clip: await clip(p) })
  // ouvrir le repli
  await p.evaluate(() => { const d = document.querySelector('[data-urbanisme-sans-objet]'); if (d) d.open = true }); await sleep(400)
  await p.evaluate(() => document.querySelector('[data-urbanisme-sans-objet]')?.scrollIntoView({ block: 'center' })); await sleep(300)
  const nLignes = await p.evaluate(() => document.querySelectorAll('[data-urbanisme-sans-objet] > div > *').length)
  await p.screenshot({ path: `${OUT}${key}_2_replie_ouvert.png`, clip: await clip(p) })
  console.log(`${key} ${idu} :: summary="${summary}" open0=${open0} lignes=${nLignes}`)
  await ctx.close()
}
// recherche « forêt » sur le témoin contraint
{
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage()
  await load(p, '97410000AN0347')
  await p.locator('.fiche-v6 button[title="Rechercher dans cette fiche"]').click().catch(() => {})
  await sleep(300); await p.locator('[data-fiche-search]').fill('forêt'); await sleep(1400)
  await p.evaluate(() => document.querySelector('[data-fiche-search]')?.scrollIntoView({ block: 'start' })); await sleep(300)
  const found = await p.evaluate(() => [...document.querySelectorAll('[data-fiche-result]')].map((b) => (b.innerText || '').replace(/\s+/g, ' ').trim()))
  await p.screenshot({ path: `${OUT}recherche_foret.png`, clip: await clip(p) })
  console.log('recherche forêt →', found.length, 'résultats :', JSON.stringify(found))
  await ctx.close()
}
await br.close(); console.log('DONE')
