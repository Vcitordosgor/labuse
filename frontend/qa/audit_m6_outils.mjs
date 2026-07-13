// AUDIT M6 §1.6 — étape 5 : MENU OUTILS (19 modules) + Vues + Projets + CRM + Sources + IA.
// LECTURE SEULE : chaque module est OUVERT (GET) ; aucun formulaire soumis, aucune écriture.
// Usage : cd frontend && node qa/audit_m6_outils.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let net = [], errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 140)) })
page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 140)))
page.on('response', (r) => {
  const u = r.url().replace(/^https?:\/\/[^/]+/, '')
  if (u.startsWith('/socle') || u.includes('.pbf') || u.includes('basemap')) return
  net.push({ url: u.slice(0, 170), status: r.status() })
})

const results = []
const MODULES = [
  'Scoring v2 (P)', 'Faisabilité programme', 'Parkings APER', 'Toitures tertiaires',
  'Division parcellaire', 'Foncier fantôme', 'Scan patrimoine', 'Mode bailleur',
  'Matching promoteurs', 'Assemblage', 'Baromètre foncier', 'Radar permis',
  'Promesses mortes', 'Vélocité admin', 'Simulateur PLU', 'Simulateur ZAN',
  'Remonter le temps', 'Due diligence', 'Courrier propriétaire',
]

await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(3000)

