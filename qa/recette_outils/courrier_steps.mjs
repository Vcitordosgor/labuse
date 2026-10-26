import { launch, mk } from './lib.mjs'
const { browser, page } = await launch()
const t = mk(page)
await page.goto('http://localhost:6020/socle/#idu=97411000AD0213&m=courriers', { waitUntil: 'networkidle' }).catch(()=>{})
await t.wait(2500)
// step 1 → 2 (Relire)
let b = page.getByRole('button', { name: /Relire/ }).first()
if (await b.count()) { await b.click(); await t.wait(2500) }
const auDosDoublon = await page.getByText('Au dos — synthèse').count()
const auDosNeutre = await page.getByText('Au dos', { exact: true }).count()
await t.shotSel('aside', 'P46-courrier-apercu-apres')
// step 2 → 3 (Vérifier/Envoi)
b = page.getByRole('button', { name: /Vérifier|Envoi|Suivant|Continuer/ }).first()
if (await b.count()) { await b.click(); await t.wait(2000) }
const btnCharte = await page.locator('[data-courrier-demander]').count()
const vosDemandes = await page.getByText('Vos demandes').count()
await t.shotSel('aside', 'P47-48-courrier-envoi-apres')
console.log(JSON.stringify({ auDosDoublon, auDosNeutre, btnCharte, vosDemandes }))
await browser.close()
