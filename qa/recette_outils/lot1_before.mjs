import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
await t.go(''); await t.wait(700)
const IDU = '97411000AD0213'
const navPick = async (key, name, waits=1600) => {
  await page.evaluate((k) => window.__labuse.setModule(k), key)
  await t.wait(600)
  await page.evaluate((i) => window.__labuse.select(i), IDU)
  await t.wait(3500)
  await t.shotSel('aside', `${name}-${SUF}`)
}
const navOnly = async (key, name, waits=1600) => {
  await page.evaluate((k) => window.__labuse.setModule(k), key)
  await t.wait(waits)
  await t.shotSel('aside', `${name}-${SUF}`)
}
// T4/T5 outils à parcelle
await navPick('taxe-amenagement', 'T5-taxe')
await navPick('gabarit', 'T5-gabarit')
await navPick('risques', 'T4-risques')
// T5 outils à filtres
await navOnly('blocs-fonciers', 'T5-blocs')
await navOnly('successions', 'T5-successions')
await navOnly('permis', 'T5-permis')
// Assemblage (point 16) — bouton Étude (besoin d'une assiette) : capture simple du panneau
await navOnly('assemblage', 'P16-assemblage')
console.log('lot1 before sweep done', SUF)
await browser.close()
