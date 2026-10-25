import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const out = {}
await t.go(''); await t.wait(700)
// Comparer entry (17) — EntreeParcelle block + chips, no "+1 libre"
await page.evaluate(() => window.__labuse.setModule('comparer')); await t.wait(1000)
await page.evaluate(() => { window.__labuse.addToCompare?.('97411000AD0213'); window.__labuse.addToCompare?.('97411000AD0214') })
await t.wait(1500)
out.entreeParcelle = await page.locator('[data-entree-parcelle]').count()
out.chips = await page.locator('[data-compare-chip]').count()
out.libre = await page.getByText('+ 1 libre').count()
await t.shotSel('aside', 'P17-comparer-entree-apres')
// open table → export button, no "Retour à la carte"/"Tout vider"
const btn = page.locator('[data-compare-ouvrir]').first()
if (await btn.count()) { await btn.click(); await t.wait(2500) }
out.exportBtn = await page.locator('[data-compare-export]').count()
out.retourCarte = await page.getByText('Retour à la carte').count()
out.toutVider = await page.getByText('Tout vider').count()
await t.shot('P19-21-comparer-table-apres')
console.log(JSON.stringify(out))
await browser.close()
