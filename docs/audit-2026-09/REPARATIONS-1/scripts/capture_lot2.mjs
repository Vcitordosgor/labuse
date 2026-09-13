// REPARATIONS-1 lot 2b — preuve navigateur : une parcelle stockée tier='brulante' (run servi)
// s'affiche « À suivre » (le palier Priorité n'est plus servi) ; l'Info scoring liste 3 paliers.
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot2.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '')
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
const IDU = process.env.IDU || '97411000AC0157'   // tier stocké = 'brulante' (run servi q_v11_m137)
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(25000)
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')

await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2500)
await p.evaluate((idu) => window.__labuse.select(idu), IDU); await p.waitForTimeout(3500)
// le verdict est « à la demande » : on le déplie si le bouton est là
try { await p.locator('text=/Demander à LABUSE d’analyser|Demander à LABUSE d\'analyser/i').first().click({ timeout: 4000 }); await p.waitForTimeout(2500) } catch {}
const t = await txt()
await p.screenshot({ path: `${OUT}/lot2-01-fiche-ex-brulante.png` })
console.log('IDU', IDU)
console.log('  contient « À suivre »   :', /À suivre/.test(t))
console.log('  contient « Priorité »   :', /Priorité/.test(t), (t.match(/[^.]{0,60}Priorité[^.]{0,60}/) || [''])[0])
writeFileSync(OUT + '/_lot2_fiche.txt', t.slice(0, 3000))
await b.close()
