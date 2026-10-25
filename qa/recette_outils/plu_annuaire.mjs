import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page, errors } = await launch()
const t = mk(page)
await t.go('#m=plu'); await t.wait(900)
const ann = page.locator('[data-plu-voie="annuaire"]').first()
if (await ann.count()) { await ann.click(); await t.wait(1600) }
const sentence = await page.locator('text=Cliquez sur la commune').count()
const retInterneListe = await page.locator('[data-retour]').count()  // 1 = Outils ; 2 = Outils+Retour
await t.shotSel('aside', `PLU-annuaire-liste-${SUF}`)
// entrer dans Saint-Denis (insee 97411)
const sd = page.locator('[data-plu-commune="97411"]').first()
if (await sd.count()) { await sd.click(); await t.wait(1500) }
else { const any = page.locator('[data-plu-commune]').first(); if (await any.count()) { await any.click(); await t.wait(1500) } }
const placeholder = await page.locator('[data-plu-q]').getAttribute('placeholder').catch(()=>null)
const retCommune = await page.locator('[data-retour]').count()
await t.shotSel('aside', `PLU-annuaire-commune-${SUF}`)
console.log(JSON.stringify({ SUF, sentence, retInterneListe, placeholder, retCommune, errors: errors.slice(0,3) }))
await browser.close()
