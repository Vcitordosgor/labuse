import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const PARC = { idu: '97408000BL0020', c: [55.343843, -20.923575] }  // La Possession
await t.go(''); await t.wait(1200)

async function clicCarte() {
  // amener la parcelle au centre de la carte puis cliquer le canvas en son centre
  await page.evaluate((c) => window.__labuse.setFlyTo({ center: c, zoom: 18.5 }), PARC.c)
  await t.wait(2600)   // vol + tuiles
  const cv = page.locator('.maplibregl-canvas').first()
  const box = await cv.boundingBox()
  if (!box) return false
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
  await t.wait(2200)
  return true
}

const results = {}
const tools = [
  { key: 'risques', check: () => page.locator('[data-entree-parcelle-choisie]').count() },
  { key: 'taxe-amenagement', check: () => page.locator('[data-entree-parcelle-choisie]').count() },
  { key: 'gabarit', check: () => page.locator('[data-entree-parcelle-choisie]').count() },
  { key: 'prospection-solaire', check: () => page.locator('[data-entree-parcelle-choisie]').count(), sub: 'ensoleillement' },
  { key: 'temps', check: () => page.locator('[data-entree-parcelle-choisie]').count() },
  { key: 'comparer', check: () => page.locator('[data-compare-chip]').count() },
  { key: 'etude-zone', check: () => page.locator('[data-entree-parcelle-choisie], [data-zone-rayon]').count() },
]
for (const tool of tools) {
  await page.evaluate((k) => window.__labuse.setModule(k), tool.key)
  await t.wait(900)
  if (tool.sub === 'ensoleillement') { const b = page.locator('[data-solaire-mode="ensoleillement"]').first(); if (await b.count()) { await b.click(); await t.wait(900) } }
  const ok = await clicCarte()
  const n = ok ? await tool.check() : 0
  results[tool.key] = { clicked: ok, picked: n }
  await t.shot(`R1-${tool.key}-apres`)
}
console.log(JSON.stringify(results, null, 0))
await browser.close()
