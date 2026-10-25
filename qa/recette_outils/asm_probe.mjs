import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'apres'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
await page.evaluate(() => window.__labuse.setModule('assemblage')); await t.wait(1000)
await page.evaluate(() => window.__labuse.setMsel(['97411000AD0213','97411000AD0214','97411000AD0215'])); await t.wait(1500)
const verif = page.locator('[data-asm-verifier]').first()
if (await verif.count()) { await verif.click(); await t.wait(3000) }
const btn = page.locator('[data-asm-etude]').first()
let btnH = 'absent'
if (await btn.count()) { await btn.scrollIntoViewIfNeeded().catch(()=>{}); await t.wait(400); btnH = Math.round((await btn.boundingBox()).height) }
await t.shotSel('aside', `R3-assemblage-btn-${SUF}`)
console.log(JSON.stringify({ btnH }))
await browser.close()
