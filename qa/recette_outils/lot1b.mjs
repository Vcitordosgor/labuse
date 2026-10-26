import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
const IDU = '97411000AD0213'
await t.go(''); await t.wait(700)
// --- Solaire Piscines résultat (T7 footer + single Retour, point 37) ---
await page.evaluate(() => window.__labuse.setModule('prospection-solaire')); await t.wait(1000)
const pisc = page.locator('[data-solaire-mode="piscines"]').first()
if (await pisc.count()) { await pisc.click(); await t.wait(1200) }
const ile = page.locator('[data-piscines-perim="ile"]').first()
if (await ile.count()) { await ile.click(); await t.wait(2500) }
const retCount = await page.locator('[data-retour]').count()
await t.shotSel('aside', `P37-piscines-${SUF}`)
// --- Solaire Ensoleillement (point 38) ---
await page.evaluate(() => window.__labuse.setModule('prospection-solaire')); await t.wait(900)
const ens = page.locator('[data-solaire-mode="ensoleillement"]').first()
if (await ens.count()) { await ens.click(); await t.wait(1000) }
await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(2500)
const ficheOuverte = await page.locator('.fiche-v6').count()
await t.shotSel('aside', `P38-ensoleillement-${SUF}`)
// --- Copilote (point 52) ---
await page.evaluate(() => window.__labuse.setView('copilote')); await t.wait(1500)
await t.shot(`P52-copilote-${SUF}`)
// --- Successions cards (point 43) ---
await page.evaluate(() => window.__labuse.setModule('successions')); await t.wait(2500)
await t.shotSel('aside', `P43-successions-${SUF}`)
console.log(JSON.stringify({ SUF, retCount, ficheOuverte }))
await browser.close()
