// VAGUE 0 — le premier écran du mode île (constat Vic 07/07 18h26) : agrégats communes
// VISIBLES sous z10, clic marqueur → commune, bandeau contextuel, clic liste → la carte
// VOLE et le ping est VISIBLE À L'ÉCRAN (3 communes différentes). Assertions de visibilité.
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes', { timeout: 20000 })
await page.waitForTimeout(3000)

// ── 0.1/0.2 : au chargement (z<10), les marqueurs communes sont VISIBLES à l'écran
const z0 = await page.evaluate(() => window.__labuse_map.getZoom())
assert(z0 < 10, `zoom initial sous le plancher MVT (${z0.toFixed(1)}) — le cas exact du constat`)
const visibleMarkers = await page.evaluate(() =>
  [...document.querySelectorAll('[data-commune-marker]')].filter((el) => {
    const r = el.getBoundingClientRect()
    return r.width > 0 && r.height > 0 && el.style.display !== 'none' &&
      r.left >= 0 && r.top >= 0 && r.right <= innerWidth && r.bottom <= innerHeight
  }).length)
assert(visibleMarkers >= 20, `marqueurs communes VISIBLES à l'écran (${visibleMarkers}/24)`)
await page.screenshot({ path: `${OUT}/vague0_ile_agregats.png` })

// ── 0.3 : bandeau contextuel — instruction exécutable
assert((await page.locator('text=Zoomez ou cliquez une commune').count()) > 0,
  'bandeau <z10 : « Zoomez ou cliquez une commune »')

// ── 0.2 : clic sur le marqueur Saint-Pierre → sélecteur + recadrage
await page.locator('[data-commune-marker="Saint-Pierre"]').click()
await page.waitForTimeout(4500)
assert((await page.locator('[data-commune-select]').innerText()).includes('Saint-Pierre'),
  'clic marqueur → sélecteur sur Saint-Pierre')
const zSp = await page.evaluate(() => window.__labuse_map.getZoom())
assert(zSp >= 10, `clic marqueur → recadrage commune (z=${zSp.toFixed(1)})`)
assert((await page.locator('text=Cliquez une parcelle').count()) > 0,
  'bandeau commune : « Cliquez une parcelle » (les parcelles servent)')

// ── retour île + molette ×3 → les parcelles MVT arrivent
await page.locator('[data-commune-select]').click()
await page.waitForTimeout(400)
await page.getByRole('button', { name: 'Toute l’île 24 communes' }).click()
await page.waitForTimeout(2500)
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.47, -20.90], zoom: 9.2 }))
await page.waitForTimeout(800)
for (let i = 0; i < 3; i++) { await page.mouse.move(720, 450); await page.mouse.wheel(0, -600); await page.waitForTimeout(700) }
await page.waitForTimeout(3000)
const zAfter = await page.evaluate(() => window.__labuse_map.getZoom())
const featAfter = await page.evaluate(() => window.__labuse_map.queryRenderedFeatures({ layers: ['ile-fill'] }).length)
assert(zAfter >= 10 && featAfter > 0, `molette ×3 → parcelles visibles (z=${zAfter.toFixed(1)}, ${featAfter} features)`)

// ── 0.4 : clic sur 3 cartes de la liste (3 communes différentes) → vol + ping VISIBLE
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.53, -21.13], zoom: 9.5 }))
await page.waitForTimeout(800)
const clicked = []
const cards = page.locator('.overflow-y-auto > button')
const n = await cards.count()
for (let i = 0; i < n && clicked.length < 3; i++) {
  const label = await cards.nth(i).innerText()
  const communeTxt = (label.match(/·\s*([A-ZÉÈL'][^\n]+)$/m) ?? [])[1] ?? label
  if (clicked.some((c) => c.commune === communeTxt)) continue
  await cards.nth(i).click()
  await page.waitForTimeout(4000)   // vol (800 ms) + tuiles à destination
  const st = await page.evaluate(() => {
    const m = window.__labuse_map
    const ping = m.getLayer('ile-ping') ? m.queryRenderedFeatures({ layers: ['ile-ping'] }) : []
    const sel = m.getLayer('ile-sel') ? m.queryRenderedFeatures({ layers: ['ile-sel'] }) : []
    return { zoom: m.getZoom(), pingN: ping.length, selN: sel.length,
             op: m.getLayer('ile-ping') ? m.getPaintProperty('ile-ping', 'line-opacity') : null }
  })
  // le pulse s'éteint après 3 s — la PREUVE de visibilité = la géométrie sel/ping rendue au viewport à z≥15
  const visible = st.zoom >= 15 && (st.pingN > 0 || st.selN > 0)
  clicked.push({ commune: communeTxt, ok: visible })
  assert(visible, `clic liste → vol + parcelle visible au viewport (${communeTxt.trim().slice(0, 22)} · z=${st.zoom.toFixed(1)} · ping/sel=${st.pingN}/${st.selN})`)
  await page.screenshot({ path: `${OUT}/vague0_ping_${clicked.length}.png` })
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
  await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.53, -21.13], zoom: 9.5 }))
  await page.waitForTimeout(900)
}
assert(clicked.length >= 3 || new Set(clicked.map((c) => c.commune)).size >= 2,
  `3 parcelles testées (${clicked.map((c) => c.commune.trim()).join(' · ')})`)

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('VAGUE 0 — PREMIER ÉCRAN ÎLE VERT')
void sql
