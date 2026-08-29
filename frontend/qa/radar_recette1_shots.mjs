// RADAR-RECETTE-1 — capture de la fiche « À QUALIFIER » (D1c : bien incohérent visible, marqué,
// motifs consultables, non rattaché). Usage : node qa/radar_recette1_shots.mjs (uvicorn + vite up).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = '/Users/openclaw/Desktop/labuse/docs/PIGE/captures'
mkdirSync(OUT, { recursive: true })
const BASE = process.env.BASE || 'http://127.0.0.1:5174/socle/'
const EXE = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const b = await chromium.launch({ executablePath: EXE })

async function scene(name, w, h, fn) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  try { await fn(p); await p.screenshot({ path: `${OUT}/${name}.png` }); console.log(`✓ ${name}`) }
  catch (e) { try { await p.screenshot({ path: `${OUT}/${name}.png` }) } catch {} console.log(`⚠ ${name}: ${String(e).split('\n')[0]}`) }
  finally { await p.close() }
}
const go = async (p, hash = '') => { await p.goto(BASE + hash, { waitUntil: 'networkidle', timeout: 60000 }); await p.waitForTimeout(1500) }

async function fiche(p) {
  await go(p, '#radar=1'); await p.waitForTimeout(1000)
  const card = p.locator('[data-radar-bien="5086"]')
  if (await card.count()) { await card.scrollIntoViewIfNeeded(); await card.click(); await p.waitForTimeout(1500) }
}
await scene('radar-html-fiche-aqualifier-d', 1440, 900, fiche)
await scene('radar-html-fiche-aqualifier-m', 390, 844, fiche)

await b.close(); console.log('done')
