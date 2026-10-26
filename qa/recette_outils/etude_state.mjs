import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(1200)
// résoudre une parcelle (clic carte simulé = select) + définir la zone
await page.evaluate(() => window.__labuse.select('97408000BL0020')); await t.wait(1500)
// EtudeZone n'adopte pas selectedIdu : il faut taper dans son ParcelInput ou setCible. Essayons le prefill store.
await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(600)
// définir la zone via le ParcelInput (taper l'IDU)
const inp = page.locator('[data-zone-point] input, input[placeholder*="Adresse"]').first()
if (await inp.count()) { await inp.fill('97408000BL0020'); await t.wait(1200); await page.keyboard.press('Enter'); await t.wait(800) }
const exportTop = await page.locator('[data-etude-export]').count()
const sections = await page.locator('[data-zone-section]').count()
await t.shotSel('aside','R9-11-etude-apres')
console.log(JSON.stringify({ exportTop, sections }))
await browser.close()
