import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
const IDU = '97408000BL0020', C = [55.343843, -20.923575]
await t.go(''); await t.wait(900)
// R1 — risques : clic carte → doit afficher « Changer de parcelle » (after) / rien (before)
await page.evaluate((k) => window.__labuse.setModule(k), 'risques'); await t.wait(900)
await page.evaluate((c) => window.__labuse.setFlyTo({ center: c, zoom: 18.5 }), C); await t.wait(2600)
const cv = page.locator('.maplibregl-canvas').first(); const box = await cv.boundingBox()
await page.mouse.click(box.x + box.width/2, box.y + box.height/2); await t.wait(2000)
await t.shotSel('aside', `R1-risques-${SUF}`)
// R2 — fiche qui reste dans le menu Outils après « ← Outils »
await page.evaluate((k) => window.__labuse.setModule(k), 'etude-zone'); await t.wait(900)
await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(1600)
const r = page.locator('[data-retour]').first(); if (await r.count()) await r.click(); await t.wait(1000)
await t.shot(`R2-menu-${SUF}`)
await browser.close()
