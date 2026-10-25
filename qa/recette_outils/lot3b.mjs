import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const out = {}
await t.go(''); await t.wait(700)
await page.evaluate(() => window.__labuse.setModule('comparer')); await t.wait(1500)
out.entreeParcelle = await page.locator('[data-entree-parcelle]').count()
out.libre = await page.getByText('+ 1 libre').count()
await t.shotSel('aside', 'P17-comparer-entree-apres')
// Gabarit panel (needs a parcelle; use a Saint-Denis one). Export button appears if gabarit ok.
await page.evaluate(() => window.__labuse.setModule('gabarit')); await t.wait(800)
await page.evaluate(() => window.__labuse.select('97411000BZ0389')); await t.wait(2500)
out.gabExport = await page.locator('[data-gabarit-export]').count()
out.gab3d = await page.locator('[data-gabarit-3d]').count()
await t.shotSel('aside', 'P31-34-gabarit-apres')
console.log(JSON.stringify(out))
await browser.close()
