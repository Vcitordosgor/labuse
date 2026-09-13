// REPARATIONS-1 lot 3 — preuves navigateur : (1) page Sources client avec la couverture réelle
// DITE sous les sources partielles, et sans les 3 sources sous convention Cerema ; (2) admin
// Données : les 13 « non disponible — partenariat requis » visibles avec leur raison.
// Rejouable :  node docs/audit-2026-09/REPARATIONS-1/scripts/capture_lot3.mjs
import { chromium } from '/Users/openclaw/Desktop/labuse-etat/frontend/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'
const EXE = process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const BASE = (process.env.BASE || 'http://localhost:5200').replace(/\/$/, '')
const OUT = '/Users/openclaw/Desktop/labuse-etat/docs/audit-2026-09/REPARATIONS-1/captures'
const b = await chromium.launch({ executablePath: EXE })
const p = await b.newPage({ viewport: { width: 1600, height: 1000 } })
p.setDefaultTimeout(25000)
const txt = async () => (await p.evaluate(() => document.body.innerText)).replace(/\s+/g, ' ')

// ── 1. page Sources client ──
await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2000)
await p.locator('text=/^Sources$/').first().click().catch(async () => {
  await p.locator('nav >> text=/Sources/i').first().click()
}); await p.waitForTimeout(2500)
// chercher une source à note de couverture (DPU)
try {
  await p.locator('input[type=search], input[placeholder*=herch]').first().fill('préemption')
  await p.waitForTimeout(1200)
} catch {}
const t1 = await txt()
await p.screenshot({ path: `${OUT}/lot3-01-sources-couverture-dpu.png` })
console.log('couverture DPU visible :', /4 communes sur 24|publiés au Géoportail/.test(t1))
console.log('LOVAC visible client   :', /LOVAC/.test(t1))

// ── 2. admin Données — les partenariat requis ──
await p.goto(`${BASE}/socle/#admin=1`, { waitUntil: 'networkidle' }); await p.waitForTimeout(2200)
await p.locator('text=/Données/i').first().click(); await p.waitForTimeout(2500)
// la liste des non-servies vit sur le détail du compteur (Résumé/Circuit) — on cherche le texte
const t2 = await txt()
let found = /partenariat requis/i.test(t2)
if (!found) {
  // essayer le détail du compteur (page compteur = lignes non servies)
  try { await p.locator('text=/en base non servies|compteur|réservoirs/i').first().click(); await p.waitForTimeout(2000) } catch {}
  found = /partenariat requis/i.test(await txt())
}
await p.screenshot({ path: `${OUT}/lot3-02-admin-partenariat.png` })
console.log('« partenariat requis » visible admin :', found)
writeFileSync(OUT + '/_lot3_textes.txt', (t1.slice(0, 1500) + '\n---\n' + t2.slice(0, 1500)))
await b.close()
