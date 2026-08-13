// M-ENTREE — vérification Playwright : chaque porte (Faisabilité, Assemblage) ouvre SON outil
// PRÉ-REMPLI avec la parcelle de la fiche ; ouverts depuis la page Outils (sans IDU), les outils
// fonctionnent comme avant (aucun pré-remplissage). Division n'a PAS de porte (contrôle négatif).
// Usage : BASE=http://127.0.0.1:8000/socle/ node qa/entree/verif.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const OUT = 'qa/entree/captures'
mkdirSync(OUT, { recursive: true })
const IDU = process.env.IDU || '97414000CV0907'   // canari
const SUF = IDU.slice(8)                            // ce que la puce Assemblage affiche

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })
page.setDefaultTimeout(20000)
const report = { idu: IDU }
const consoleErrs = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrs.push(m.text().slice(0, 140)) })
page.on('pageerror', (e) => consoleErrs.push('PAGEERROR ' + String(e).slice(0, 140)))
const bread = () => page.$eval('[data-module-breadcrumb]', (e) => e.textContent || '').catch(() => '(pas de panneau)')

async function ouvrirFicheEtTiroir() {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-omnibox]')
  await page.fill('[data-omnibox]', IDU)
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fiche-adresse]', { timeout: 25000 })
  // ouvrir le tiroir Constructibilité (accordéon) — les portes y vivent
  const head = page.locator('[data-drawer="faisabilite"] > button.tiroir')
  await head.waitFor({ timeout: 15000 })
  await head.click()
  await page.waitForTimeout(500)
}

async function fermerModule() {
  const x = await page.$('[aria-label="Fermer le module"]')
  if (x) { await x.click(); await page.waitForTimeout(400) }
}

// ── 1. PORTE FAISABILITÉ → outil pré-rempli mode « par parcelle » ──
await ouvrirFicheEtTiroir()
const pFaisa = page.locator('[data-porte="faisabilite-outil"]')
report.porte_faisabilite_presente = await pFaisa.count() > 0
await pFaisa.click()
await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 })
report.faisa_breadcrumb = (await bread()).trim()
report.faisa_mode_parcelle = await page.$('[data-faisa-parcelle]') != null   // picked amorcé
report.faisa_idu_affiche = await page.locator(`text=${IDU.slice(8, 10)} ${IDU.slice(10)}`).count() > 0
await page.screenshot({ path: `${OUT}/1-faisabilite-prerempli.png` })
await fermerModule()

// ── 2. PORTE ASSEMBLAGE → parcelle = 1ʳᵉ du lot ──
// le tiroir peut s'être refermé au retour ; on le rouvre au besoin
if (await page.locator('[data-porte="assemblage-outil"]').count() === 0) {
  await page.locator('[data-drawer="faisabilite"] > button.tiroir').click().catch(() => {})
  await page.waitForTimeout(400)
}
const pAsm = page.locator('[data-porte="assemblage-outil"]')
report.porte_assemblage_presente = await pAsm.count() > 0
await pAsm.click()
await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 })
report.asm_breadcrumb = (await bread()).trim()
report.asm_parcelle_dans_lot = await page.locator(`text=${SUF} ×`).count() > 0        // puce du lot
report.asm_compte_1 = await page.locator("text=Analyser l'assiette (1)").count() > 0
await page.screenshot({ path: `${OUT}/2-assemblage-prerempli.png` })

// ── 3. Contrôle négatif : PAS de porte Division ──
await fermerModule()
report.porte_division_absente = await page.locator('[data-porte="division-outil"], [data-porte="division"]').count() === 0

// ── 4. Ouverts depuis la page Outils (sans IDU) → aucun pré-remplissage ──
await page.goto(BASE, { waitUntil: 'domcontentloaded' })   // état frais (parcelPrefill jamais posé)
await page.waitForSelector('[data-omnibox]')
// ouvrir la page Outils puis chaque outil
const openOutil = async (key) => {
  const card = page.locator(`[data-outil="${key}"]`)
  if (await card.count() === 0) {
    // ouvrir le panneau Outils d'abord (bouton du rail)
    const railBtn = await page.$('button[title="Outils"]')
    if (railBtn) { await railBtn.click(); await page.waitForTimeout(400) }
  }
  await page.locator(`[data-outil="${key}"]`).first().click()
  await page.waitForSelector('[data-module-breadcrumb]', { timeout: 10000 })
}
await openOutil('programme')
report.outils_faisa_sans_prefill = await page.$('[data-faisa-parcelle]') == null   // mode critères par défaut
report.outils_faisa_breadcrumb = (await bread()).trim()
await page.screenshot({ path: `${OUT}/3-faisabilite-outils-vide.png` })
await fermerModule()
await openOutil('assemblage')
report.outils_asm_vide = await page.locator('text=aucune parcelle sélectionnée').count() > 0
await page.screenshot({ path: `${OUT}/4-assemblage-outils-vide.png` })

report.console_errors = consoleErrs
console.log(JSON.stringify(report, null, 1))
await browser.close()
