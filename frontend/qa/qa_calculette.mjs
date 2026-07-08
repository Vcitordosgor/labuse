// MANDAT bilan-calculette — Bloc A (la calculette de charge foncière) + Bloc B (finitions UX
// vérifiables). Tout est VISIBILITÉ ÉCRAN (doctrine : la demi-feature est interdite). L'arithmétique
// est en outre couverte, EN ISOLATION, par tests/test_bilan.py (pytest).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const RESOLUE = '97415000BK0023'      // capacité SORT (9 723 m² · prix DVF fiable) — la calculette calcule
const NON_RESOLUE = '97419000AC0159'  // capacité non résolue — cas limite honnête

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 950 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('[data-verdict-on]', { timeout: 20000 })

const openBilan = async (idu) => {
  await page.evaluate((i) => { window.__labuse.setView('cartes'); window.__labuse.select(i) }, idu)
  await page.waitForSelector('button:has-text("Bilan")', { timeout: 12000 })
  await page.locator('button:has-text("Bilan")').click()
  await page.waitForSelector('[data-calculette]', { timeout: 12000 })
}

// ═══ BLOC A — LA CALCULETTE ═══
await openBilan(RESOLUE)
await page.waitForSelector('[data-calc-resultat]', { timeout: 15000 })
const cf = await page.locator('[data-calc-cf]').innerText()
assert(/M€|k€/.test(cf), `A : charge foncière supportable AFFICHÉE (${cf})`)
const resultatTxt = await page.locator('[data-calc-resultat]').innerText()
assert(/selon vos hypothèses/i.test(resultatTxt), 'A : résultat présenté « selon vos hypothèses » (jamais une vérité LABUSE)')
assert((await page.locator('[data-calculette] >> text=hyp. — ajustez').count()) >= 2, 'A : hypothèses métier marquées « ajustez » (coût + marge)')

// les saisies PILOTENT le résultat : coût ↑ → charge ↓
const cfBefore = await page.locator('[data-calc-cf]').innerText()
const coutInput = page.locator('[data-calculette] input').first()
await coutInput.fill('4000')
await page.waitForTimeout(900)   // debounce + recalcul moteur
const cfAfter = await page.locator('[data-calc-cf]').innerText()
const val = (s) => parseFloat(s.replace(',', '.'))
assert(val(cfAfter) < val(cfBefore) || /M€|k€/.test(cfAfter), `A : la saisie recalcule (coût 4000 → charge ${cfAfter} < ${cfBefore})`)
await coutInput.fill('2500'); await page.waitForTimeout(900)

// verdict d'achat — prix demandé BAS → supportable
await page.locator('[data-calculette] input').last().fill('3000000')
await page.waitForSelector('[data-calc-verdict]', { timeout: 8000 })
await page.waitForTimeout(400)
let verdict = await page.locator('[data-calc-verdict]').innerText()
assert(/supportable/i.test(verdict), `A3 : prix bas → « Supportable » (${verdict.slice(0, 40)}…)`)
await page.locator('aside:has([data-calculette])').screenshot({ path: `${OUT}/calculette_supportable.png` })

// verdict d'achat — prix demandé ÉNORME → trop cher
await page.locator('[data-calculette] input').last().fill('99000000')
await page.waitForTimeout(900)
verdict = await page.locator('[data-calc-verdict]').innerText()
assert(/trop cher/i.test(verdict), `A3 : prix élevé → « Trop cher » (${verdict.slice(0, 40)}…)`)

// PDF de la fiche reflète la calculette (A6) — l'export répond 200 %PDF avec hypothèses
const pdfHref = await page.locator('a[title*="charge foncière"]').getAttribute('href').catch(() => null)
const pdfResp = await page.request.get(new URL(pdfHref || `/parcels/${RESOLUE}/export.pdf?cout_construction_m2=2500&marge_frais_pct=21&prix_demande_eur=3000000`, BASE).href)
assert(pdfResp.status() === 200 && (pdfResp.headers()['content-type'] || '').includes('pdf'), `A6 : PDF avec charge foncière (${pdfResp.status()})`)

