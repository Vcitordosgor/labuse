// RECETTE-12 B2 — PREUVE segments : l'API renvoie jusqu'à 200 éléments PAR SEGMENT dès le 1er appel.
// Saint-Denis (filtre île) : permis_pro=63 → « 63 sur 63 » ; terrain_nu=6809 → 200 puis « voir 200 de plus ».
// Mesure les temps d'ouverture (cible < 2 s). Front :5199, API :8031.
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/captures-recette-12/', import.meta.url).pathname

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 140)) })
const wait = (ms) => page.waitForTimeout(ms)
const shot = async (n) => { await page.screenshot({ path: `${OUT}${n}.png` }); console.log('CAPTURE', n) }
const now = () => Date.now()
// texte du compteur « N sur total affichées » DANS le segment donné
const compteur = (seg) => page.evaluate((s) => {
  const btn = document.querySelector(`[data-segment="${s}"]`)
  const box = btn?.parentElement
  const c = box?.querySelector('[data-pagination-count]')
  return c ? c.textContent.replace(/\s+/g, ' ').trim() : null
}, seg)

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await wait(600)
// mode ANALYSE, vue île, filtré sur Saint-Denis (commune reste null → ile=true → chemin serveur segment)
await page.evaluate(() => {
  window.__labuse.setVerdict(true)
  window.__labuse.setFilters({ ...window.__labuse.getFilters(), analyseLabuse: true, communes: ['Saint-Denis'] })
})
// attendre que le panneau soit prêt (compte du segment chargé = requête de comptage faite, tables
// chaudes) — c'est l'état réel où l'utilisateur clique. On mesure alors l'ouverture À CHAUD.
await page.waitForFunction(() => {
  const b = document.querySelector('[data-segment="permis_pro"]')
  return b && /\d/.test(b.textContent || '')
}, { timeout: 20000 }).catch(() => {})
await wait(1500)

// ── segment permis_pro (63) : « 63 sur 63 » ──
console.log('--- permis_pro (63) ---')
let t0 = now()
await page.click('[data-segment="permis_pro"]')
await page.waitForFunction(() => {
  const b = document.querySelector('[data-segment="permis_pro"]')?.parentElement
  return b && b.querySelector('[data-pagination-count]')
}, { timeout: 8000 })
const tPP = now() - t0
console.log('compteur permis_pro =', await compteur('permis_pro'), '· ouverture', tPP, 'ms')
await wait(400)
await shot('B2-permis-pro-63')
// refermer
await page.click('[data-segment="permis_pro"]'); await wait(300)

// ── segment terrain_nu (6809) : 200 puis « voir 200 de plus » ──
console.log('--- terrain_nu (6809) ---')
t0 = now()
await page.click('[data-segment="terrain_nu"]')
await page.waitForFunction(() => {
  const b = document.querySelector('[data-segment="terrain_nu"]')?.parentElement
  return b && b.querySelector('[data-pagination-count]')
}, { timeout: 8000 })
const tTN = now() - t0
console.log('compteur terrain_nu (1er appel) =', await compteur('terrain_nu'), '· ouverture', tTN, 'ms')
await wait(400)
await shot('B2-terrain-nu-200')
// « voir 200 de plus »
const before = await compteur('terrain_nu')
t0 = now()
await page.click('[data-segment-more="terrain_nu"]')
await page.waitForFunction((prev) => {
  const b = document.querySelector('[data-segment="terrain_nu"]')?.parentElement
  const c = b?.querySelector('[data-pagination-count]')
  return c && c.textContent.replace(/\s+/g, ' ').trim() !== prev
}, before, { timeout: 8000 })
const tMore = now() - t0
console.log('compteur terrain_nu (voir 200 de plus) =', await compteur('terrain_nu'), '· temps', tMore, 'ms')
await wait(400)
await shot('B2-terrain-nu-400')

await browser.close()
console.log(`\nTEMPS — permis_pro ouverture ${tPP}ms · terrain_nu ouverture ${tTN}ms · voir 200 de plus ${tMore}ms`)
console.log('DONE')
