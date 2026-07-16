import { chromium } from 'playwright'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 900 } })
await p.goto('http://127.0.0.1:8010/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setModule('velocite'))
await p.waitForTimeout(2500)
await p.screenshot({ path: `${OUT}/nuit-velocite-classement.png` })
await b.close(); console.log('velocite capture OK')
