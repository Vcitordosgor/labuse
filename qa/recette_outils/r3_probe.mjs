import { launch, mk } from './lib.mjs'
const { browser, page, errors } = await launch()
const t = mk(page)
await t.go('#m=plu'); await t.wait(2500)
const voies = await page.locator('[data-plu-voie]').count()
await page.evaluate(() => window.__labuse.setModule('plu')); await t.wait(1500)
const ann = page.locator('[data-plu-voie="annuaire"]').first()
const annCount = await ann.count()
if (annCount) { await ann.click(); await t.wait(1800) }
const nR = await page.locator('[data-retour]').count()
let heights = []
for (let i=0;i<nR;i++){ const b = await page.locator('[data-retour]').nth(i).boundingBox(); heights.push(b?Math.round(b.height):null) }
console.log(JSON.stringify({ voies, annCount, nR, heights, errors: errors.slice(0,3) }))
await browser.close()
