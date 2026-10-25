import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(700)
await page.evaluate(() => window.__labuse.setModule('blocs-fonciers')); await t.wait(1200)
await t.shotSel('aside', `P39-blocs-filtres-${SUF}`)
const voir = page.locator('[data-blocs-voir]').first()
if (await voir.count()) { await voir.click(); await t.wait(2800) }
const cards = await page.locator('[data-bloc-row]').count()
const smallScan = await page.locator('[data-bloc-scan]').count()
const resume = await page.locator('[data-blocs-filtres-resume]').count()
await t.shotSel('aside', `P41-blocs-listing-${SUF}`)
console.log(JSON.stringify({ SUF, cards, smallScan, resume }))
await browser.close()