for (const m of MODULES) {
  try {
    await page.locator('button[title="Outils"]').click()
    await page.waitForTimeout(900)
    net = []; errs = []
    await page.locator(`button:has-text("${m}")`).first().click()
    await page.waitForTimeout(4000)
    const panel = await page.evaluate(() => {
      const asides = [...document.querySelectorAll('aside, div')]
        .filter((d) => { const r = d.getBoundingClientRect(); return r.width > 280 && r.width < 560 && r.height > 400 && d.innerText?.length > 60 })
      const el = asides.sort((a, b) => b.innerText.length - a.innerText.length)[0]
      return el ? el.innerText.slice(0, 1200) : '(panneau non identifié)'
    })
    const bad = net.filter((n) => n.status >= 400)
    const statut = errs.length || bad.length ? 'CASSÉ' : (net.length === 0 && panel === '(panneau non identifié)' ? 'MORT?' : 'OK')
    const slug = m.toLowerCase().normalize('NFD').replace(/[^a-z0-9]+/g, '-').slice(0, 24)
    await page.screenshot({ path: `${OUT}/outil-${slug}.png` })
    results.push({ module: m, statut, net: net.slice(0, 6), bad, errs: errs.slice(0, 3), extrait: panel.slice(0, 400) })
    console.log(`[${statut}] ${m} — net:${net.length}${bad.length ? ' BAD:' + JSON.stringify(bad) : ''}${errs.length ? ' ERR:' + errs[0] : ''}`)
    // referme le module (bouton ✕ ou retour Cartes)
    try { await page.locator('button[title*="Fermer" i]').first().click({ timeout: 1500 }) } catch { await page.locator('button[title="Cartes"]').click() }
    await page.waitForTimeout(700)
  } catch (e) {
    results.push({ module: m, statut: 'CASSÉ (ouverture impossible)', err: e.message.slice(0, 120) })
    console.log(`[CASSÉ] ${m} — ${e.message.slice(0, 100)}`)
    await page.goto(BASE + '#f=1&v=1&c=Saint-Paul', { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
  }
}

// ── Vues : Recalculer les compteurs (GET) + ouvrir une vue preset ──
await page.locator('button[title="Vues"]').click(); await page.waitForTimeout(2500)
net = []; errs = []
await page.locator('button:has-text("Recalculer les compteurs")').click()
await page.waitForTimeout(4000)
results.push({ module: 'Vues — Recalculer les compteurs', statut: errs.length || net.some((n) => n.status >= 400) ? 'CASSÉ' : 'OK', net: net.slice(0, 5), errs: errs.slice(0, 3) })
console.log('[Vues recalcul]', JSON.stringify(net.slice(0, 5)))
net = []; errs = []
await page.locator('button:has-text("Foncier — Brûlantes & chaudes")').first().click()
await page.waitForTimeout(4000)
await page.screenshot({ path: `${OUT}/vue-foncier-ouverte.png` })
results.push({ module: 'Vues — ouvrir « Foncier — Brûlantes & chaudes »', statut: errs.length || net.some((n) => n.status >= 400) ? 'CASSÉ' : 'OK', net: net.slice(0, 8), errs: errs.slice(0, 3) })
const vueTxt = await page.evaluate(() => document.body.innerText.slice(0, 1500))
writeFileSync('../reports/m6-audit/vue-foncier-texte.txt', vueTxt)

// argumentaire (lecture)
try {
  net = []
  await page.locator('button[title="Vues"]').click(); await page.waitForTimeout(2000)
  await page.locator('button:has-text("argumentaire")').first().click(); await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/vue-argumentaire.png` })
  results.push({ module: 'Vues — argumentaire', statut: net.some((n) => n.status >= 400) ? 'CASSÉ' : 'OK', net: net.slice(0, 4) })
  await page.keyboard.press('Escape')
} catch (e) { results.push({ module: 'Vues — argumentaire', statut: 'CASSÉ (clic)', err: e.message.slice(0, 80) }) }

// ── Projets : Ouvrir (rejouer, lecture) ──
try {
  await page.locator('button[title="Projets"]').click(); await page.waitForTimeout(2200)
  net = []; errs = []
  await page.locator('button[title*="rejouer" i], button:has-text("Ouvrir")').first().click()
  await page.waitForTimeout(4500)
  await page.screenshot({ path: `${OUT}/projet-rejoue.png` })
  const postOk = net.filter((n) => n.status >= 400)
  results.push({ module: 'Projets — Ouvrir (rejouer)', statut: errs.length || postOk.length ? 'CASSÉ' : 'OK', net: net.slice(0, 8), errs: errs.slice(0, 3) })
  console.log('[Projets Ouvrir]', JSON.stringify(net.slice(0, 6)))
} catch (e) { results.push({ module: 'Projets — Ouvrir', statut: 'CASSÉ (clic)', err: e.message.slice(0, 100) }) }

// ── CRM : clic IDU → fiche ──
try {
  await page.locator('button[title="CRM"]').click(); await page.waitForTimeout(2200)
  await page.screenshot({ path: `${OUT}/crm-kanban.png` })
  net = []; errs = []
  await page.locator('button[title="Ouvrir la fiche sur la carte"]').first().click()
  await page.waitForTimeout(3500)
  await page.screenshot({ path: `${OUT}/crm-vers-fiche.png` })
  results.push({ module: 'CRM — ouvrir fiche depuis kanban', statut: errs.length ? 'CASSÉ' : 'OK', net: net.slice(0, 5), errs: errs.slice(0, 3) })
} catch (e) { results.push({ module: 'CRM — ouvrir fiche', statut: 'CASSÉ (clic)', err: e.message.slice(0, 100) }) }

// ── IA : suggestion + Chercher (GET/stub) ──
try {
  await page.locator('button[title="IA"]').click(); await page.waitForTimeout(1500)
  net = []; errs = []
  await page.locator('button:has-text("chaudes avec vue mer de plus de 1 000 m²")').click()
  await page.waitForTimeout(1000)
  await page.locator('button:has-text("Chercher")').first().click()
  await page.waitForTimeout(5000)
  await page.screenshot({ path: `${OUT}/ia-recherche.png` })
  const iaTxt = await page.evaluate(() => document.body.innerText.slice(0, 1200))
  writeFileSync('../reports/m6-audit/ia-resultat.txt', iaTxt)
  results.push({ module: 'IA — recherche NL (suggestion)', statut: errs.length || net.some((n) => n.status >= 400) ? 'CASSÉ' : 'OK', net: net.slice(0, 6), errs: errs.slice(0, 3) })
  console.log('[IA]', JSON.stringify(net.slice(0, 5)))
} catch (e) { results.push({ module: 'IA — recherche NL', statut: 'CASSÉ (clic)', err: e.message.slice(0, 100) }) }

// ── Sources : page + bouton Imprimer (intercepté) ──
try {
  await page.locator('button[title^="Fraîcheur"]').click(); await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/sources-page.png` })
  await page.evaluate(() => { window.print = () => { window.__printed = true } })
  await page.locator('button:has-text("Imprimer")').click(); await page.waitForTimeout(800)
  const printed = await page.evaluate(() => window.__printed === true)
  results.push({ module: 'Sources — Imprimer', statut: printed ? 'OK (window.print)' : 'MORT?', net: [] })
  console.log('[Sources Imprimer] printed=', printed)
} catch (e) { results.push({ module: 'Sources — Imprimer', statut: 'CASSÉ (clic)', err: e.message.slice(0, 100) }) }

writeFileSync('../reports/m6-audit/outils-resultats.json', JSON.stringify(results, null, 1))
console.log(`\n${results.length} modules/écrans testés → reports/m6-audit/outils-resultats.json`)
await browser.close()
