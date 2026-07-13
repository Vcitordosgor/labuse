// M6 §1.5 — AUDIT LECTURE SEULE du menu Outils.
// LOT 0 : inventaire réel du tiroir. Puis chaque outil : ouverture, requête type EN LECTURE,
// rendu, erreurs console/réseau. AUCUN POST qui écrit en base (matching run/add : NON testés).
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { createRequire } from 'node:module'
const require = createRequire('/Users/openclaw/Desktop/labuse/frontend/qa/_resolve.js')
const { chromium } = require('playwright')

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/reports/m6-audit/captures-1-5'
const DB = 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()
const digits = (s) => Number(String(s).replace(/\D+/g, ''))
const report = { inventaire: [], outils: {}, mutabilite: {} }

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
let consoleErrors = []
let netErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('pageerror', (e) => consoleErrors.push('PAGEERROR ' + e.message))
page.on('response', (r) => { if (r.status() >= 400) netErrors.push(`${r.status()} ${r.url()}`) })
const drain = () => { const c = [...consoleErrors], n = [...netErrors]; consoleErrors = []; netErrors = []; return { console: c, net: n } }

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 45000 })
await page.waitForTimeout(3000)
drain()

// ───────── LOT 0 : inventaire du tiroir Outils tel qu'affiché ─────────
await page.locator('nav button[title="Outils"]').click()
await page.waitForTimeout(500)
report.inventaire = await page.evaluate(() => {
  const groups = [...document.querySelectorAll('[data-outil-group]')]
  return groups.flatMap((g) => {
    const groupLabel = g.querySelector('h3, h4, p, span')?.textContent?.trim() || g.getAttribute('data-outil-group')
    return [...g.querySelectorAll('[data-outil]')].map((b) => ({
      key: b.getAttribute('data-outil'),
      phare: b.getAttribute('data-outil-phare') === '1',
      groupe: g.getAttribute('data-outil-group'),
      groupeLabel: groupLabel,
      texte: b.textContent.trim().slice(0, 120),
    }))
  })
})
await page.screenshot({ path: `${OUT}/lot0_tiroir.png` })
console.log('LOT0 inventaire:', JSON.stringify(report.inventaire, null, 1))

async function openTool(key, label) {
  // ré-ouvre le tiroir si besoin
  if (!(await page.locator('[data-outil]').first().isVisible().catch(() => false))) {
    await page.locator('nav button[title="Outils"]').click()
    await page.waitForTimeout(400)
  }
  await page.locator(`[data-outil="${key}"]`).click()
  await page.waitForTimeout(2200)
  const opened = (await page.locator('aside h2', { hasText: label }).count()) > 0
  return opened
}

async function finish(key, extra = {}) {
  await page.waitForTimeout(800)
  const errs = drain()
  report.outils[key] = { ...extra, consoleErrors: errs.console, netErrors: errs.net }
  await page.screenshot({ path: `${OUT}/outil_${key}.png` })
  await page.locator('aside button[title="Fermer le module"]').click().catch(() => {})
  await page.waitForTimeout(300)
  console.log(`✔ ${key}:`, JSON.stringify(report.outils[key]))
}

// ── scoring-v2
{
  const ok = await openTool('scoring-v2', 'Scoring v2')
  await page.waitForTimeout(1500)
  const nRows = await page.locator('aside .overflow-y-auto button').count()
  const sqlBrulantes = sql(`SELECT count(*) FROM parcel_p_score_v2 s2 JOIN parcels p ON p.idu=s2.parcelle_id JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label='q_v3_datagap' WHERE s2.tier='brulante' AND s2.run_id LIKE 'm36-l2f%' AND d.status NOT IN ('exclue','faux_positif_probable')`)
  await finish('scoring-v2', { ok, rowsAffichees: nRows, sqlBrulantesEffectives: Number(sqlBrulantes) })
}

// ── programme (M22) — POST lecture seule
{
  const ok = await openTool('programme', 'Faisabilité programme')
  await page.getByRole('button', { name: 'Trouver les parcelles' }).click()
  await page.waitForTimeout(4000)
  const t = await page.locator('text=parcelles candidates').innerText().catch(() => 'ABSENT')
  await finish('programme', { ok, candidates: t })
}

// ── parkings-aper (M23)
{
  const ok = await openTool('parkings-aper', 'Parkings APER')
  await page.waitForTimeout(2000)
  const t = await page.locator('text=parkings assujettis').innerText().catch(() => 'ABSENT')
  const sqlN = sql("SELECT count(*) FROM parkings_aper WHERE tranche IS NOT NULL")
  await finish('parkings-aper', { ok, compteurUI: t, sqlAssujettis: Number(sqlN) })
}

