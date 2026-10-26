import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const IDU = '97408000BL0020'
await t.go(''); await t.wait(900)
async function flow(key, indicator) {
  await page.evaluate((k) => window.__labuse.setModule(k), key); await t.wait(1000)
  await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(1800)
  const avant = await page.locator(indicator).count()
  // « ← Outils » : la 1re pastille de retour (PanelRetour)
  const retour = page.locator('[data-retour]').first()
  if (await retour.count()) { await retour.click(); await t.wait(900) }
  // rouvrir l'outil depuis le menu
  const card = page.locator(`[data-outil="${key}"]`).first()
  if (await card.count()) { await card.click(); await t.wait(1700) }
  const apres = await page.locator(indicator).count()
  const ficheReste = await page.locator('.fiche-v6').count()
  return { avant, apresReentree: apres, ficheReste }
}
const out = {}
out.temps = await flow('temps', '[data-entree-parcelle-choisie]')
out.etudeZone = await flow('etude-zone', 'text=Parcelle :')
console.log(JSON.stringify(out))
await browser.close()
