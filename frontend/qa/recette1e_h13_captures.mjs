// RECETTE-1e H13.3 — vérification LIVE + captures du chemin Piscines refait :
//   assistant 2 étapes (Périmètre → Statut) + carte en PARCELLES COLORÉES (plus des points).
// Front dev :5895 (/socle/), API :8695. Chromium headful (channel chrome) = vrai GPU, carte rendue.
//   node frontend/qa/recette1e_h13_captures.mjs
import pkg from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.js'
const { chromium } = pkg

const BASE = 'http://127.0.0.1:5895/socle/'
const OUT = new URL('../../docs/audit-2026-09/RECETTE-1/captures-recette-1e/', import.meta.url).pathname
import { mkdirSync } from 'node:fs'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ headless: false, channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error' && !/40[0-4]/.test(m.text())) console.error('PAGE-ERR', m.text().slice(0, 160)) })
// page.screenshot peut se bloquer sur « waiting for fonts » (webfont jamais résolue) : timeout court + repli.
const shot = async (name) => {
  try { await page.screenshot({ path: `${OUT}${name}.png`, timeout: 8000, animations: 'disabled' }); console.log('CAPTURE', name) }
  catch { console.log('CAPTURE(retry)', name); await page.screenshot({ path: `${OUT}${name}.png`, timeout: 8000, animations: 'disabled' }).catch((e) => console.log('SHOT FAIL', name, String(e).slice(0, 60))) }
}
const wait = (ms) => page.waitForTimeout(ms)

await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForFunction(() => window.__labuse != null && window.__labuse_map != null, { timeout: 30000 })
await wait(1500)

// ── AVANT (H13.3) — l'ancien rendu : des POINTS/GOUTTES (centroïdes), invisibles au zoom île et sans
// distinction de statut. On recrée l'ancien comportement en alimentant module-extra avec /points.
await page.evaluate(async () => {
  const r = await fetch('http://127.0.0.1:8695/modules/prospection-piscines/points?commune=Saint-Paul&inclure_incertaines=1')
  const fc = await r.json()
  window.__labuse.setModuleMap({ idus: [], extra: fc, fit: true })
})
await wait(2600)
await shot('H13-3-AVANT-points-gouttes')
await page.evaluate(() => window.__labuse.setModuleMap({ idus: [], extra: null }))
await wait(400)

// Ouvrir l'outil Prospection solaire → mode Piscines
await page.evaluate(() => window.__labuse.setModule('prospection-solaire'))
await page.waitForSelector('[data-solaire-mode="piscines"]', { timeout: 15000 })
await wait(400)
await page.click('[data-solaire-mode="piscines"]')

// ── ÉTAPE 1 — PÉRIMÈTRE (toute l'île + les 24 communes, compte à côté) ──
await page.waitForSelector('[data-piscines-perim="ile"]', { timeout: 15000 })
await wait(600)
await shot('H13-3-etape1-perimetre')

// Choisir une commune (Saint-Paul : lecture nette des parcelles colorées)
await page.click('[data-piscines-perim="Saint-Paul"]')

// ── ÉTAPE 2 — STATUT (confirmées / à confirmer / les deux) ──
await page.waitForSelector('[data-piscines-statut="tous"]', { timeout: 10000 })
await wait(500)
await shot('H13-3-etape2-statut')

// « Les deux » → la carte doit colorer confirmées (menthe) ET à confirmer (ambre)
await page.click('[data-piscines-statut="tous"]')

// ── RÉSULTAT — compte + liste paginée + CARTE EN PARCELLES COLORÉES ──
await page.waitForSelector('[data-piscines-row]', { timeout: 15000 })
// laisser la couche /parcelles charger et la carte se rendre
await page.waitForFunction(() => {
  const m = window.__labuse_map
  const s = m && m.getSource('module-extra')
  const d = s && s._data
  return d && d.features && d.features.some((f) => f.properties && f.properties.kind === 'piscine-parcelle')
}, { timeout: 20000 }).catch(() => console.log('WARN: module-extra pas peuplé dans le délai'))
await page.evaluate(() => window.__labuse_map.once('idle', () => {}))
await wait(2500)

// DIAGNOSTIC : combien de parcelles-piscine rendues, et de quels statuts
const diag = await page.evaluate(() => {
  const m = window.__labuse_map
  const s = m.getSource('module-extra')
  const feats = (s && s._data && s._data.features) || []
  const parc = feats.filter((f) => f.properties && f.properties.kind === 'piscine-parcelle')
  const rendered = m.queryRenderedFeatures({ layers: ['module-piscine-fill'] })
  const byStatut = {}
  for (const f of parc) { const k = f.properties.statut; byStatut[k] = (byStatut[k] || 0) + 1 }
  return { totalParcelles: parc.length, byStatut, renderedOnScreen: rendered.length,
           hasFillLayer: !!m.getLayer('module-piscine-fill'), hasLineLayer: !!m.getLayer('module-piscine-line'),
           total: document.querySelector('[data-piscines-total]')?.textContent }
})
console.log('DIAG H13.3', JSON.stringify(diag))
await shot('H13-3-resultat-parcelles-colorees')

// Zoom sur un cluster de parcelles pour voir le remplissage coloré de près
await page.evaluate(() => window.__labuse_map.flyTo({ center: [55.29, -21.03], zoom: 15.5, duration: 1500 }))
await wait(2200)
await shot('H13-3-resultat-zoom-parcelles')

// Clic sur une parcelle colorée → la fiche s'ouvre (parcelle sous-jacente)
await page.click('[data-piscines-row]')
await wait(1800)
await shot('H13-3-clic-ligne-fiche')

await browser.close()
console.log('DONE', JSON.stringify(diag))
