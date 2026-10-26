import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
await t.go('')              // charge l'app une fois
await t.wait(700)
const nav = async (key, name, waits=1500) => {
  await page.evaluate((k) => window.__labuse.setModule(k), key)
  await t.wait(waits)
  await t.shotSel('aside', `${name}-${SUF}`)
}
await nav('taxe-amenagement', 'P35-taxe')
await nav('blocs-fonciers', 'P40-blocs')
await nav('successions', 'P44-successions')
await nav('comparer', 'P18-comparer')
console.log('sweep done', SUF)
await browser.close()
