import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const IDU = '97408000BL0020'
await t.go(''); await t.wait(900)
const out = {}
async function leaveReenter(key) {
  await page.evaluate((k) => window.__labuse.setModule(k), key); await t.wait(1000)
  await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(1800)
  const avant = await page.locator('[data-entree-parcelle-choisie], [data-compare-chip], [data-zone-rayon]').count()
  // sortir vers le menu Outils (comme « ← Outils ») : on bascule module=null puis on rouvre
  await page.evaluate(() => window.__labuse.setModule(null)); await t.wait(700)
  await page.evaluate((k) => window.__labuse.setModule(k), key); await t.wait(1600)
  const apres = await page.locator('[data-entree-parcelle-choisie], [data-compare-chip], [data-zone-rayon]').count()
  return { avant, apresReentree: apres }
}
out.temps = await leaveReenter('temps')
out.etudeZone = await leaveReenter('etude-zone')
out.gabarit = await leaveReenter('gabarit')
out.taxe = await leaveReenter('taxe-amenagement')
console.log(JSON.stringify(out))
await browser.close()
