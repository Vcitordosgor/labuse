// RETOURS-13 Lot 1 — captures APRÈS + recette des nouveautés (R2, R4, R5, R9).
// Lancer depuis frontend/ (copie locale) : CHROME=<exe> PHASE=apres node ./retours13_tmp2.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-13/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (name, sfx = SUFFIX) => { await page.screenshot({ path: `${OUT}/${name}-${sfx}.png` }); console.log('  shot', name, sfx) }
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2500)
  await page.mouse.click(400, 860)
  await page.waitForTimeout(300)
}
const toggleLayer = async (key) => { await page.click(`[data-layer="${key}"]`); await page.waitForTimeout(1800) }
const zoomIn = async (n, x = 720, y = 450) => {
  for (let i = 0; i < n; i++) { await page.mouse.dblclick(x, y); await page.waitForTimeout(900) }
}
const drawerScroll = async (frac) => {
  const drawer = page.locator('[data-couches-drawer]')
  if (!(await drawer.count())) { await page.click('[data-couches-toggle]'); await page.waitForTimeout(500) }
  await page.locator('[data-couches-drawer]').evaluate((el, f) => { el.scrollTop = el.scrollHeight * f }, frac)
  await page.waitForTimeout(300)
}

// ── R1 — mer sur Ortho IGN / Plan IGN / Clair, île entière (cadre par défaut) ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await basemap('Ortho IGN')
await page.waitForTimeout(3500)
await shot('R1-ortho-ile')
await basemap('Plan IGN')
await page.waitForTimeout(2000)
await shot('R1-plan-ile')
await basemap('Clair')
await page.waitForTimeout(1500)
await shot('R1-clair-ile')

// ── R2 — « Parcelles — classement LABUSE » seule VS « Limites parcelles » seule (même cadrage) ──
await basemap('Sombre')
await drawerScroll(0)
// état par défaut : parcelles ON, limites ON, communes ON → isoler chaque couche
await toggleLayer('limites')      // OFF → parcelles seule
await toggleLayer('communes')     // OFF
await zoomIn(3, 720, 430)         // zoom quartier pour voir le rendu parcellaire
await shot('R2-parcelles-seule', 'seule')
await toggleLayer('parcelles')    // OFF
await toggleLayer('limites')      // ON → limites seule
await shot('R2-limites-seule', 'seule')
await toggleLayer('parcelles')    // restaurer
await toggleLayer('communes')

// ── R3 — menu Couches : groupe « Réseaux » déplié ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await drawerScroll(0.55)
await shot('R3-couches-reseaux')

// ── R4 — moyenne tension : couche MT + HT (sombre, île puis zoom) ──
await toggleLayer('lignes_mt')
await toggleLayer('lignes_ht')
await page.click('[data-legend-toggle]').catch(() => {})
await page.waitForTimeout(2500)
await shot('R4-mt-ht-ile-sombre')
await zoomIn(3, 700, 300)
await shot('R4-mt-ht-zoom-sombre')
await toggleLayer('lignes_mt')
await toggleLayer('lignes_ht')

// ── R5 — couche TCSP (tronçons + stations), sombre puis zoom Saint-Denis ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await drawerScroll(0.55)
await toggleLayer('tcsp')
await page.click('[data-legend-toggle]').catch(() => {})
await page.waitForTimeout(2000)
await shot('R5-tcsp-ile-sombre')
await zoomIn(4, 700, 210)   // Saint-Denis (boulevard sud)
await shot('R5-tcsp-zoom-st-denis')
await toggleLayer('tcsp')

// ── R9 — arrêts : couche dédiée + clic → bulle nom + lignes + réseau ──
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)
await drawerScroll(0.55)
await toggleLayer('arrets')
await zoomIn(5, 700, 210)   // zoom quartier Saint-Denis
await page.waitForTimeout(1500)
// cliquer un arrêt : viser le canvas — les arrêts sont denses en centre-ville
const clicked = await page.evaluate(() => {
  return new Promise((resolve) => {
    // trouver un arrêt rendu et cliquer dessus par événement carte
    resolve(true)
  })
})
// clic en série sur une grille jusqu'à obtenir une popup
let popupOk = false
for (const [x, y] of [[720, 450], [680, 420], [760, 480], [700, 500], [740, 400], [660, 460], [780, 430]]) {
  await page.mouse.click(x, y)
  await page.waitForTimeout(700)
  if (await page.locator('.maplibregl-popup').count()) { popupOk = true; break }
  await page.keyboard.press('Escape').catch(() => {})
}
console.log('popup arrêt:', popupOk)
await shot('R9-arret-bulle')

console.log('erreurs page:', JSON.stringify(errors.slice(0, 8)))
await browser.close()
