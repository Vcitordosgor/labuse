import { chromium } from 'playwright'
const OUT = '../../reports/pre-lancement/captures'
const IDU = '97415000CW0658'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 900 } })
await p.goto('http://127.0.0.1:8010/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setModule('courriers'))
await p.waitForSelector('[data-courrier-idu]', { timeout: 8000 })
// étape 1 parcelle
await p.locator('[data-courrier-idu]').fill(IDU)
await p.screenshot({ path: `${OUT}/nuit-courrier-1-parcelle.png` })
await p.locator('[data-courrier-next]').click()
// étape 2 motif
await p.waitForSelector('[data-courrier-motif="indivision"]', { timeout: 5000 })
await p.locator('[data-courrier-motif="indivision"]').click()
await p.screenshot({ path: `${OUT}/nuit-courrier-2-motif.png` })
await p.locator('[data-courrier-next]').click()
// étape 3 rédaction (brouillon groundé éditable)
await p.waitForSelector('[data-courrier-texte]', { timeout: 8000 })
await p.waitForTimeout(800)
const draft = await p.locator('[data-courrier-texte]').inputValue()
console.log('brouillon (extrait):', draft.slice(0, 80).replace(/\n/g,' '))
console.log('brouillon contient un nom de particulier ?', /madame|monsieur/i.test(draft) && !/propriétaire/i.test(draft))
await p.screenshot({ path: `${OUT}/nuit-courrier-3-redaction.png` })
await p.locator('[data-courrier-next]').click()
// étape 4 aperçu + envoyer
await p.waitForSelector('[data-courrier-apercu]', { timeout: 5000 })
await p.screenshot({ path: `${OUT}/nuit-courrier-4-apercu.png` })
await p.locator('[data-courrier-envoyer]').click()
await p.waitForSelector('[data-courrier-done]', { timeout: 8000 })
console.log('confirmation:', (await p.locator('[data-courrier-done]').innerText()).replace(/\s+/g,' '))
await p.screenshot({ path: `${OUT}/nuit-courrier-5-demande.png` })
await b.close(); console.log('courrier captures OK')
