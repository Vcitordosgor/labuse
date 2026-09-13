// REPARATIONS-1 lot 0 — preuve navigateur AU BOUTON : « Vérifier que tout coule » (un contrôle,
// jamais un calcul) rejoué depuis la page Circuit → bandeau à 0 fuite, pompe qui accepte.
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot0b.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '')
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
mkdirSync(OUT, { recursive: true })
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(20000)
const shot = async n => { await p.waitForTimeout(400); await p.screenshot({ path: `${OUT}/${n}.png` }); console.log('  📸', n) }
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')

await p.goto(`${BASE}/socle/#admin=1`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2000)
await p.locator('text=/Données/i').first().click(); await p.waitForTimeout(2500)
await p.locator('button:has-text("Vérifier que tout coule")').first().click()
console.log('  contrôle lancé — attente de la fin (~60 s)…')
// le bandeau « Contrôle terminé » se met à jour à la fin de la tâche détachée
await p.waitForFunction(() => /Contrôle terminé\s*:/.test(document.body.innerText) &&
  !/en cours|—\s*\d+\s*\/\s*\d+/.test(document.body.innerText), null, { timeout: 180000, polling: 2000 })
  .catch(() => console.log('  (timeout d’attente fine — on capture l’état courant)'))
await p.waitForTimeout(2000)
const t = await txt()
const bandeau = t.match(/Contrôle terminé[^.]*\./)?.[0]
console.log('  BANDEAU :', bandeau)
await shot('lot0-04-verifier-bandeau')
writeFileSync(OUT + '/_lot0b_bandeau.txt', bandeau || t.slice(0, 800))
await b.close()
