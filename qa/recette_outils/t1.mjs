import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page, errors } = await launch()
const t = mk(page)
await t.go('')
await t.wait(800)
// 1) ouvrir une fiche parcelle via le store
await page.evaluate(() => window.__labuse.select('97411000AD0213'))
await t.wait(1500)
const ficheOuverte = await page.locator('.fiche-v6').count()
await t.shot(`T1-01-fiche-ouverte-${SUF}`)
// 2) basculer vers « Remonter le temps » en session (setModule), SANS fermer la fiche
await page.evaluate(() => window.__labuse.setModule('temps'))
await t.wait(1500)
const ficheResteApresTemps = await page.locator('.fiche-v6').count()
await t.shot(`T1-02-temps-fiche-reste-${SUF}`)
// 3) Permis : saisir une recherche, puis basculer PLU
await page.evaluate(() => window.__labuse.setModule('permis'))
await t.wait(1200)
const champ = page.locator('[data-entree-parcelle] input, input[placeholder*="Adresse"], input[placeholder*="commune"]').first()
let tape = false
if (await champ.count()) { await champ.fill('Saint-Denis').catch(()=>{}); tape = true; await t.wait(500) }
await t.shot(`T1-03-permis-recherche-${SUF}`)
await page.evaluate(() => window.__labuse.setModule('plu'))
await t.wait(1200)
const resteRecherche = await page.evaluate(() => {
  const inputs = [...document.querySelectorAll('input')]
  return inputs.some(i => (i.value||'').includes('Saint-Denis'))
})
await t.shot(`T1-04-plu-apres-permis-${SUF}`)
console.log(JSON.stringify({ SUF, ficheOuverte, ficheResteApresTemps, tape, resteRecherche, errors: errors.slice(0,4) }))
await browser.close()
