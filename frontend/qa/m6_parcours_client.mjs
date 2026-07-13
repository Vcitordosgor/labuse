// M6 §1.14 — PARCOURS PREMIER CLIENT (audit lecture seule).
// Simule un client qui découvre l'app : première connexion → première opportunité
// pertinente. Chronomètre chaque étape (timings machine ; le temps humain de lecture
// est estimé dans le rapport). N'écrit rien : navigation + clics de consultation.
//
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/m6_parcours_client.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../reports/m6-audit/sections/captures-1-14'
mkdirSync(OUT, { recursive: true })

const T0 = Date.now()
const marks = []
const mark = (label) => { const t = Date.now() - T0; marks.push([label, t]); console.log(`  [${(t / 1000).toFixed(1).padStart(6)} s] ${label}`) }
const frictions = []
const friction = (sev, txt) => { frictions.push([sev, txt]); console.log(`  ⚠ [${sev}] ${txt}`) }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + e.message))
const failedReqs = []
page.on('requestfailed', (r) => failedReqs.push(`${r.method()} ${r.url()} — ${r.failure()?.errorText}`))

// ── Étape 1 : arrivée ──────────────────────────────────────────────────────
console.log('\n── Étape 1 — arrivée sur l\'app ──')
await page.goto(BASE, { waitUntil: 'domcontentloaded' })
mark('DOM chargé (page blanche → structure)')
await page.waitForSelector('canvas', { timeout: 20000 })
mark('carte MapLibre présente (canvas)')
await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
mark('réseau au repos (tuiles + geojson chargés)')
await page.screenshot({ path: `${OUT}/01-arrivee.png` })

// que voit le client ? (chips de tête, jargon)
const headerTxt = (await page.textContent('header').catch(() => '')) || ''
const bodyTxt0 = (await page.textContent('body')) || ''
console.log('  · bandeau haut :', headerTxt.replace(/\s+/g, ' ').slice(0, 160))
if (!bodyTxt0.includes('Afficher l’analyse LABUSE') && !bodyTxt0.includes("Afficher l'analyse LABUSE"))
  friction('P2', 'CTA « Afficher l\'analyse LABUSE » introuvable à l\'arrivée')

// ── Étape 2 : le client clique le seul CTA visible ─────────────────────────
console.log('\n── Étape 2 — « Afficher l\'analyse LABUSE » ──')
const t2 = Date.now()
await page.click('text=Afficher l\'analyse LABUSE')
await page.waitForSelector('text=Brûlantes v2', { timeout: 20000 })
mark(`chips de verdict affichées (+${((Date.now() - t2) / 1000).toFixed(1)} s après le clic)`)
await page.waitForSelector('[data-results-scroll] button', { timeout: 20000 })
mark('liste de résultats peuplée (1res cartes)')
await page.screenshot({ path: `${OUT}/02-analyse.png` })

// jargon à l'écran au moment où le client doit comprendre
const bodyTxt = (await page.textContent('body')) || ''
for (const [terme, ou] of [['Brûlantes v2', 'chips'], ['rang P', 'tri'], ['×N', 'tri'],
  ['Mutabilité', 'barre de filtres'], ['Réserve foncière', 'chips'], ['SDP', 'filtres']]) {
  if (bodyTxt.includes(terme)) console.log(`  · jargon visible : « ${terme} » (${ou})`)
}

// « pourquoi ? » : l'explication existe-t-elle et s'ouvre-t-elle ?
const pourquoi = page.locator('text=pourquoi ?').first()
if (await pourquoi.count()) {
  await pourquoi.click()
  await page.waitForTimeout(600)
  const t = (await page.textContent('body')) || ''
  if (t.length > bodyTxt.length + 100) mark('« pourquoi ? ▾ » ouvert — explication des verdicts disponible')
  else friction('P2', '« pourquoi ? ▾ » : clic sans effet visible')
  await page.screenshot({ path: `${OUT}/03-pourquoi.png` })
  // fermer le popover : le fond (backdrop plein écran) capte le clic — cliquer le fond
  const backdrop = page.locator('div.fixed.inset-0').first()
  if (await backdrop.count()) await backdrop.click({ force: true, timeout: 2000 }).catch(() => {})
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
} else friction('P2', 'aucun « pourquoi ? » près des compteurs')

