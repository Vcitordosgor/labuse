// REPARATIONS-1 lot 1 — preuve navigateur : LED « Run servi » honnête (q_v11_m137, plus le run
// des tuiles) et page Circuit avec le candidat q_v14 déclaré assumé, V3a vert.
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot1.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '')
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(20000)
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')
await p.goto(`${BASE}/socle/#admin=1`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2500)
await p.locator('text=/Données/i').first().click(); await p.waitForTimeout(2500)
await p.locator('text=/^Circuit$/').first().click().catch(() => {}); await p.waitForTimeout(2000)
await p.screenshot({ path: `${OUT}/lot1-01-led-et-candidat.png` })
const t = await txt()
console.log('LED rail   :', t.match(/Run servi\s*\S+/)?.[0])
console.log('Verrous LED:', t.match(/Verrous\s*[\d/ ]+/)?.[0])
console.log('candidat   :', t.match(/candidat[^·]{0,40}/)?.[0])
writeFileSync(OUT + '/_lot1_texte.txt', t.slice(0, 2000))
await b.close()
