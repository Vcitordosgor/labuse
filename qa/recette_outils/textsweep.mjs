import { launch, mk } from './lib.mjs'
const SUF = process.argv[2] || 'avant'
const { browser, page } = await launch()
const t = mk(page)
const grab = async (hash, name, waits=1400) => { await t.go(hash); await t.wait(waits); await t.shotSel('aside', `${name}-${SUF}`) }
await grab('#m=taxe-amenagement', 'P35-taxe')
await grab('#m=blocs-fonciers', 'P40-blocs')
await grab('#m=successions', 'P44-successions')
await grab('#m=comparer', 'P18-comparer')
console.log('sweep done', SUF)
await browser.close()
