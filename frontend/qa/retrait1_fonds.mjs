// COUCHES-RETRAIT-1 lot 1 — captures Sombre/Ortho/Plan IGN. node qa/retrait1_fonds.mjs <avant|apres>
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'avant'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/couches-retrait/${PHASE}/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const V = [55.2735, -21.0095, 15.4]
const OCEAN = [55.20, -21.02, 11.5]
const CLIP = { x: 360, y: 60, width: 1080, height: 900 }
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(3500)
const jump = async (v) => { for (let i = 0; i < 6; i++) { await p.evaluate(([lon, lat, zz]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: zz }), v); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - v[2]) < 0.3) break } await p.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 40000 }).catch(() => {}); await sleep(2200) }
async function fond(label, opt) {
  if (opt) {
    await jump(OCEAN)
    const bm = p.locator('button', { hasText: /Sombre|Ortho|Clair|Plan/ }).first()
    await bm.click().catch(() => {}); await sleep(400)
    await p.getByText(opt, { exact: true }).first().click().catch(() => {}); await sleep(1000)
    await p.mouse.click(180, 320); await sleep(200); await p.mouse.move(720, 500); await sleep(300)
  }
  await jump(V)
  await p.screenshot({ path: OUT + label + '.png', clip: CLIP })
  console.log('  →', label)
}
await fond('sombre', null)          // défaut = Sombre
await fond('ortho', 'Ortho IGN')
await fond('plan', 'Plan IGN')
await br.close()
console.log('OK', PHASE)
