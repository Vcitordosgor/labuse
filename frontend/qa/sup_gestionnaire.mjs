// SUP-GESTIONNAIRE-1 — capture du détail d'une SUP (popup au clic). node qa/sup_gestionnaire.mjs <avant|apres>
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'avant'
const OUT = `/Users/openclaw/Desktop/labuse-couches-tuyau/captures/sup-gestionnaire/`
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const SUP = [55.56016, -21.12586, 14.5]   // el10 (littoral) — ST_PointOnSurface de la plus grande assiette
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const explore = p.getByText('Explorer la carte', { exact: false })
if (await explore.count().catch(() => 0)) await explore.first().click().catch(() => {})
await sleep(2500)
// ouvrir « Couches » + activer SUP
const toggle = p.locator('[data-couches-toggle]')
if (await toggle.count()) { const exp = await toggle.first().getAttribute('aria-expanded'); if (exp !== 'true') await toggle.first().click().catch(() => {}) }
await sleep(800)
const sup = p.locator('[data-couches-drawer] [data-layer="sup"]')
if (await sup.count()) { await sup.first().scrollIntoViewIfNeeded().catch(() => {}); await sup.first().click().catch(() => {}) }
await sleep(600)
// aller sur l'assiette SUP
for (let i = 0; i < 6; i++) { await p.evaluate(([lon, lat, z]) => window.__labuse_map.jumpTo({ center: [lon, lat], zoom: z }), SUP); await sleep(700); if (Math.abs(await p.evaluate(() => window.__labuse_map.getZoom()) - SUP[2]) < 0.3) break }
await p.waitForFunction(() => window.__labuse_map.areTilesLoaded(), { timeout: 30000 }).catch(() => {})
await sleep(1500)
// clic au centre (sur l'assiette) → popup couche-detail
await p.mouse.click(720, 500)
await sleep(1200)
// attendre que le fetch /map/couche-detail ait remplacé le placeholder « … »
for (let i = 0; i < 20; i++) { const t = await p.locator('.maplibregl-popup').first().innerText().catch(() => ''); if (t && !/^…$/.test(t.trim())) break; await sleep(400) }
await sleep(500)
const popup = p.locator('.maplibregl-popup')
const hasPopup = await popup.count().catch(() => 0)
const txt = hasPopup ? await popup.first().innerText().catch(() => '') : ''
console.log(`[${PHASE}] popup présent:`, hasPopup, '| contient "Gestionnaire":', /Gestionnaire/i.test(txt))
console.log(`[${PHASE}] texte popup:`, JSON.stringify(txt).slice(0, 400))
if (hasPopup) await popup.first().screenshot({ path: OUT + `sup_${PHASE}.png` }).catch(() => p.screenshot({ path: OUT + `sup_${PHASE}.png`, clip: { x: 500, y: 350, width: 460, height: 320 } }))
else await p.screenshot({ path: OUT + `sup_${PHASE}_nopopup.png`, clip: { x: 360, y: 60, width: 1080, height: 900 } })
await br.close()
console.log('OK', PHASE)
