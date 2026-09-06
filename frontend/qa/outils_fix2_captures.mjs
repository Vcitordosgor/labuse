// OUTILS-FIX-2 — captures des écrans touchés. LABEL=avant|apres.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const LABEL = process.env.LABEL || 'apres'
const OUT = `/Users/openclaw/Desktop/labuse-fix2/docs/audit-2026-09/OUTILS-FIX-2/${LABEL}`
mkdirSync(OUT, { recursive: true })
const BASE = 'http://localhost:5173/socle/'
const IDU = '97411000BZ1065'
const IDU2 = '97411000AB0006'
const PERMIS_SIREN = '9744152600448'   // permis avec petitioner_siren (A4)
const PANEL = { x: 0, y: 0, width: 540, height: 900 }

const b = await chromium.launch({ channel: 'chrome' })
const shot = async (name, page, clip) => { await page.screenshot({ path: `${OUT}/${name}_${LABEL}.png`, clip }); console.log('shot', name) }
async function open(mod) {
  const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
  await p.goto(`${BASE}#m=${mod}`, { waitUntil: 'networkidle', timeout: 60000 })
  await p.waitForTimeout(1500)
  return p
}
const tryClick = async (p, sel) => { try { await p.click(sel, { timeout: 8000 }) } catch {} }

try {
  // A3 — Étudier un bien : deux ponts (Faisabilité détaillée / Assembler)
  try {
    const p = await open('scoreur-adresse')
    await p.fill('[data-etudier-adresse]', IDU).catch(() => {})
    await p.keyboard.press('Enter')
    await p.waitForSelector('[data-etudier-fiche]', { timeout: 40000 }).catch(() => {})
    await p.waitForTimeout(1500)
    await p.locator('[data-etudier-fiche]').scrollIntoViewIfNeeded().catch(() => {})
    await p.waitForTimeout(600)
    await shot('01_etudier_ponts', p, PANEL)
    await p.close()
  } catch (e) { console.log('A3 fail', e.message) }

  // A2/A5 — Densifier tableau complet : Faisabilité par ligne + sélection Comparer
  try {
    const p = await open('renouvellement')
    await tryClick(p, 'text=/Ouvrir le tableau complet/')
    await p.waitForSelector('[data-densifier-row]', { timeout: 40000 }).catch(() => {})
    await p.waitForTimeout(1200)
    const cbs = await p.$$('[data-densifier-sel]')
    for (const c of cbs.slice(0, 2)) await c.click().catch(() => {})
    await p.waitForTimeout(400)
    await shot('02_densifier_ponts', p)
    await p.close()
  } catch (e) { console.log('A2 fail', e.message) }

  // A5 — Faisabilité par critères : sélection → Comparer
  try {
    const p = await open('programme')
    await tryClick(p, 'text=Trouver les parcelles')
    await p.waitForSelector('[data-prog-sel]', { timeout: 40000 }).catch(() => {})
    const cbs = await p.$$('[data-prog-sel]')
    for (const c of cbs.slice(0, 2)) await c.click().catch(() => {})
    await p.waitForTimeout(400)
    await shot('03_faisabilite_comparer', p, PANEL)
    await p.close()
  } catch (e) { console.log('A5-prog fail', e.message) }

  // A5 — Solaire piscines : bouton Comparer dans la barre d'actions
  try {
    const p = await open('prospection-solaire')
    await tryClick(p, '[data-solaire-mode="piscines"]')
    await p.waitForSelector('[data-piscines-sel]', { timeout: 30000 }).catch(() => {})
    const cbs = await p.$$('[data-piscines-sel]')
    for (const c of cbs.slice(0, 2)) await c.click().catch(() => {})
    await p.waitForTimeout(400)
    await shot('04_solaire_comparer', p, PANEL)
    await p.close()
  } catch (e) { console.log('A5-solaire fail', e.message) }

  // A1/A5 — Scan patrimoine : liste avec sélection → Courrier + Comparer
  try {
    const p = await open('patrimoine')
    await p.fill('[data-scan-search] input, input[data-scan-search]', 'CBO TERRITORIA').catch(async () => {
      await p.fill('input[placeholder*="SIREN"]', 'CBO TERRITORIA').catch(() => {})
    })
    await tryClick(p, '[data-scan-chercher]')
    await p.waitForTimeout(2500)
    await tryClick(p, '[data-scan-voir-parcelles]')
    await p.waitForSelector('[data-scan-parc-sel]', { timeout: 30000 }).catch(() => {})
    const cbs = await p.$$('[data-scan-parc-sel]')
    for (const c of cbs.slice(0, 2)) await c.click().catch(() => {})
    await p.waitForTimeout(500)
    await shot('05_scan_patrimoine_ponts', p, PANEL)
    await p.close()
  } catch (e) { console.log('A1 fail', e.message) }

  // A4 — Permis : drawer d'un permis AVEC SIREN → Scan patrimoine du porteur (ouvert par permitToOpen)
  try {
    const p = await open('permis')
    await p.waitForTimeout(1000)
    await p.evaluate((id) => window.__labuse.setPermitToOpen(id), PERMIS_SIREN)
    await p.waitForSelector('[data-permis-drawer]', { timeout: 20000 }).catch(() => {})
    await p.waitForTimeout(1200)
    console.log('A4 scan button:', !!(await p.$('[data-permis-scan-patrimoine]')))
    await shot('06_permis_scan', p)
    await p.close()
  } catch (e) { console.log('A4 fail', e.message) }

  // B — Taxe : surface VIDE + repère « reprendre », omnibox permanente, plus de « retirer »
  try {
    const p = await open('taxe-amenagement')
    await p.fill('[data-taxe-parcelle]', IDU).catch(() => {})
    await p.keyboard.press('Enter')
    await p.waitForSelector('[data-taxe-field="surface"]', { timeout: 40000 }).catch(() => {})
    await p.waitForTimeout(1200)
    await shot('07_taxe_surface_vide', p, PANEL)
    await p.close()
  } catch (e) { console.log('B fail', e.message) }

  // C — PLU procédure & changement : deux onglets
  try {
    const p = await open('plu')
    await tryClick(p, '[data-plu-voie="procchg"]')
    await p.waitForSelector('[data-procchg-tab]', { timeout: 30000 }).catch(() => {})
    await p.waitForTimeout(800)
    await shot('08_plu_onglets_parcelle', p, PANEL)
    await tryClick(p, '[data-procchg-tab="simuler"]')
    await p.waitForTimeout(800)
    await shot('09_plu_onglets_simuler', p, PANEL)
    await p.close()
  } catch (e) { console.log('C fail', e.message) }

  // D — Comparer : omnibox + tableau (badges Sourcé/Estimé, fourchette, CSV)
  try {
    const p = await open('comparer')
    await shot('10_comparer_omnibox', p, PANEL)
    // ajout fiable via « + Ajouter la parcelle courante » (select pose selectedIdu, le panneau l'offre)
    for (const id of [IDU, IDU2]) {
      await p.evaluate((i) => window.__labuse.select(i), id)
      await p.waitForTimeout(1000)
      await tryClick(p, '[data-compare-ajouter-courante]')
      await p.waitForTimeout(600)
    }
    await tryClick(p, '[data-compare-ouvrir]')
    await p.waitForSelector('[data-compare-col]', { timeout: 30000 }).catch(() => {})
    await p.waitForTimeout(1500)
    await shot('11_comparer_tableau', p)
    await p.close()
  } catch (e) { console.log('D fail', e.message) }
} finally {
  await b.close()
}
