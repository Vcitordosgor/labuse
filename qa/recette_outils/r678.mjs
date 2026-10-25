import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
const out = {}
await page.evaluate(() => window.__labuse.setModule('temps')); await t.wait(1200)
out.r6_temps = await page.getByText("La parcelle d'abord").count()
await t.shotSel('aside','R6-temps-apres')
await page.evaluate(() => window.__labuse.setModule('courriers')); await t.wait(1500)
out.r7_courrier = await page.getByText("procède à l'envoi").count()
await page.evaluate(() => window.__labuse.setView('documents')); await t.wait(1500)
out.r8_docs = await page.getByText("Les 19 lignes de Comparer").count()
console.log(JSON.stringify(out))
await browser.close()