// ── toitures-tertiaires (M24)
{
  const ok = await openTool('toitures-tertiaires', 'Toitures tertiaires')
  await page.waitForTimeout(2500)
  const t = await page.locator('aside p.text-\\[11px\\]', { hasText: 'toitures' }).first().innerText().catch(() => 'ABSENT')
  await finish('toitures-tertiaires', { ok, compteurUI: t })
}

// ── division (M01)
{
  const ok = await openTool('division', 'Division parcellaire')
  await page.waitForTimeout(2000)
  const t = await page.locator('text=candidats (SQL)').innerText().catch(() => 'ABSENT')
  const sqlN = sql('SELECT count(*) FROM module_division WHERE score >= 70')
  const first = await page.locator('aside .overflow-y-auto > button').first().innerText().catch(() => 'ABSENT')
  await finish('division', { ok, compteurUI: t, sqlScore70: Number(sqlN), premierItem: first.replace(/\n/g, ' | ') })
}

// ── fantome (M07)
{
  const ok = await openTool('fantome', 'Foncier fantôme')
  await page.waitForTimeout(2500)
  const t = await page.locator('text=parcelles gelées').innerText().catch(() => 'ABSENT')
  await finish('fantome', { ok, compteurUI: t })
}

// ── patrimoine (M02)
{
  const ok = await openTool('patrimoine', 'Scan patrimoine')
  await page.locator('aside input').fill('CBO')
  await page.waitForTimeout(1200)
  await page.getByRole('button', { name: /CBO TERRITORIA/ }).first().click().catch(() => {})
  await page.waitForTimeout(2500)
  const t = await page.locator('aside', { hasText: 'parcelles' }).locator('text=parcelles').first().innerText().catch(() => 'ABSENT')
  const sqlN = sql("SELECT count(*) FROM parcelle_personne_morale WHERE siren='452038805'")
  await finish('patrimoine', { ok, parcellesUI: t, sqlCBO: Number(sqlN) })
}

// ── bailleur (M06)
{
  const ok = await openTool('bailleur', 'Mode bailleur')
  await page.waitForTimeout(2500)
  const t = await page.locator('text=parcelles promues en QPV').innerText().catch(() => 'ABSENT')
  await finish('bailleur', { ok, compteurUI: t })
}

// ── matching (M19) — LECTURE SEULE : ni ajout de profil, ni run (écrit event_log)
{
  const ok = await openTool('matching', 'Matching promoteurs')
  await page.waitForTimeout(1500)
  const profils = await page.locator('aside .overflow-y-auto > div').count()
  const demos = await page.locator('aside text=DÉMO').count().catch(() => 0)
  await finish('matching', { ok, profilsAffiches: profils, notaBene: 'run/add NON testés (écriture base interdite)' })
}

