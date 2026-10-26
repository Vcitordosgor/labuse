import { launch, mk } from './lib.mjs'
const { browser, page, errors } = await launch()
const t = mk(page)
// Ouvrir une fiche parcelle depuis la recherche, puis aller dans Remonter le temps.
await t.go('')
// recherche globale → ouvrir une fiche
await t.go('#idu=97411000AD0213')         // deep-link fiche si supporté
await t.wait(1500)
await t.shot('T1-01-fiche-ouverte-avant')
const ficheVisibleAvant = await page.locator('[data-fiche], [data-fiche-panel], text=14 Rue de Nice').count()
// Basculer vers Remonter le temps SANS fermer la fiche
await t.go('#m=temps')
await t.wait(1500)
await t.shot('T1-02-temps-avant')
const ficheResteTemps = await page.locator('text=14 Rue de Nice, [data-fiche-panel]').count()
// Permis → PLU test
await t.go('#m=permis'); await t.wait(1200)
// taper une recherche dans permis si champ présent
const champ = page.locator('[data-entree-parcelle] input, input[placeholder*="Adresse"]').first()
if (await champ.count()) { await champ.fill('Saint-Denis').catch(()=>{}); await t.wait(600) }
await t.shot('T1-03-permis-recherche-avant')
await t.go('#m=plu'); await t.wait(1200)
await t.shot('T1-04-plu-apres-permis-avant')
console.log(JSON.stringify({ ficheVisibleAvant, ficheResteTemps, errors: errors.slice(0,5) }))
await browser.close()
