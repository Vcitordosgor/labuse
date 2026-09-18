import { chromium } from 'playwright'
import { mkdirSync, readFileSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-sources-audit/captures/sources-audit/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const temoins = JSON.parse(readFileSync('/tmp/temoins_couches.json','utf8'))
// repères hors spatial_layers
temoins['limites_parcelles'] = [55.4489, -20.8907, 17]
temoins['zonage_parcelle']   = [55.4489, -20.8907, 17]
temoins['limites_communes']  = [55.536, -21.115, 9]
const only = process.argv.slice(2) // optional subset
const kinds = (only.length ? only : Object.keys(temoins)).filter(k => temoins[k])

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1200)
const ex = p.getByText('Explorer la carte', { exact: false })
if (await ex.count().catch(() => 0)) { await ex.first().click().catch(() => {}); await sleep(3500) }
await p.waitForSelector('canvas.maplibregl-canvas', { timeout: 30000 }).catch(()=>{})
await sleep(1500)

let ok=0, fail=[]
for (const k of kinds) {
  const [lon,lat,z] = temoins[k]
  try {
    await p.evaluate((kk) => window.__labuse.setTuyauActives({[kk]: true}), k)
    await sleep(300)
    await p.evaluate(({lon,lat,z}) => window.__labuse.setFlyTo({ center:[lon,lat], zoom:z }), {lon,lat,z})
    await sleep(3200) // tiles
    await p.screenshot({ path: OUT + `couche_${k}.png` })
    ok++; console.log('OK', k, lon, lat, z)
  } catch(e) { fail.push(k); console.log('FAIL', k, e.message) }
}
console.log('COUCHES done', ok, 'fail', JSON.stringify(fail))
await br.close()
