// COMMUNE-RANGEMENT-2 lot 4 — preuve APRÈS : les 10 cartes (5 groupes) dépliées + le bandeau 6 chiffres,
// sur Saint-Denis (ORT hors) et Cilaos (sans QPV → carte Fiscalité « aucun quartier prioritaire »).
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const BASE = process.env.BASE || 'http://localhost:5299/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/commune-rangement2/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const COMMUNES = [{ key: 'saint-denis', nom: 'Saint-Denis' }, { key: 'cilaos', nom: 'Cilaos' }]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1500,1200'] })
const manifest = []
for (const { key, nom } of COMMUNES) {
  const OUT = ROOT + key + '/'; mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1500, height: 1200 }, deviceScaleFactor: 2 })
  const p = await ctx.newPage(); p.on('pageerror', () => {})
  await p.goto(BASE + `#f=1&v=1&c=${encodeURIComponent(nom)}`, { waitUntil: 'domcontentloaded' })
  await p.reload({ waitUntil: 'domcontentloaded' })
  await p.waitForSelector('[data-contexte-btn]', { timeout: 30000 }); await sleep(800)
  await p.locator('[data-contexte-btn]').click()
  await p.waitForSelector('[data-contexte-panel] details[data-acc="identite"]', { timeout: 20000 })
  // attendre la tendance (requête séparée) puis ouvrir toutes les cartes
  await p.waitForSelector('[data-contexte-panel] >> text=Tendance 12 mois', { timeout: 12000 }).catch(() => {})
  await sleep(1200)
  const cards = await p.evaluate(() => {
    const panel = document.querySelector('[data-contexte-panel]')
    panel.querySelectorAll('details').forEach((d) => { d.open = true })
    return [...panel.querySelectorAll('details[data-acc]')].map((d) => ({
      id: d.getAttribute('data-acc'), titre: (d.querySelector('summary b')?.textContent || '').trim() }))
  })
  await sleep(500)
  // bandeau 6 chiffres
  try { await p.locator('[data-bandeau-chiffres]').screenshot({ path: OUT + '00_bandeau.png' }) } catch (e) {}
  const rec = { commune: nom, key, cards: [] }
  for (const [idx, c] of cards.entries()) {
    const el = p.locator(`[data-contexte-panel] details[data-acc="${c.id}"]`)
    const nn = String(idx + 1).padStart(2, '0')
    const file = `${nn}_${c.id}.png`
    try { await el.scrollIntoViewIfNeeded(); await sleep(120); await el.screenshot({ path: OUT + file }) } catch (e) {}
    rec.cards.push({ id: c.id, titre: c.titre, file })
  }
  // panneau complet
  await p.evaluate(() => {
    const panel = document.querySelector('[data-contexte-panel]')
    panel.style.position = 'static'; panel.style.height = 'auto'; panel.style.maxHeight = 'none'
    panel.querySelectorAll('*').forEach((el) => { const cs = getComputedStyle(el); if (cs.overflowY === 'auto' || cs.overflowY === 'scroll') { el.style.overflow = 'visible'; el.style.maxHeight = 'none'; el.style.height = 'auto' } })
  })
  await sleep(400)
  try { await p.locator('[data-contexte-panel]').screenshot({ path: OUT + 'panel_full.png' }) } catch (e) {}
  rec.n_cards = cards.length; manifest.push(rec)
  console.log(`${nom}: ${cards.length} cartes`)
  await ctx.close()
}
writeFileSync(ROOT + 'manifest.json', JSON.stringify(manifest, null, 1))
await br.close(); console.log('OK — captures/commune-rangement2/')
