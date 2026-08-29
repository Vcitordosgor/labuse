// RADAR-HTML — captures des écrans touchés : dépôt HTML admin (Lot 1), fiche PISTE + Instruire (Lot 3),
// marché + écart demandé/acté (Lot 4). Usage : node qa/radar_html_shots.mjs (uvicorn :8000 + vite :5174).
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
const go = async (p, hash = '') => { await p.goto(BASE + hash, { waitUntil: 'networkidle', timeout: 60000 }); await p.waitForTimeout(2000) }

// ── ADMIN — Zone 0 « Dépôt HTML » (Lot 1) ──
async function adminRadar(p) {
  await go(p, '#admin=1'); await p.waitForTimeout(800)
  const tab = p.getByRole('button', { name: 'Radar' })
  if (await tab.count()) { await tab.first().click(); await p.waitForTimeout(1200) }
  await p.locator('[data-radar-depot-html]').first().waitFor({ timeout: 8000 }).catch(() => {})
}
await scene('radar-html-admin-d', 1440, 900, adminRadar)
await scene('radar-html-admin-m', 390, 844, adminRadar)

// ── CLIENT — listing + fiche PISTE + Instruire (Lot 3) ──
await scene('radar-html-cat-d', 1440, 900, async (p) => { await go(p, '#radar=1'); await p.waitForTimeout(1200) })
async function fichePiste(p) {
  await go(p, '#radar=1'); await p.waitForTimeout(1000)
  const card = p.locator('[data-radar-bien="5057"]')
  if (await card.count()) { await card.click(); await p.waitForTimeout(1500) }
  const btn = p.locator('[data-radar-instruire]')
  if (await btn.count()) { await btn.click(); await p.waitForTimeout(2000) }
}
await scene('radar-html-fiche-piste-d', 1440, 900, fichePiste)
await scene('radar-html-fiche-piste-m', 390, 844, fichePiste)

await b.close(); console.log('done')
