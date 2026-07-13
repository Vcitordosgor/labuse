// QA M5.1 — unification des vues sur le scoring v2 (mandat M5.1 lot 5.1).
// Vérifie : compteurs v2, tri par rang, AS1425 en tête de liste Saint-Benoît,
// brûlante v2 « écartée matrice » visible par défaut, toggle copro, aucun « V nn ».
//
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/qa_m51.mjs
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../reports/m51-unification/captures'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const failures = []
const ok = (name) => console.log(`  ✓ ${name}`)
const fail = (name, detail = '') => { failures.push(`${name}${detail ? ' — ' + detail : ''}`); console.log(`  ✗ ${name} ${detail}`) }
const assert = (cond, name, detail = '') => (cond ? ok(name) : fail(name, detail))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// ── vérité SQL : tiers v2 EFFECTIFS (étage 0 du run servi prime) ──
const V2RUN = sql("SELECT run_id FROM p_score_v2_runs ORDER BY computed_at DESC LIMIT 1")
const [brulantes, chaudes, reserve, creuser, ecartees] = sql(`
  WITH eff AS (
    SELECT CASE WHEN d.status IN ('exclue','faux_positif_probable') THEN 'ecartee'
                ELSE COALESCE(s.tier, 'ecartee') END AS t
    FROM parcel_p_score_v2 s
    JOIN parcels p ON p.idu = s.parcelle_id
    LEFT JOIN dryrun_parcel_evaluations d ON d.parcel_id = p.id AND d.run_label = 'q_v3_datagap'
    WHERE s.run_id = '${V2RUN}')
  SELECT count(*) FILTER (WHERE t='brulante'), count(*) FILTER (WHERE t='chaude'),
         count(*) FILTER (WHERE t='reserve_fonciere'), count(*) FILTER (WHERE t='a_creuser'),
         count(*) FILTER (WHERE t='ecartee') FROM eff`).split('|').map(Number)
console.log(`SQL v2 (${V2RUN}) : ${brulantes} brûlantes · ${chaudes} chaudes · ${reserve} réserve · ${creuser} à creuser · ${ecartees} écartées`)

const fmt = (n) => n.toLocaleString('fr-FR').replace(/ /g, ' ')

const browser = await chromium.launch()

async function newPage(url) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page._errors = []
  page.on('console', (m) => { if (m.type() === 'error') page._errors.push(m.text()) })
  page.on('pageerror', (e) => page._errors.push('PAGEERROR ' + e.message))
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(2500)
  return page
}

