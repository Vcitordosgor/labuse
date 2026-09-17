// Sombre inchangé : capture même viewport, toast attendu (fondu), + lecture du paint parcelles.
// node qa/style6_sombre.mjs <avant|apres>
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'apres'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/style6/sombre_cmp/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const CENTER = [55.2735, -21.0095, 16.2]
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(3500)
await p.evaluate(() => window.__labuse.setTuyauActives({ limites_communes: true, limites_parcelles: true }))
for (let i = 0; i < 6; i++) { await p.evaluate(([a, b, c]) => window.__labuse_map.jumpTo({ center: [a, b], zoom: c }), CENTER); await sleep(900); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - CENTER[2]) < 0.3) break }
await sleep(8000)   // laisse le toast « Votre carte va changer… » se fondre
const paint = await p.evaluate(() => { const m = window.__labuse_map, id = 'tuyau-limites_parcelles-outline'; return { color: m.getPaintProperty(id, 'line-color'), width: m.getPaintProperty(id, 'line-width'), opacity: m.getPaintProperty(id, 'line-opacity') } })
console.log(PHASE, 'parcelles Sombre =', JSON.stringify(paint))
await p.screenshot({ path: OUT + PHASE + '.png', clip: { x: 360, y: 60, width: 1080, height: 900 } })
await br.close()
console.log('OK', PHASE)
