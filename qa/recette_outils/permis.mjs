import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(700)
await page.evaluate(() => window.__labuse.setCommune('Saint-Denis'))
await page.evaluate(() => window.__labuse.setModule('permis'))
await t.wait(2600)
const toggle = page.locator('[data-permis-bloc-toggle="liste"]').first()
if (await toggle.count()) { await toggle.click(); await t.wait(2200) }
const rows = page.locator('[data-permis-row][data-geocode="1"]')
const n = await rows.count()
let clicked = false
if (n > 0) { await rows.first().scrollIntoViewIfNeeded().catch(()=>{}); await rows.first().click(); clicked = true; await t.wait(2800) }
const bulle = await page.locator('.maplibregl-popup').count()
const modal = await page.locator('[data-permis-drawer]').count()
const rowActive = await page.locator('[data-permis-actif="1"]').count()
await t.shot(`P6-7-permis-${SUF}`)
console.log(JSON.stringify({ SUF, nRows: n, clicked, bulle, modal, rowActive }))
await browser.close()
