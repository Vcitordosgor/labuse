// REPARATIONS-1 lot 0 — preuve navigateur : la page Circuit ne montre plus la fuite aléa,
// et la pompe accepte un calcul (aucune quarantaine) — SANS lancer de calcul.
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot0.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '')
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
mkdirSync(OUT, { recursive: true })
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(20000)
p.on('pageerror', e => console.log('  PAGEERR', String(e).slice(0, 140)))
const out = {}
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')
const shot = async n => { await p.waitForTimeout(600); await p.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log('  📸', n) }

// ── Tour de contrôle → Données (le Circuit) ──
await p.goto(`${BASE}/socle/#admin=1`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2500)
await shot('lot0-01-admin')
try {
  await p.locator('text=/Données|Circuit/i').first().click(); await p.waitForTimeout(2500)
} catch (e) { console.log('nav Données KO', e.message) }
out.circuit = await txt(); await shot('lot0-02-circuit')

// ── détail de la POMPE (clic sur le bloc pompe du diagramme, repli hash #cx=pompe) ──
try {
  await p.locator('text=/pompe/i').first().click({ timeout: 6000 })
} catch { await p.evaluate(() => { location.hash = location.hash + '&cx=pompe' }) }
await p.waitForTimeout(2500)
out.pompe = await txt(); await shot('lot0-03-pompe')

writeFileSync(OUT + '/_lot0_textes.json', JSON.stringify(out, null, 1))
const c = out.circuit || '', q = out.pompe || ''
console.log('VERIFS —')
console.log('  fuite mentionnée sur Circuit :', /fuite/i.test(c) ? c.match(/[^.]*fuite[^.]*/i)?.[0]?.slice(0, 160) : 'aucune mention')
console.log('  quarantaine mentionnée      :', /quarantaine/i.test(c + q) ? (c + q).match(/[^.]*quarantaine[^.]*/i)?.[0]?.slice(0, 160) : 'aucune mention')
console.log('  pompe (extrait)             :', q.slice(0, 400))
await b.close()
