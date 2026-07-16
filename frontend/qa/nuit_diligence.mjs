import { chromium } from 'playwright'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 950 } })
await p.goto('http://127.0.0.1:8010/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setModule('duediligence'))
await p.waitForSelector('textarea', { timeout: 8000 })
await p.locator('textarea').fill('97401000AI1188\n97402000AD1052')
await p.locator('button:has-text("Analyser le lot")').click()
await p.waitForSelector('[data-diligence-risque]', { timeout: 10000 })
await p.waitForTimeout(1000)
await p.screenshot({ path: `${OUT}/nuit-diligence-checklist.png` })
await b.close(); console.log('diligence capture OK')
