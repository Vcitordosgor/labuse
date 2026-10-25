import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'apres'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
await page.evaluate(() => window.__labuse.setModule('etude-zone')); await t.wait(1200)
await t.shotSel('aside', `R10-activite-${SUF}`)
await page.evaluate(() => window.__labuse.select('97411000AD0213')); await t.wait(2500)
const lire = page.getByRole('button', { name: /Lire la zone/ }).first()
if (await lire.count()) { await lire.click(); await t.wait(6000) }
const sections = await page.locator('[data-zone-section]').count()
const exportBtn = await page.locator('[data-etude-export]').count()
// chevrons fermés par défaut : ouvrir le 1er pour voir l'orientation
await t.shotSel('aside', `R11-etude-chevrons-${SUF}`)
// scroll bas → bouton export après Dynamique
await page.evaluate(() => { const a = document.querySelector('[data-etude-zone]'); if (a) a.scrollTop = a.scrollHeight })
await t.wait(600)
const exportBox = exportBtn ? await page.locator('[data-etude-export]').first().boundingBox() : null
await t.shotSel('aside', `R9-etude-export-${SUF}`)
console.log(JSON.stringify({ sections, exportBtn, exportY: exportBox?Math.round(exportBox.y):null }))
await browser.close()
