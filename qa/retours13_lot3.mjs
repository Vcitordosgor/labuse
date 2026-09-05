// RETOURS-13 Lot 3 — recette navigateur (R19-R28, R32) + RE-TEST T1 réel (BZ1065 barre par barre, R24)
// + mesure du zoom R27. PHASE=avant|apres.
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-13/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'
const REF = 'BZ1065'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })
const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  shot', n, SUFFIX) }
const outil = async (key) => {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  await page.click('[data-rail="outils"]')
  await page.waitForTimeout(500)
  await page.click(`[data-outil="${key}"]`)
  await page.waitForTimeout(1400)
}
const inventaire = {}

// ── R19/R20 — Trouver les parcelles (Faisabilité › critères) ──
await outil('programme')
await page.waitForTimeout(800)
await shot('R20-programme-formulaire')
// lancer une recherche pour voir le bloc de résultat (R19)
const lancer = page.locator('button:has-text("Trouver les parcelles")')
if (await lancer.count()) {
  await lancer.click()
  await page.waitForTimeout(6000)
  await shot('R19-programme-resultat')
}

// ── R21/R22/R23 — Annuaire PLU ──
await outil('plu')
await page.click('[data-plu-voie="annuaire"]').catch(() => page.click('button:has-text("Annuaire")'))
await page.waitForTimeout(2500)
await shot('R21-annuaire-plu')

// ── R24 — Vérification PLU : BZ1065 dans la barre ──
await outil('plu')
await page.click('[data-plu-voie="procchg"]').catch(() => {})
await page.waitForTimeout(1500)
const verifInput = page.locator('[data-verif-idu]')
if (await verifInput.count()) {
  await verifInput.fill(REF)
  await verifInput.press('Enter')
  await page.waitForTimeout(2500)
  const cands = await page.locator('[data-parcelinput-candidat]').count()
  const result = await page.locator('[data-verif-result]').count()
  inventaire['VerifProcedure'] = cands > 0 ? `désambiguïsation (${cands} candidates)` : (result ? 'résolu direct' : 'ÉCHEC')
  await shot('R24-verif-procedure-BZ1065')
  if (cands > 0) {
    await page.locator('[data-parcelinput-candidat]').first().click()
    await page.waitForTimeout(2500)
    inventaire['VerifProcedure_apres_choix'] = (await page.locator('[data-verif-result]').count()) ? 'résultat rendu' : 'PAS DE RÉSULTAT'
  }
} else { inventaire['VerifProcedure'] = 'CHAMP INTROUVABLE' }

// ── R24 — re-test T1 : BZ1065 dans les barres ParcelInput des outils + omnibox ──
const BARRES = [
  ['scoreur-adresse', 'Étudier un bien', '[data-etudier-adresse]'],
  ['risques', 'Pièges & risques', '[data-blocb-adresse]'],
  ['prospection-solaire', 'Prospection solaire', null],
  ['temps', 'Remonter le temps', null],
  ['courriers', 'Courrier propriétaire', null],
  ['instruire', 'Diligence', null],
  ['etude-zone', 'Étude de zone', null],
  ['renouvellement', 'Densifier l’existant', null],
  ['mon-secteur', 'Mon secteur', null],
]
for (const [key, nom, sel] of BARRES) {
  try {
    await outil(key)
    let champ = sel ? page.locator(sel) : page.locator('input[placeholder*="dresse"], input[placeholder*="IDU"]').first()
    if (!(await champ.count())) champ = page.locator('input').first()
    if (!(await champ.count())) { inventaire[nom] = 'CHAMP INTROUVABLE'; continue }
    await champ.fill(REF)
    await champ.press('Enter')
    await page.waitForTimeout(2200)
    const cands = await page.locator('[data-parcelinput-candidat]').count()
    inventaire[nom] = cands > 0 ? `désambiguïsation (${cands})` : 'résolution directe ou aucune liste (à vérifier)'
  } catch (e) { inventaire[nom] = 'ERREUR ' + String(e).slice(0, 60) }
}
// omnibox
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1200)
const omni = page.locator('header input').first()
if (await omni.count()) {
  await omni.fill(REF)
  await omni.press('Enter')
  await page.waitForTimeout(2500)
  const toast = await page.locator('text=/commune/i').count()
  inventaire['Omnibox (header)'] = toast > 0 ? 'multi-communes signalé' : 'réponse rendue (vérifier zoom/toast)'
  await shot('R24-omnibox-BZ1065')
}

// ── R25 — simulateur AU : accordéon Attention replié ──
await outil('plu')
await page.click('[data-plu-voie="procchg"]').catch(() => {})
await page.waitForTimeout(1500)
await shot('R25-simulateur-au')

// ── R26 — taxe d'aménagement depuis une parcelle ──
await outil('scoreur-adresse')
const etudier = page.locator('[data-etudier-adresse]')
if (await etudier.count()) {
  await etudier.fill('97411000BE0158')
  await etudier.press('Enter')
  await page.waitForTimeout(3500)
}
await page.click('[data-rail="outils"]'); await page.waitForTimeout(400)
await page.click('[data-outil="taxe-amenagement"]')
await page.waitForTimeout(1000)
const btn = page.locator('[data-taxe-prefill]')
if (await btn.count()) { await btn.click(); await page.waitForTimeout(2500) }
await shot('R26-taxe-preremplie')
const surfVal = await page.locator('[data-taxe-field="surface"]').inputValue().catch(() => '')
console.log('R26 surface préremplie:', surfVal)

// ── R27 — zoom franc (Étudier un bien) : mesurer le zoom final ──
await outil('scoreur-adresse')
const e2 = page.locator('[data-etudier-adresse]')
if (await e2.count()) {
  await e2.fill('97411000BE0158')
  await e2.press('Enter')
  await page.waitForTimeout(4000)
  const z = await page.evaluate(() => window.__labuse_map?.getZoom())
  console.log('R27 zoom final:', z)
  await shot('R27-etudier-zoom')
}

// ── R28 — Étude de zone : bouton Lire la zone ──
await outil('etude-zone')
await shot('R28-etude-zone-bouton')

console.log('INVENTAIRE R24:', JSON.stringify(inventaire, null, 1))
console.log('erreurs page:', JSON.stringify(errors.slice(0, 8)))
await browser.close()
