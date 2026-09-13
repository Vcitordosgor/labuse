// REPARATIONS-1 lots 4+5 — preuves navigateur : fiche « Le bien » (RNB ID + lien officiel,
// ligne « Sol artificialisé — d'après OCS GE ») et couche « Artificialisation (OCS GE) ».
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot45.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
const IDU = '97411000AC0157'
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(25000)
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')

await p.goto('http://localhost:5200/socle/', { waitUntil: 'networkidle' }); await p.waitForTimeout(2500)
await p.evaluate((idu) => window.__labuse.select(idu), IDU); await p.waitForTimeout(3000)
// ouvrir le tiroir « Le bien »
try { await p.locator('text=/Le bien/i').first().click(); await p.waitForTimeout(1500) } catch {}
await p.evaluate(() => { const el = [...document.querySelectorAll('*')].find(e => /Identifiant national du bâtiment/i.test(e.textContent||'') && (e.textContent||'').length < 400); el?.scrollIntoView({block:'center'}) })
await p.waitForTimeout(600)
const t = await txt()
console.log('RNB visible   :', /RNB/.test(t) && /G42PNDBB3ED7|rnb/.test(t))
console.log('OCS GE visible:', /d'après OCS GE|d’après OCS GE/.test(t))
await p.screenshot({ path: `${OUT}/lot45-01-fiche-rnb-ocsge.png` })

// couche artificialisation
await p.goto('http://localhost:5200/socle/', { waitUntil: 'networkidle' }); await p.waitForTimeout(2000)
try {
  await p.locator('text=/COUCHES/i').first().click(); await p.waitForTimeout(1200)
  await p.locator('text=/Artificialisation \(OCS GE\)/i').first().click(); await p.waitForTimeout(4000)
} catch (e) { console.log('couche KO', e.message) }
await p.screenshot({ path: `${OUT}/lot45-02-couche-artificialisation.png` })
console.log('couche cliquée')
await b.close()
