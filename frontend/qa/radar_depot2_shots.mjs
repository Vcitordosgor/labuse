// RADAR-DEPOT-2 — captures de recette : fiche client sobre (D3, aucun bouton Instruire), bloc déclaré
// (D2), badge sous le marché (D4, liste + fiche + filtre), écran d'instruction ADMIN (D3).
// Usage : node qa/radar_depot2_shots.mjs (uvicorn :8000 dev + vite :5173).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = '/Users/openclaw/Desktop/labuse/docs/PIGE/captures'
mkdirSync(OUT, { recursive: true })
const BASE = process.env.BASE || 'http://127.0.0.1:5173/socle/'
const EXE = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const b = await chromium.launch({ executablePath: EXE })

async function scene(name, w, h, fn) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  try { await fn(p); await p.screenshot({ path: `${OUT}/${name}.png` }); console.log(`✓ ${name}`) }
  catch (e) { try { await p.screenshot({ path: `${OUT}/${name}.png` }) } catch {} console.log(`⚠ ${name}: ${String(e).split('\n')[0]}`) }
  finally { await p.close() }
}
const go = async (p, hash = '') => { await p.goto(BASE + hash, { waitUntil: 'networkidle', timeout: 60000 }); await p.waitForTimeout(1500) }
const filtrerCommune = async (p, commune) => {
  const sel = p.locator('[data-radar-commune]')
  if (await sel.count()) { await sel.selectOption({ label: commune }); await p.waitForTimeout(1200) }
}
const ouvrir = async (p, id) => {
  const card = p.locator(`[data-radar-bien="${id}"]`)
  if (await card.count()) { await card.scrollIntoViewIfNeeded(); await card.click(); await p.waitForTimeout(1500) }
}

// D4 — liste avec badges + filtre « sous le marché »
await scene('rdp2-liste-badges', 1440, 900, async (p) => {
  await go(p, '#m=radar'); await p.waitForTimeout(1000)
  const seg = p.locator('[data-seg="radar-seg-sm"] button', { hasText: 'Sous le marché' })
  if (await seg.count()) { await seg.click(); await p.waitForTimeout(4500) }   // le calcul sur tout l'ensemble
})
// capture CROPPÉE sur le panneau fiche (398px) — lisibilité des blocs D2/D3.
async function fiche(name, id, commune) {
  const p = await b.newPage({ viewport: { width: 1440, height: 1000 } })
  try {
    await go(p, '#m=radar'); await filtrerCommune(p, commune); await ouvrir(p, id)
    const panel = p.locator('[data-radar-fiche]').first()
    if (await panel.count()) await panel.screenshot({ path: `${OUT}/${name}.png` })
    else await p.screenshot({ path: `${OUT}/${name}.png` })
    console.log(`✓ ${name}`)
  } catch (e) { console.log(`⚠ ${name}: ${String(e).split('\n')[0]}`) } finally { await p.close() }
}
// D2 — fiche d'un bien avec faits DÉCLARÉS (zone UBc) — bien 7 (T-possession, La Possession)
await fiche('rdp2-fiche-declare', 7, 'La Possession')
// D3 — fiche d'un bien en PISTE : bloc SOBRE « position au quartier », AUCUN bouton Instruire — bien 50
await fiche('rdp2-fiche-piste-sobre', 50, 'La Possession')
// D3 — écran d'INSTRUCTION admin (zone 3bis) : onglet Radar de l'admin puis dérouler
await scene('rdp2-admin-instruction', 1440, 1300, async (p) => {
  await go(p, '#admin=1'); await p.waitForTimeout(800)
  const nav = p.locator('[data-admin-section="radar"]')
  if (await nav.count()) { await nav.click(); await p.waitForTimeout(1800) }
  const zone = p.locator('[data-radar-instruction]').first()
  if (await zone.count()) await zone.scrollIntoViewIfNeeded()
  await p.waitForTimeout(1000)
})

await b.close(); console.log('done')
