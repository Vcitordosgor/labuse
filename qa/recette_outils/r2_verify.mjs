import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
const IDU = '97408000BL0020'
await t.go(''); await t.wait(900)
const out = {}
// (A) leave via "← Outils" → fiche doit disparaître dans le menu
for (const key of ['temps','etude-zone','gabarit','risques']) {
  await page.evaluate((k) => window.__labuse.setModule(k), key); await t.wait(900)
  await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(1600)
  const retour = page.locator('[data-retour]').first(); if (await retour.count()) await retour.click()
  await t.wait(900)
  const ficheDansMenu = await page.locator('.fiche-v6').count()
  // rouvrir
  const card = page.locator(`[data-outil="${key}"]`).first(); if (await card.count()) await card.click()
  await t.wait(1500)
  const picked = await page.locator('[data-entree-parcelle-choisie], .fiche-v6').count()
  out[key] = { ficheDansMenu, apresReentree: picked }
}
// (B) direct tool→tool : Gabarit(A) → Étude → doit être vide
await page.evaluate((k) => window.__labuse.setModule(k), 'gabarit'); await t.wait(800)
await page.evaluate((i) => window.__labuse.select(i), IDU); await t.wait(1500)
await page.evaluate((k) => window.__labuse.setModule(k), 'etude-zone'); await t.wait(1500)
out.directGabEtude = { etudeCible: await page.getByText('Parcelle :').count(), fiche: await page.locator('.fiche-v6').count() }
console.log(JSON.stringify(out))
await browser.close()