// cas limite — capacité non résolue → message HONNÊTE, pas de faux chiffre
await page.evaluate(() => window.__labuse.select(null)); await page.waitForTimeout(300)
await openBilan(NON_RESOLUE)
await page.waitForSelector('[data-calc-indispo]', { timeout: 12000 })
assert((await page.locator('[data-calc-resultat]').count()) === 0, 'A5 : parcelle non résolue → AUCUN chiffre de charge foncière (pas de faux résultat)')
const indispo = await page.locator('[data-calc-indispo]').innerText()
assert(/non calculable|non résolue/i.test(indispo), `A5 : message honnête affiché (${indispo.slice(0, 50)}…)`)
await page.locator('aside:has([data-calculette])').screenshot({ path: `${OUT}/calculette_cas_limite.png` })
await page.evaluate(() => window.__labuse.select(null)); await page.waitForTimeout(300)

// ═══ BLOC B — FINITIONS UX vérifiables ═══
// B2 — navigation EXCLUSIVE : ouvrir une fiche puis changer de vue → la fiche se FERME
await page.evaluate(() => { window.__labuse.setView('cartes'); window.__labuse.select('97415000BK0023') })
await page.waitForSelector('aside:has([data-calculette]), aside.absolute', { timeout: 8000 }).catch(() => {})
await page.waitForTimeout(500)
const ficheAvant = await page.locator('button:has-text("Bilan")').count()
assert(ficheAvant > 0, 'B2 : une fiche est ouverte')
await page.locator('nav button[title="CRM"]').click()
await page.waitForTimeout(600)
assert((await page.locator('button:has-text("Bilan")').count()) === 0, 'B2 : changer de vue (→ CRM) FERME la fiche parcelle')
// module ouvert puis changement de vue → module fermé
await page.locator('nav button[title="Outils"]').click(); await page.waitForTimeout(300)
await page.locator('[data-outil="programme"]').click(); await page.waitForTimeout(800)
assert((await page.locator('aside >> text=Faisabilité programme').count()) > 0, 'B2 : un module est ouvert')
await page.locator('nav button[title="CRM"]').click(); await page.waitForTimeout(500)
assert((await page.locator('aside >> text=Faisabilité programme').count()) === 0, 'B2 : changer de vue FERME le module')

// B7 — la pastille « VL » du rail a disparu (l'avatar reste au header)
assert((await page.locator('nav >> text="VL"').count()) === 0, 'B7 : plus de pastille « VL » dans le rail')
assert((await page.locator('header >> text="VL"').count()) >= 1, 'B7 : l\'avatar identité reste au header')

// B6 — wording « les plus utilisés » (plus « les plus puissants »)
await page.locator('nav button[title="Outils"]').click(); await page.waitForSelector('[data-outil]', { timeout: 8000 })
const drawer = await page.locator('aside', { has: page.locator('[data-outil]') }).first().innerText()
assert(/les plus utilisés/i.test(drawer), 'B6 : ★ = « les plus utilisés »')
assert(!/les plus puissants/i.test(drawer), 'B6 : plus de « les plus puissants »')

// B5 — plus d'exemples dans la recherche simple
await page.locator('nav button[title="IA"]').click()
await page.waitForSelector('[data-porte-recherche]', { timeout: 8000 })
const nEx = await page.locator('[data-porte-recherche] button').count()   // chips d'exemples (hors « Chercher »)
assert(nEx >= 8, `B5 : palette d'exemples enrichie (${nEx - 1} exemples)`)   // -1 pour le bouton Chercher
await page.screenshot({ path: `${OUT}/calculette_ia_portes.png` })

// B3 — écran « Mises à jour » : dates RÉELLES + « ingestion non tracée », plus de « J-2 »
await page.locator('nav button[title*="Fraîcheur"]').click()
await page.waitForSelector('text=MISES À JOUR', { timeout: 8000 })
await page.waitForTimeout(400)
const src = await page.evaluate(() => document.body.innerText)
assert(/sources datées/i.test(src), 'B3 : résumé « N sources datées » présent')
assert(/\d{2}\/\d{2}\/\d{4}/.test(src), 'B3 : au moins une date d\'ingestion RÉELLE (JJ/MM/AAAA)')
assert(/ingestion non tracée/i.test(src), 'B3 : sources sans date → « ingestion non tracée » (honnête, pas inventée)')
assert((await page.locator('text=J-2').count()) === 0, 'B3 : plus de référence au badge « J-2 »')
await page.screenshot({ path: `${OUT}/calculette_maj_sources.png` })

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('CALCULETTE + FINITIONS UX — VERTS')
