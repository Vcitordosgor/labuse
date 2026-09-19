// FICHE-PORTES-1 — preuve : les 2 nouvelles portes (Permis §9, Densifier §10) cliquées → outil
// ouvert avec la commune de la parcelle ; + §8 Marché SANS la porte Taxe (Comparer/Temps restent).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-portes1/'
const IDU = '97410000AN0347'   // Saint-Benoît
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
async function loadFiche(p) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1200); await p.evaluate((i) => window.__labuse.select(i), IDU)
  await p.waitForFunction((i) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(i) && !/Chargement de la fiche/.test(t) }, IDU, { timeout: 90000 }).catch(() => {})
  await sleep(1400)
}
// 1) Permis §9 Quartier
{
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage(); p.on('pageerror', () => {})
  await loadFiche(p)
  await p.evaluate(() => document.querySelector('[data-drawer="quartier"] button.tiroir')?.click()); await sleep(500)
  await p.locator('[data-porte="permis"]').first().scrollIntoViewIfNeeded().catch(() => {})
  await p.locator('[data-porte="permis"]').first().click(); await sleep(1800)
  const ctxOk = (await p.evaluate(() => (document.body.innerText || '').toLowerCase())).includes('benoit') || (await p.evaluate(() => (document.body.innerText || '').toLowerCase())).includes('benoît')
  await p.screenshot({ path: `${OUT}permis_ouvert.png` })
  console.log('Permis §9 → outil ouvert, commune Saint-Benoît en contexte :', ctxOk)
  await ctx.close()
}
// 2) Densifier §10 Potentiel
{
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage(); p.on('pageerror', () => {})
  await loadFiche(p)
  await p.evaluate(() => document.querySelector('[data-drawer="potentiel"] button.tiroir')?.click()); await sleep(500)
  await p.locator('[data-porte="renouvellement"]').first().scrollIntoViewIfNeeded().catch(() => {})
  await p.locator('[data-porte="renouvellement"]').first().click(); await sleep(1800)
  const ctxOk = (await p.evaluate(() => (document.body.innerText || '').toLowerCase())).includes('benoit') || (await p.evaluate(() => (document.body.innerText || '').toLowerCase())).includes('benoît')
  await p.screenshot({ path: `${OUT}densifier_ouvert.png` })
  console.log('Densifier §10 → outil ouvert, commune Saint-Benoît en contexte :', ctxOk)
  await ctx.close()
}
// 3) §8 Marché SANS la porte Taxe (Comparer + Temps restent)
{
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage(); p.on('pageerror', () => {})
  await loadFiche(p)
  await p.evaluate(() => document.querySelector('[data-drawer="marche"] button.tiroir')?.click()); await sleep(600)
  await p.evaluate(() => document.querySelector('[data-drawer="marche"]')?.scrollIntoView({ block: 'start' })); await sleep(400)
  const state = await p.evaluate(() => {
    const d = document.querySelector('[data-drawer="marche"]')
    return {
      taxe: !!d.querySelector('[data-porte="taxe-amenagement"]'),
      comparer: !!d.querySelector('[data-porte="comparer"]'),
      temps: !!d.querySelector('[data-porte="temps"]'),
    }
  })
  const bb = await p.locator('.fiche-v6').boundingBox()
  await p.screenshot({ path: `${OUT}marche_sans_taxe.png`, clip: { x: Math.max(0, bb.x), y: 0, width: bb.width, height: Math.min(1100, bb.height) } })
  console.log('§8 Marché : porte taxe =', state.taxe, '| comparer =', state.comparer, '| temps =', state.temps)
  await ctx.close()
}
await br.close(); console.log('DONE')
