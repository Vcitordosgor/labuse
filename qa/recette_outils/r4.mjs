import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'apres'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(900)
// PLU tool : doit ouvrir direct sur l'annuaire, sans voie « Procédure »
await page.evaluate(() => window.__labuse.setModule('plu')); await t.wait(1600)
const out = {}
out.voies = await page.locator('[data-plu-voie]').count()
out.procchgCard = await page.getByText('Procédure & changement').count()
out.annuaire = await page.locator('[data-plu-annuaire], [data-plu-commune]').count()
await t.shotSel('aside', `R4-plu-${SUF}`)
// Fiche parcelle : procédure PLU en cours (Saint-Joseph a du_en_cours=PLU)
await page.evaluate(() => window.__labuse.setModule(null)); await t.wait(400)
await page.evaluate(() => window.__labuse.select('97412000BE0280')); await t.wait(2500)
out.ficheProcedure = await page.getByText(/procédure|révision|en cours/i).count()
await t.shot(`R4-fiche-parcelle-${SUF}`)
console.log(JSON.stringify(out))
await browser.close()
