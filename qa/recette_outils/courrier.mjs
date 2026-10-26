import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
// deep-link : parcelle + outil courrier (prefill destinataire)
await page.goto('http://localhost:6020/socle/#idu=97411000AD0213&m=courriers', { waitUntil: 'networkidle' }).catch(()=>{})
await t.wait(2500)
const btnCharte = await page.locator('[data-courrier-demander]').count()
const vosDemandes = await page.getByText('Vos demandes').count()
const envoiPas = await page.getByText('pas encore disponible').count()
const auDosDoublon = await page.getByText('Au dos — synthèse').count()
await t.shotSel('aside', `P45-48-courrier-${SUF}`)
console.log(JSON.stringify({ SUF, btnCharte, vosDemandes, envoiPas, auDosDoublon }))
await browser.close()
