// M65 — captures APRÈS de la passe visuelle. Front dev :5173 (proxy /map,/accueil → :8000).
// Usage : node qa/m65_capture.mjs
import { chromium } from 'playwright'

const BASE = 'http://localhost:5173/'
const OUT = '../reports/m65/captures'
const wait = (p, ms) => p.waitForTimeout(ms)

const b = await chromium.launch({ channel: 'chrome' })
const page = await b.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE ERR:', m.text().slice(0, 160)) })

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse_map && window.__labuse_map.isStyleLoaded(), { timeout: 20000 }).catch(() => {})
await wait(page, 2500)

// 1 — ACCUEIL (panneau gauche : 3 cases, halo, 2 boutons, compteur)
const accueil = page.locator('[data-accueil]')
if (await accueil.count()) { await accueil.screenshot({ path: `${OUT}/accueil-apres.png` }); console.log('✓ accueil') }
else console.log('✗ accueil introuvable')

// 2 — RAIL (7 entrées, plus de « Recherche »)
const rail = page.locator('nav').first()
await rail.screenshot({ path: `${OUT}/rail-apres.png` }); console.log('✓ rail')

// 3 — CARTE SOMBRE (défaut)
await page.screenshot({ path: `${OUT}/carte-sombre-apres.png` }); console.log('✓ carte sombre')

// 4 — COUCHES (titres de catégories en étiquettes) — ouvrir le tiroir si fermé
const couches = page.locator('[data-couches-toggle]')
if (await couches.count()) {
  const drawer = page.locator('[data-couches-drawer]')
  if (!(await drawer.count())) { await couches.click(); await wait(page, 500) }
  const panel = page.locator('[data-accueil]').count().then(n => n) // placeholder
  const left = page.locator('aside, [data-couches-drawer]').first()
  await page.locator('[data-couches-drawer]').screenshot({ path: `${OUT}/couches-apres.png` }).catch(() => {})
  console.log('✓ couches')
}

// 5 — SÉLECTEUR DE COMMUNES (plus de code postal) — ouvrir le menu du header
const communeBtn = page.locator('button', { hasText: /Toute l.?.?le|communes?$/ }).first()
try {
  await communeBtn.click({ timeout: 3000 }); await wait(page, 400)
  await page.screenshot({ path: `${OUT}/communes-apres.png` })
  console.log('✓ communes (menu ouvert)')
  await page.keyboard.press('Escape')
} catch (e) { console.log('✗ communes:', String(e).slice(0, 80)) }

// 6 — CARTE CLAIR (bascule manuelle via le sélecteur « Fond de plan »)
try {
  await page.locator('button[title="Fond de plan"]').click({ timeout: 4000 }); await wait(page, 300)
  await page.getByRole('button', { name: 'Clair', exact: true }).click({ timeout: 4000 })
  await wait(page, 3500)
  await page.screenshot({ path: `${OUT}/carte-clair-apres.png` }); console.log('✓ carte clair')
  // zoom sur l'île pour bien voir l'inversion terre/mer + trait de côte
} catch (e) { console.log('✗ clair:', String(e).slice(0, 120)) }

// 7 — BOUTONS DE CARTE (crop haut-gauche, taille réduite 70 %)
await page.screenshot({ path: `${OUT}/zoom-boutons-apres.png`, clip: { x: 0, y: 60, width: 160, height: 200 } })
console.log('✓ boutons zoom')

await b.close()
console.log('FINI')
