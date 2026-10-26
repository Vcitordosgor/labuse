import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
const out = {}
await page.evaluate(() => window.__labuse.setModule('plu')); await t.wait(1000)
const ann = page.locator('[data-plu-voie="annuaire"]').first(); if (await ann.count()) { await ann.click(); await t.wait(1200) }
const retours = page.locator('[data-retour]'); const nR = await retours.count()
out.outilsH = nR>0 ? Math.round((await retours.nth(0).boundingBox()).height) : null
out.pluRetourH = nR>1 ? Math.round((await retours.nth(1).boundingBox()).height) : null
await t.shotSel('aside', `R3-plu-retour-${SUF}`)
await page.evaluate(() => window.__labuse.setModule('assemblage')); await t.wait(900)
await page.evaluate(() => window.__labuse.setMsel(['97411000AD0213','97411000AD0214'])); await t.wait(2200)
const asm = page.locator('[data-asm-etude]').first()
if (await asm.count()) { await asm.scrollIntoViewIfNeeded().catch(()=>{}); await t.wait(400); out.asmBtnH = Math.round((await asm.boundingBox()).height) }
else out.asmBtnH = 'absent'
await t.shotSel('aside', `R3-assemblage-btn-${SUF}`)
console.log(JSON.stringify(out))
await browser.close()
