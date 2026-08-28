// RADAR-CATÉGORIE (T6) — captures 1440 (desktop) + 390 (mobile) de la catégorie Radar.
// Usage : node qa/radar_categorie_shots.mjs   (vite dev + seed [RADAR-TEST] requis).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = '/Users/openclaw/Desktop/labuse/docs/PIGE/captures'
mkdirSync(OUT, { recursive: true })
const BASE = process.env.BASE || 'http://[::1]:5174/socle/'
const b = await chromium.launch({ channel: 'chrome' })

async function scene(name, w, h, fn) {
  const p = await b.newPage({ viewport: { width: w, height: h } })
  try { await fn(p); await p.screenshot({ path: `${OUT}/${name}.png` }); console.log(`✓ ${name}`) }
  catch (e) { try { await p.screenshot({ path: `${OUT}/${name}.png` }) } catch {} console.log(`⚠ ${name}: ${String(e).split('\n')[0]}`) }
  finally { await p.close() }
}
const go = async (p, hash = '') => { await p.goto(BASE + hash, { waitUntil: 'networkidle', timeout: 60000 }); await p.waitForTimeout(2500) }

// ── DESKTOP 1440 ──
// Écran 1 — la catégorie (listing + carte)
await scene('radar-cat-ecran-d', 1440, 900, async (p) => { await go(p, '#radar=1'); await p.waitForTimeout(1500) })
// Écran 2 — la fiche d'un bien rattaché (avec baisse + 6 tuiles) : clic sur le bien 900001
await scene('radar-cat-fiche-d', 1440, 900, async (p) => {
  await go(p, '#radar=1'); await p.waitForTimeout(1200)
  await p.locator('[data-radar-bien="900001"]').click(); await p.waitForTimeout(2500)
})
// Fiche d'un bien NON rattaché (900003) : pas de section outils ni parcelle → ouvre le portail.
// On capture plutôt la fiche Estimé rattachée (900007) pour montrer une 2e fiche complète.
await scene('radar-cat-fiche-estime-d', 1440, 900, async (p) => {
  await go(p, '#radar=1'); await p.waitForTimeout(1200)
  await p.locator('[data-radar-bien="900007"]').click(); await p.waitForTimeout(2500)
})
// Filtre commune réel (bug T2) : sélectionne « Les Avirons »
await scene('radar-cat-filtre-commune-d', 1440, 900, async (p) => {
  await go(p, '#radar=1'); await p.waitForTimeout(1000)
  await p.locator('[data-radar-commune]').selectOption({ label: 'Les Avirons' }); await p.waitForTimeout(1800)
})

// ── MOBILE 390 ──
await scene('radar-cat-ecran-m', 390, 844, async (p) => { await go(p, '#radar=1'); await p.waitForTimeout(1500) })
await scene('radar-cat-fiche-m', 390, 844, async (p) => {
  await go(p, '#radar=1'); await p.waitForTimeout(1200)
  const c = p.locator('[data-radar-bien="900001"]'); if (await c.count()) { await c.click(); await p.waitForTimeout(2500) }
})

await b.close(); console.log('done')
