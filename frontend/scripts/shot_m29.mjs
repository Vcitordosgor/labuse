import { chromium } from 'playwright'
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })
for (const [idu, out] of [['97409000AR2714','/tmp/temoin_9.png'],['97413000CX2538','/tmp/temoin_11.png']]) {
  await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
  await p.waitForFunction(() => !!window.__labuse, null, { timeout: 15000 }).catch(()=>{})
  await p.evaluate((i) => { window.__labuse?.setView('cartes'); window.__labuse?.select(i) }, idu)
  await p.waitForSelector('[data-fiche-idu]', { timeout: 15000 })
  await p.waitForTimeout(2500)
  await p.locator('aside:has([data-fiche-idu])').first().screenshot({ path: out })
  console.log('shot', out)
}
await b.close()
