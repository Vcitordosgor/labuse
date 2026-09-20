// COMMUNE-AUDIT-1 — preuve : fiche commune dépliée (toutes les cartes ouvertes) sur 2 témoins,
// une grande (Saint-Denis) et une petite (Cilaos). Panneau [data-contexte-panel], cartes = <details
// data-acc>. Ouverture via hash #f=1&v=1&c=<commune> + clic [data-contexte-btn]. Chaque carte est
// screenshotée dépliée (element.screenshot) + une vue panneau complète (scroll interne neutralisé).
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
const BASE = process.env.BASE || 'http://localhost:5299/socle/'
const ROOT = '/Users/openclaw/Desktop/labuse/captures/commune-audit/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const COMMUNES = [
  { key: 'saint-denis', nom: 'Saint-Denis' },
  { key: 'cilaos', nom: 'Cilaos' },
]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1500,1100'] })
const manifest = []
for (const { key, nom } of COMMUNES) {
  const OUT = ROOT + key + '/'
  mkdirSync(OUT, { recursive: true })
  const ctx = await br.newContext({ viewport: { width: 1500, height: 1100 }, deviceScaleFactor: 2 })
  const p = await ctx.newPage()
  p.on('pageerror', () => {})
  await p.goto(BASE + `#f=1&v=1&c=${encodeURIComponent(nom)}`, { waitUntil: 'domcontentloaded' })
  await p.reload({ waitUntil: 'networkidle' })
  await p.waitForSelector('[data-contexte-btn]', { timeout: 30000 })
  await sleep(800)
  await p.locator('[data-contexte-btn]').click()
  await p.waitForSelector('[data-contexte-panel]', { timeout: 15000 })
  await sleep(1500)
  // ouvrir toutes les cartes (details) + neutraliser le scroll interne pour capturer toute la hauteur
  const cards = await p.evaluate(() => {
    const panel = document.querySelector('[data-contexte-panel]')
    if (!panel) return []
    panel.querySelectorAll('details').forEach((d) => { d.open = true })
    // liste des cartes (data-acc) avec leur titre
    return [...panel.querySelectorAll('details[data-acc]')].map((d, i) => ({
      idx: i, id: d.getAttribute('data-acc'),
      titre: (d.querySelector('summary b')?.textContent || '').trim(),
    }))
  })
  await sleep(500)
  const rec = { commune: nom, key, cards: [] }
  // par carte : screenshot de l'element details déplié
  for (const c of cards) {
    const el = p.locator(`[data-contexte-panel] details[data-acc="${c.id}"]`)
    const nn = String(c.idx + 1).padStart(2, '0')
    const file = `${nn}_${c.id}.png`
    try { await el.scrollIntoViewIfNeeded(); await sleep(120); await el.screenshot({ path: OUT + file }) }
    catch (e) { /* carte hors flux */ }
    rec.cards.push({ id: c.id, titre: c.titre, file })
  }
  // vue panneau complète : on déplie l'aside en hauteur auto + le conteneur scrollable en overflow visible
  await p.evaluate(() => {
    const panel = document.querySelector('[data-contexte-panel]')
    if (!panel) return
    panel.style.position = 'static'; panel.style.height = 'auto'; panel.style.maxHeight = 'none'
    panel.querySelectorAll('*').forEach((el) => {
      const cs = getComputedStyle(el)
      if (cs.overflowY === 'auto' || cs.overflowY === 'scroll') { el.style.overflow = 'visible'; el.style.maxHeight = 'none'; el.style.height = 'auto' }
    })
  })
  await sleep(400)
  try { await p.locator('[data-contexte-panel]').screenshot({ path: OUT + 'panel_full.png' }) } catch (e) {}
  rec.n_cards = cards.length
  manifest.push(rec)
  console.log(`${nom}: ${cards.length} cartes capturées`)
  await ctx.close()
}
writeFileSync(ROOT + 'manifest.json', JSON.stringify(manifest, null, 1))
await br.close()
console.log('OK — captures/commune-audit/{saint-denis,cilaos}/')
