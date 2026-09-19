// CIRCUIT-SOURCES-1 lot 3 — preuve : la fiche d'un réservoir dans le Circuit dit TOUT ce qu'il touche,
// en 3 blocs toujours présents. Trois témoins : BD TOPO IGN (17, riche), Géorisques — ICPE (34, après
// réattribution lot 2 : la ligne « Vigilances » apparaît), INSEE RP Logement 2023 (41, commune-seule :
// Couches carte + Lignes fiche vides mais PRÉSENTES, Ailleurs = fiche commune).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5176/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/circuit-sources1/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const TEMOINS = [
  { id: 17, slug: 'bd_topo', nom: 'BD TOPO IGN' },
  { id: 34, slug: 'icpe', nom: 'Géorisques — ICPE' },
  { id: 41, slug: 'insee_rp', nom: 'INSEE RP Logement 2023' },
]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1500,1600'] })
for (const t of TEMOINS) {
  const ctx = await br.newContext({ viewport: { width: 1500, height: 1600 } })
  const p = await ctx.newPage(); p.on('pageerror', () => {})
  await p.goto(BASE + `#admin=1`, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  await sleep(1000)
  // ouvrir la section « Données » (le Circuit) dans le rail admin, puis deep-linker le réservoir
  await p.locator('aside button', { hasText: 'Données' }).first().click().catch(() => {})
  await p.waitForFunction(() => (document.body.innerText || '').includes('réservoir') || document.querySelector('.circuit,.reservoirs'), { timeout: 30000 }).catch(() => {})
  await sleep(800)
  await p.evaluate((id) => { window.location.hash = `#admin=1&cx=reservoir:${id}`; window.dispatchEvent(new HashChangeEvent('hashchange')) }, t.id)
  // le détail réservoir se monte sur le hash — attendre les 3 titres de bloc
  await p.waitForFunction(() => {
    const txt = document.body.innerText || ''
    return txt.includes('Couches carte alimentées') && txt.includes('Lignes de la fiche parcelle') && txt.includes('Ailleurs ·')
  }, { timeout: 60000 }).catch(() => {})
  await sleep(1200)
  const blocs = await p.evaluate(() => {
    const cards = [...document.querySelectorAll('.detail .card h3')].map((h) => h.textContent)
    const grab = (needle) => {
      const h = [...document.querySelectorAll('.detail .card h3')].find((x) => (x.textContent || '').startsWith(needle))
      if (!h) return null
      const card = h.closest('.card')
      const items = [...card.querySelectorAll('li')].map((li) => li.innerText.replace(/\n/g, ' · '))
      const chips = [...card.querySelectorAll('.chip')].map((c) => c.textContent)
      const muted = card.querySelector('.muted') ? card.querySelector('.muted').textContent : null
      return { titre: h.textContent, items, chips, muted }
    }
    return {
      titres: cards,
      couches: grab('Couches carte alimentées'),
      lignes: grab('Lignes de la fiche parcelle'),
      ailleurs: grab('Ailleurs ·'),
    }
  })
  console.log(`\n=== ${t.nom} (réservoir ${t.id}) ===`)
  console.log('  3 blocs présents :',
    !!blocs.couches, '(Couches)', !!blocs.lignes, '(Lignes fiche)', !!blocs.ailleurs, '(Ailleurs)')
  console.log('  Couches carte :', blocs.couches?.chips?.length ? blocs.couches.chips : (blocs.couches?.muted || '?'))
  console.log('  Lignes fiche  :', blocs.lignes?.items?.length ? blocs.lignes.items.slice(0, 6) : (blocs.lignes?.muted || '?'))
  console.log('  Ailleurs      :', blocs.ailleurs?.items?.length ? blocs.ailleurs.items.slice(0, 6) : (blocs.ailleurs?.muted || '?'))
  await p.screenshot({ path: `${OUT}${t.slug}.png`, fullPage: true })
  await ctx.close()
}
await br.close(); console.log('\nDONE')