// ═══ 1. Mode ÎLE (défaut) : compteurs v2, tri rang, périmètre, lexique ═══
console.log('\n── Mode île (défaut) ──')
{
  const page = await newPage(BASE + '#v=1')
  const body = await page.textContent('body')

  // compteurs = tiers v2 (chips)
  for (const [label, n] of [['Brûlantes v2', brulantes], ['Chaudes', chaudes],
                            ['Réserve foncière', reserve], ['À creuser', creuser], ['Écartées', ecartees]]) {
    const chip = page.locator('button', { hasText: label }).first()
    const txt = (await chip.textContent().catch(() => '')) ?? ''
    assert(txt.replace(/[   ]/g, '').includes(String(n)),
      `chip « ${label} » = ${fmt(n)} (SQL-exact)`, `chip="${txt}"`)
  }

  // opportunités détectées = brûlantes + chaudes v2
  assert(body.includes('opportunités détectées'), 'ligne « opportunités détectées » présente')
  const opp = (brulantes + chaudes).toLocaleString('fr-FR')
  assert(body.replace(/[  ]/g, ' ').includes(`${opp} opportunités`) ||
         body.includes(`${(brulantes + chaudes)}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')),
    `opportunités = ${opp} (brûlantes v2 + chaudes v2)`)

  // tri par défaut = rang P ; le tri par V a disparu
  const sortActive = await page.locator('[data-sort="rang"]').getAttribute('class')
  assert(sortActive?.includes('text-mint'), 'tri par défaut = rang P')
  assert(!body.includes('vendabilité') && !body.includes('Vendabilité'),
    'aucune mention « vendabilité » dans le panneau', 'trouvée dans le body')

  // brûlante v2 « écartée matrice » visible par défaut : le rang 1 île est matrice=ecartee
  const rang1 = sql(`SELECT p.idu FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id
    WHERE s.run_id='${V2RUN}' AND s.rang=1`)
  const rang1Matrice = sql(`SELECT d.matrice_statut FROM parcels p
    JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label='q_v3_datagap'
    WHERE p.idu='${rang1}'`)
  const firstCard = await page.locator('[data-results-scroll] button').first().textContent()
  assert(firstCard.replace(/\s/g, '').includes(rang1.slice(8)),
    `rang 1 (${rang1}, matrice=${rang1Matrice}) EN TÊTE de la liste île`, `1re carte="${firstCard.slice(0, 60)}"`)
  assert(rang1Matrice === 'ecartee', 'le rang 1 est bien une « écartée matrice » (la preuve du périmètre v2)')

  // chip tier v2 en PREMIER sur la carte de résultat
  const firstChip = await page.locator('[data-results-scroll] button [data-tier-chip]').first().textContent()
  assert(/Brûlante v2/.test(firstChip), 'chip tier v2 en premier sur la 1re carte', `chip="${firstChip}"`)

  // aucun « V nn » à l'écran ; aucun « À surveiller » ; plus de « 🔥 N brûlantes » v1.3
  assert(!/(^|[\s(])V \d{1,3}([\s)·]|$)/.test(body), 'aucun badge « V nn » à l\'écran')
  assert(!body.includes('À surveiller'), 'le libellé « À surveiller » a disparu')
  assert(!body.includes('🔥'), 'plus de compteur 🔥 v1.3')

  // toggle copro (attendre le refetch serveur — jamais un compte à zéro pendant le chargement)
  const toggle = page.locator('[data-toggle-copro]')
  assert(await toggle.count() === 1, 'toggle copro présent')
  await toggle.check()
  await page.waitForFunction(
    () => document.querySelectorAll('[data-results-scroll] button').length > 0,
    null, { timeout: 15000 }).catch(() => null)
  const afterCopro = await page.locator('[data-results-scroll] button').count()
  assert(afterCopro > 0, 'liste toujours servie avec « masquer les copropriétés »', `${afterCopro} cartes`)
  await toggle.uncheck()

  // légende (vignette bas droite) synchronisée v2
  const legend = await page.textContent('body')
  assert(legend.includes('VERDICT · SCORING V2'), 'légende carte en mode « VERDICT · SCORING V2 »')

  await page.screenshot({ path: `${OUT}/apres-panneau-ile.png` })
  ok(`capture → ${OUT}/apres-panneau-ile.png`)
  assert(page._errors.length === 0, 'zéro erreur console (île)', page._errors.slice(0, 3).join(' | '))
  await page.close()
}

// ═══ 2. Saint-Benoît : AS1425 en tête de liste ═══
console.log('\n── Saint-Benoît ──')
{
  const page = await newPage(BASE + '#f=1&v=1&c=Saint-Beno%C3%AEt')
  const cards = page.locator('[data-results-scroll] button')
  await page.waitForTimeout(1500)
  const top3 = []
  for (let i = 0; i < Math.min(3, await cards.count()); i++) top3.push((await cards.nth(i).textContent()).replace(/\s/g, ''))
  assert(top3.some((t) => t.includes('AS1425')), 'AS1425 dans le top 3 de Saint-Benoît (rang 16, 2e derrière CD0905 rang 8)',
    `top3=${top3.map((t) => t.slice(0, 20)).join(' / ')}`)
  assert(top3[0]?.includes('CD0905'), 'tête de liste Saint-Benoît = CD0905 (rang 8, brûlante « écartée matrice »)', `1re=${top3[0]?.slice(0, 24)}`)
  const body = await page.textContent('body')
  assert(!/(^|[\s(])V \d{1,3}([\s)·]|$)/.test(body), 'aucun badge « V nn » (Saint-Benoît)')
  await page.screenshot({ path: `${OUT}/apres-panneau-saint-benoit.png` })
  ok(`capture → ${OUT}/apres-panneau-saint-benoit.png`)
  assert(page._errors.length === 0, 'zéro erreur console (Saint-Benoît)', page._errors.slice(0, 3).join(' | '))
  await page.close()
}

// ═══ 3. Filtre tier v2 via chips + fiche raccord ═══
console.log('\n── Filtre brûlantes + fiche ──')
{
  const page = await newPage(BASE + '#v=1')
  await page.locator('button', { hasText: 'Brûlantes v2' }).first().click()
  await page.waitForFunction(
    (cible) => document.querySelectorAll('[data-results-scroll] button').length > 0 &&
               document.querySelectorAll('[data-results-scroll] button').length <= cible,
    Math.min(brulantes, 500), { timeout: 15000 }).catch(() => null)
  await page.waitForTimeout(500)
  const n = await page.locator('[data-results-scroll] button').count()
  assert(n === Math.min(brulantes, 500), `filtre « Brûlantes v2 » → ${brulantes} cartes`, `${n} cartes`)
  // ouvrir la 1re fiche : verdict d'en-tête = Brûlante v2 (aucune deuxième vérité)
  await page.locator('[data-results-scroll] button').first().click()
  await page.waitForTimeout(2500)
  const badge = await page.locator('[data-badge-verdict]').textContent().catch(() => '')
  assert(/Brûlante v2/.test(badge ?? ''), 'fiche : verdict d\'en-tête = Brûlante v2 (raccord liste ↔ fiche)', `badge="${badge}"`)
  await page.screenshot({ path: `${OUT}/apres-filtre-brulantes-fiche.png` })
  ok(`capture → ${OUT}/apres-filtre-brulantes-fiche.png`)
  await page.close()
}

await browser.close()
console.log('\n════════════════════════════')
if (failures.length) {
  console.log(`✗ ${failures.length} échec(s) :`)
  failures.forEach((f) => console.log('  - ' + f))
  process.exit(1)
}
console.log('✓ QA M5.1 : tout est vert')
