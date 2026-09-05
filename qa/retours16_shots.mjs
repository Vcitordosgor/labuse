// RETOURS-16 — recette navigateur + captures V1-V5. PHASE=avant|apres, ONLY=V1,V2…
// Lancer depuis frontend/ : CHROME=<exe> PHASE=apres node ../qa/retours16_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-16/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean)
const run = (s) => !ONLY.length || ONLY.includes(s)
const VP = Number(process.env.VP || 1440)

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: VP, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  shot', n, SUFFIX) }
let _n = 0
const go = async (hash = '') => { await page.goto(`${BASE}?r16=${++_n}${hash}`, { waitUntil: 'networkidle' }); await page.waitForTimeout(1500) }
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2500)
  await page.mouse.click(400, 860)
  await page.waitForTimeout(300)
}
const jump = async (lon, lat, z, wait = 5000) => {
  await page.evaluate(([ln, lt, zz]) => window.__labuse_map?.jumpTo({ center: [ln, lt], zoom: zz }), [lon, lat, z])
  await page.waitForTimeout(wait)
}
const report = {}

// ── V1 — la mer partout, sans marches : 4 cadrages × 2 fonds ──
if (run('V1')) {
  await go()
  await basemap('Ortho IGN')
  await page.waitForTimeout(4000)
  await shot('V1-ortho-ile')                        // 1. île entière : mer UNIFORME, zéro marche
  await jump(55.45, -20.83, 12.4, 7000)
  await shot('V1-ortho-nord-large')                 // 2. côte nord AU LARGE (cadrage du constat)
  await jump(55.222, -21.057, 13.2, 7000)
  await shot('V1-ortho-st-gilles')                  // 3. Saint-Gilles : bande côtière fondue
  await jump(55.45, -20.878, 16, 7000)
  await shot('V1-ortho-z16')                        // 4. z16 : photo pleine, aucune régression
  await go()
  await basemap('Plan IGN')
  await page.waitForTimeout(3500)
  await shot('V1-plan-ile')
  await jump(55.45, -20.83, 12.4, 6000)
  await shot('V1-plan-nord-large')
  await jump(55.222, -21.057, 13.2, 6000)
  await shot('V1-plan-st-gilles')
  await jump(55.45, -20.878, 16, 6000)
  await shot('V1-plan-z16')
}

// ── V2 — chip « Autorisé » retiré, puce localisation entière ──
if (run('V2')) {
  await go('#m=permis')
  await page.waitForTimeout(3500)
  report.V2_chip_autorise = await page.locator('[data-permis-liste] >> text=Autorisé').count()
  report.V2_puce_approx = await page.locator('text=approx').first().innerText().catch(() => 'absente')
  await shot('V2-permis-liste')
}

// ── V3 — « Dormant » partout (segment, filtres, légende) ──
if (run('V3')) {
  await go('#m=permis')
  await page.waitForTimeout(3000)
  report.V3_point_mort = await page.locator('text=point mort').count()
  report.V3_dormant = await page.locator('text=Dormant').count()
  await shot('V3-permis-segment')
  await page.click('[data-permis-filtres-toggle]').catch(() => {})
  await page.waitForTimeout(800)
  await shot('V3-permis-filtres')
}

// ── V4 — compteurs nommés ──
if (run('V4')) {
  await go('#m=permis')
  await page.waitForTimeout(3500)
  report.V4_haut = await page.locator('[data-permis-segment]').innerText().catch(() => '?')
  report.V4_bas = await page.locator('[data-permis-pied]').innerText().catch(
    () => page.locator('text=/en base/').first().innerText().catch(() => '?'))
  await shot('V4-permis-compteurs')
}

// ── V5 — autocomplétion : les six grammaires en action ──
if (run('V5')) {
  const suggest = async (nom, saisie, attente = 1200) => {
    await go()
    const barre = page.locator('[data-suggest-input]').first()
    await barre.click()
    await barre.fill(saisie)
    await page.waitForTimeout(attente)
    await shot(`V5-${nom}`)
    return page.locator('[data-suggest-item]').allInnerTexts().catch(() => [])
  }
  report.V5_adresse = await suggest('adresse', '50 rue helene boucher')
  report.V5_cadastre = await suggest('cadastre', 'BZ1065')
  report.V5_proprietaire = await suggest('proprietaire', 'SCI')
  report.V5_siren = await suggest('siren', '3801290')
  report.V5_commune = await suggest('commune', 'saint-pa')
  report.V5_projet = await suggest('projet', 'projet')
  report.V5_vide = await suggest('zero', 'zzzzzzz')
}

console.log('REPORT', JSON.stringify(report, null, 1))
console.log('erreurs page:', JSON.stringify(errors.slice(0, 10)))
await browser.close()
