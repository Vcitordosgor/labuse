// M30 — reprise capture popover « + Filtre » (le popover s'ouvre à DROITE du header)
import { chromium } from 'playwright'
const suffixe = process.argv[2] || 'apres'
const DIR = new URL('../../qa/m30/captures/', import.meta.url).pathname
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })
await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
await p.getByText('+ Filtre').first().click()
await p.waitForTimeout(800)
await p.screenshot({ path: `${DIR}popover_filtres_${suffixe}.png`, clip: { x: 560, y: 0, width: 880, height: 900 } })
console.log('shot popover', suffixe)
await b.close()