// ── assemblage (M16) — 2 clics carte puis analyse (POST lecture seule)
{
  const ok = await openTool('assemblage', 'Assemblage')
  // zoom sur deux parcelles contiguës connues (Saint-Paul BH0283/BH0122)
  const center = sql("SELECT ST_X(ST_Centroid(ST_Transform(geom_2975,4326))) || ',' || ST_Y(ST_Centroid(ST_Transform(geom_2975,4326))) FROM parcels WHERE idu='97415000BH0283'")
  const [lon, lat] = center.split(',').map(Number)
  await page.evaluate(([lo, la]) => { window.location.hash = `#c=Saint-Paul&ll=${lo},${la}&z=18` }, [lon, lat])
  await page.waitForTimeout(4000)
  drain() // le rechargement commune peut générer du bruit réseau hors sujet
  const box = await page.locator('.maplibregl-canvas').first().boundingBox()
  if (box) {
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
    await page.waitForTimeout(900)
    await page.mouse.click(box.x + box.width / 2 + 40, box.y + box.height / 2)
    await page.waitForTimeout(900)
  }
  const chips = await page.locator('aside button[title="Retirer de la sélection"]').count()
  let result = 'non lancé'
  if (chips >= 2) {
    await page.getByRole('button', { name: /Analyser l'assiette/ }).click()
    await page.waitForTimeout(2500)
    result = await page.locator('text=score d\'assemblage').innerText().catch(() => 'ERREUR rendu')
  }
  await finish('assemblage', { ok, chips, result })
}

// ── barometre (M18)
{
  const ok = await openTool('barometre', 'Baromètre foncier')
  await page.waitForTimeout(2000)
  const trimestres = await page.locator('aside .shrink-0.flex-col > div').count()
  const pdf = await page.request.get(BASE.replace(/\/socle\/$/, '') + '/moteurs/barometre.pdf')
  await finish('barometre', { ok, lignesTrimestres: trimestres, pdfStatus: pdf.status(), pdfType: pdf.headers()['content-type'] })
}

// ── permis (M03)
{
  const ok = await openTool('permis', 'Radar permis')
  await page.waitForTimeout(2500)
  const t = await page.locator('aside p', { hasText: 'permis' }).first().innerText().catch(() => 'ABSENT')
  const banner = await page.locator('aside', { hasText: 'Données jusqu' }).locator('b').first().innerText().catch(() => 'ABSENT')
  await finish('permis', { ok, compteurUI: t, donneesJusquAu: banner })
}

// ── promesses (M04)
{
  const ok = await openTool('promesses', 'Promesses mortes')
  await page.waitForTimeout(2500)
  const t = await page.locator('text=promesses mortes').innerText().catch(() => 'ABSENT')
  await finish('promesses', { ok, compteurUI: t })
}

// ── velocite (M05)
{
  const ok = await openTool('velocite', 'Vélocité admin')
  await page.waitForTimeout(2000)
  const rows = await page.locator('aside .grid.grid-cols-\\[1fr_54px_58px_54px\\]').count()
  await finish('velocite', { ok, lignes: rows - 1 })
}

// ── simulplu (M15)
{
  const ok = await openTool('simulplu', 'Simulateur PLU')
  await page.waitForTimeout(1500)
  await page.locator('aside .flex-wrap button').first().click().catch(() => {})
  await page.waitForTimeout(3000)
  const t = await page.locator('text=ratio analogie').innerText().catch(() => 'ABSENT')
  await finish('simulplu', { ok, resume: t })
}

// ── zan (M17)
{
  const ok = await openTool('zan', 'Simulateur ZAN')
  await page.waitForTimeout(2500)
  const t = await page.locator('text=ZAN-compatibles').innerText().catch(() => 'ABSENT')
  await finish('zan', { ok, compteurUI: t })
}

// ── temps (M08)
{
  const ok = await openTool('temps', 'Remonter le temps')
  await page.waitForTimeout(3500)
  const handle = await page.locator('button[title="Glisser pour comparer"]').count()
  const labels = await page.locator('text=1950-1965').count()
  await finish('temps', { ok, poignee: handle, label1950: labels })
}

// ── duediligence (M10) — POST lecture seule
{
  const ok = await openTool('duediligence', 'Due diligence')
  await page.locator('aside textarea').fill('97415000AC0253')
  await page.getByRole('button', { name: 'Analyser le lot' }).click()
  await page.waitForTimeout(3000)
  const t = await page.locator('text=références trouvées').innerText().catch(() => 'ABSENT')
  await finish('duediligence', { ok, resultat: t })
}

// ── courriers (M09) — génération pure (aucune écriture, aucun envoi)
{
  const ok = await openTool('courriers', 'Courrier propriétaire')
  await page.locator('aside textarea').fill('97415000AC0253')
  await page.waitForTimeout(400)
  await page.getByRole('button', { name: /Générer 1 courrier/ }).click()
  await page.waitForTimeout(2500)
  const t = await page.locator('aside .line-clamp-3').first().innerText().catch(() => 'ABSENT')
  await finish('courriers', { ok, extrait: t.slice(0, 90) })
}

// ───────── Mutabilité (bouton d'en-tête, hors tiroir) ─────────
{
  await page.evaluate(() => { window.location.hash = '' })
  await page.waitForTimeout(2500)
  drain()
  await page.getByRole('button', { name: 'Mutabilité', exact: true }).click()
  await page.waitForTimeout(2500)
  const legend = await page.locator('text=MUTABILITÉ').count()
  const gradient = await page.locator('text=SDP résiduelle').count()
  const errs = drain()
  report.mutabilite = { legendVisible: legend > 0, gradientLegende: gradient > 0, consoleErrors: errs.console, netErrors: errs.net }
  await page.screenshot({ path: `${OUT}/mode_mutabilite.png` })
  await page.getByRole('button', { name: 'Verdict', exact: true }).click()
  console.log('✔ mutabilite:', JSON.stringify(report.mutabilite))
}

console.log('\n=== RAPPORT JSON ===')
console.log(JSON.stringify(report, null, 2))
await browser.close()
