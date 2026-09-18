// FICHE-COUCHES-2 — fiche de 97410000AN0347 : lot 1. node qa/fiche_couches2.mjs <before|after>
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const PHASE = process.argv[2] || 'after'
const IDU = '97410000AN0347'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/fiche-couches2/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(2500)
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
await sleep(5500)
async function shot(label, texte) {
  try { const h = p.getByText(texte, { exact: false }).first(); await h.scrollIntoViewIfNeeded(); await sleep(400)
    // ouvrir le tiroir si replié
    await h.click().catch(() => {}); await sleep(600) } catch { /* déjà ouvert */ }
  await p.screenshot({ path: OUT + `${PHASE}_${label}.png`, clip: { x: 1010, y: 0, width: 430, height: 1000 } })
  console.log('  →', `${PHASE}_${label}`)
}
// section Risques (compteur + tri_zone/znieff en lot 1) puis Accès (transport_ligne)
await shot('risques', 'Risques et protections')
await shot('acces', 'Accès')
await br.close()
console.log('OK', PHASE)
