// M30 — reprise capture liste filtrée declasse_bati_sature (verdict allumé, page fraîche)
import { chromium } from 'playwright'
const suffixe = process.argv[2] || 'apres'
const DIR = new URL('../../qa/m30/captures/', import.meta.url).pathname
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })
await p.goto('http://localhost:5173/socle/#v=1&f=1&tv=declasse_bati_sature', { waitUntil: 'networkidle' })
await p.waitForTimeout(4500)
await p.screenshot({ path: `${DIR}liste_declasse_bati_sature_${suffixe}.png` })
console.log('shot liste', suffixe)
await b.close()