// ── Étape 3 : premier filtre (le client clique la chip Brûlantes v2) ───────
console.log('\n── Étape 3 — premier filtre : chip « Brûlantes v2 » ──')
const t3 = Date.now()
await page.locator('button', { hasText: 'Brûlantes v2' }).first().click()
await page.waitForTimeout(2500) // refetch
mark(`filtre brûlantes appliqué (+${((Date.now() - t3) / 1000).toFixed(1)} s)`)
const firstCard = await page.locator('[data-results-scroll] button').first().textContent()
console.log('  · 1re carte :', (firstCard || '').replace(/\s+/g, ' ').slice(0, 90))
await page.screenshot({ path: `${OUT}/04-filtre-brulantes.png` })

// ── Étape 4 : première fiche ────────────────────────────────────────────────
console.log('\n── Étape 4 — première fiche ouverte ──')
const t4 = Date.now()
await page.locator('[data-results-scroll] button').first().click()
await page.waitForSelector('[data-badge-verdict]', { timeout: 20000 })
mark(`fiche ouverte, verdict affiché (+${((Date.now() - t4) / 1000).toFixed(1)} s)`)
await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
mark('fiche complète (réseau au repos)')
await page.screenshot({ path: `${OUT}/05-fiche.png` })

// la fiche répond-elle aux questions d'un client ? (adresse, prix, contact, zone)
const fiche = (await page.locator('[data-badge-verdict]').locator('xpath=ancestor::*[self::aside or self::section or self::div][3]').textContent().catch(() => '')) || (await page.textContent('body'))
const checks = [
  ['adresse', /adresse|Adresse|rue |Rue |chemin |Chemin |impasse |Impasse |allée /],
  ['zone PLU', /[Zz]one|PLU/],
  ['surface', /m²/],
  ['prix / marché', /€\/?m?²?|marché|médiane?/i],
  ['propriétaire', /[Pp]ropriétaire/],
  ['contact (tél / courrier)', /téléphone|contact|courrier|Courrier/i],
]
for (const [what, re] of checks) {
  const found = re.test(fiche)
  console.log(`  · ${found ? '✓' : '✗'} ${what} ${found ? 'présent(e)' : 'INTROUVABLE sur la fiche'}`)
  if (!found) friction(what === 'contact (tél / courrier)' || what === 'prix / marché' ? 'P1' : 'P2',
    `fiche : ${what} introuvable au premier regard`)
}

// ── Étape 5 : jugement de pertinence (critère métier simple) ────────────────
// Le client cherche une opportunité BRÛLANTE avec un « pourquoi » lisible :
// tier v2 brûlante + surface + commune + verdict cohérent (pas d'exclusion dure).
console.log('\n── Étape 5 — première opportunité jugée pertinente ──')
const verdict = (await page.locator('[data-badge-verdict]').first().textContent().catch(() => '')) || ''
const ecartee = await page.locator('[data-bandeau-ecartee]').count()
console.log(`  · verdict fiche : « ${verdict.trim()} » · bandeau écartée : ${ecartee ? 'OUI' : 'non'}`)
if (/Brûlante|Chaude/i.test(verdict) && !ecartee) {
  mark('OPPORTUNITÉ PERTINENTE identifiée (brûlante v2, non écartée, surface + commune lisibles)')
} else {
  friction('P1', `la 1re fiche ouverte n'est pas une opportunité nette (verdict="${verdict.trim()}", écartée=${!!ecartee})`)
  mark('échec : première fiche non pertinente')
}

// ── Étape 6 : détour classique — recherche d'une référence précise ──────────
console.log('\n── Étape 6 — recherche omnibox (référence connue) ──')
const t6 = Date.now()
await page.fill('[data-omnibox]', 'AS 1425')
await page.keyboard.press('Enter')
await page.waitForTimeout(2500)
mark(`recherche « AS 1425 » (+${((Date.now() - t6) / 1000).toFixed(1)} s)`)
await page.screenshot({ path: `${OUT}/06-recherche.png` })

// ── Bilan ────────────────────────────────────────────────────────────────────
console.log('\n════ CHRONOLOGIE ════')
for (const [l, t] of marks) console.log(`${(t / 1000).toFixed(1).padStart(7)} s  ${l}`)
console.log('\n════ FRICTIONS (machine) ════')
for (const [s, f] of frictions) console.log(`[${s}] ${f}`)
console.log(`\nerreurs console : ${consoleErrors.length}`)
consoleErrors.slice(0, 5).forEach((e) => console.log('  ·', e.slice(0, 160)))
console.log(`requêtes échouées : ${failedReqs.length}`)
failedReqs.slice(0, 5).forEach((e) => console.log('  ·', e.slice(0, 160)))

await browser.close()
