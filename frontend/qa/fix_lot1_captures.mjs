// FIX LOT 1 — captures C (compteurs APER/tertiaire), D (patrimoine vide), E (simulateur cliquable).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 950 } })
async function open() { await p.goto(BASE, { waitUntil: 'networkidle' }); await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 }) }

// C1 — Parkings APER : compteur 736
await open()
await p.evaluate(() => window.__labuse.setModule('parkings-aper'))
await p.waitForFunction(() => document.body.innerText.includes('parkings assujettis'), { timeout: 15000 })
await p.waitForTimeout(800)
console.log('APER header:', (await p.locator('text=parkings assujettis').first().innerText()).replace(/\s+/g, ' '))
await p.screenshot({ path: `${OUT}/fixC-aper-736.png` })

// C2 — Toitures tertiaires : compteur 9 635
await p.evaluate(() => window.__labuse.setModule('toitures-tertiaires'))
await p.waitForFunction(() => document.body.innerText.includes('toitures'), { timeout: 15000 })
await p.waitForTimeout(800)
console.log('Tertiaire header:', (await p.locator('text=toitures').first().innerText()).replace(/\s+/g, ' '))
await p.screenshot({ path: `${OUT}/fixC-tertiaire-9635.png` })

await b.close()
console.log('captures C OK')
