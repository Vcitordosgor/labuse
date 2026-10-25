import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page, errors } = await launch()
const t = mk(page)
await t.go('#m=plu'); await t.wait(1000)
await t.shotSel('aside', `PLU-hub-${SUF}`)
// Procédure & changement
const proc = page.locator('[data-plu-voie="procchg"]').first()
if (await proc.count()) { await proc.click(); await t.wait(1400) }
const parTab = await page.locator('[data-procchg-tab="parcelle"]').count()
const retoursProc = await page.locator('[data-retour]').count()
await t.shotSel('aside', `PLU-procchg-${SUF}`)
// retour au hub
const ret = page.locator('[data-retour]').first()
if (await ret.count()) { await ret.click(); await t.wait(900) }
// Annuaire
const ann = page.locator('[data-plu-voie="annuaire"]').first()
if (await ann.count()) { await ann.click(); await t.wait(1500) }
const sentence = await page.locator('text=Cliquez sur la commune').count()
const retoursListe = await page.locator('[data-retour]').count()
await t.shotSel('aside', `PLU-annuaire-liste-${SUF}`)
// entrer dans une commune (Saint-Denis)
const sd = page.locator('[data-plu-commune], button:has-text("Saint-Denis")').first()
if (await sd.count()) { await sd.click().catch(()=>{}); await t.wait(1400) }
const placeholder = await page.locator('[data-plu-q]').getAttribute('placeholder').catch(()=>null)
const retoursCommune = await page.locator('[data-retour]').count()
await t.shotSel('aside', `PLU-annuaire-commune-${SUF}`)
console.log(JSON.stringify({ SUF, parTab, retoursProc, sentence, retoursListe, placeholder, retoursCommune, errors: errors.slice(0,3) }))
await browser.close()
