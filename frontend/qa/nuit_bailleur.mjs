import { chromium } from 'playwright'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 900 } })
await p.goto('http://127.0.0.1:8010/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setCommune, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setCommune('Saint-Leu'))
await p.evaluate(() => window.__labuse.setModule('bailleur'))
await p.waitForSelector('[data-bailleur-sru]', { timeout: 10000 })
await p.waitForTimeout(1500)
console.log('SRU card:', (await p.locator('[data-bailleur-sru]').innerText()).replace(/\s+/g,' '))
await p.screenshot({ path: `${OUT}/nuit-bailleur-sru.png` })
await b.close(); console.log('bailleur capture OK')
