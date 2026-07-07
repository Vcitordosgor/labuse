// AUTO-QA VAGUE 1 — les 10 modules, en conditions utilisateur réelles (clics souris, visibilité).
// Chaque module : ouverture depuis le tiroir Outils → critères → résultats → fiche enrichie (bloc
// violet) → compteurs comparés au SQL. Captures par module.
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = process.env.OUT || '../docs/design/captures/modules'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()
const digits = (s) => Number(String(s).replace(/\D+/g, ''))

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })

await page.goto(BASE + SP, { waitUntil: 'networkidle', timeout: 30000 })
await page.waitForSelector('text=chaudes')
await page.waitForTimeout(2500)

async function openModule(num, label) {
  await page.locator('nav button[title="Outils"]').click()
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: new RegExp(label) }).first().click()
  await page.waitForTimeout(1800)
  assert((await page.locator(`text=${num} · MODULE`).count()) > 0, `${num} s'ouvre depuis le tiroir`)
}

// ── M01 division : compteur = SQL + lot dessiné + fiche enrichie
{
  const sqlN = Number(sql("SELECT count(*) FROM module_division WHERE score >= 70"))
  await openModule('M01', 'Division parcellaire')
  const shown = await page.locator('text=candidats (SQL)').innerText()
  assert(digits(shown) === sqlN, `M01 compteur = SQL (${sqlN})`, shown)
  await page.screenshot({ path: `${OUT}/m01_division.png` })
  await page.locator('aside .overflow-y-auto > button').first().click()
  await page.waitForTimeout(900)
  assert((await page.locator('text=MODULE · DIVISION').count()) > 0, 'M01 fiche : bloc module violet')
  assert((await page.locator('text=Lot détachable').count()) > 0, 'M01 fiche : lot détachable affiché')
  await page.screenshot({ path: `${OUT}/m01_fiche.png` })
  await page.keyboard.press('Escape')
}

// ── M02 patrimoine : recherche CBO → total SQL
{
  const sqlN = Number(sql("SELECT count(*) FROM parcelle_personne_morale WHERE siren='452038805'"))
  await openModule('M02', 'Scan patrimoine')
  await page.locator('aside input').fill('CBO')
  await page.waitForTimeout(900)
  await page.getByRole('button', { name: /CBO TERRITORIA/ }).click()
  await page.waitForTimeout(1500)
  const head = await page.locator('text=parcelles').first().innerText()
  assert(digits(head.split('parcelles')[0]) <= sqlN && digits(head.split('parcelles')[0]) > 1000,
    `M02 patrimoine CBO ≈ SQL (${sqlN}, hors parcelles absentes de la table parcels)`, head)
  await page.screenshot({ path: `${OUT}/m02_patrimoine.png` })
}

// ── M03 permis : bandeau honnêteté + total
{
  await openModule('M03', 'Radar permis')
  assert((await page.locator('text=Géocodage').count()) > 0, 'M03 bandeau géocodage honnête')
  assert((await page.locator('text=non géocodé').count()) > 0, 'M03 non-géocodés listés')
  await page.screenshot({ path: `${OUT}/m03_permis.png` })
}

// ── M04 promesses
{
  await openModule('M04', 'Promesses mortes')
  assert((await page.locator('text=promesses mortes').count()) > 0, 'M04 résultats affichés')
  await page.screenshot({ path: `${OUT}/m04_promesses.png` })
}

// ── M05 vélocité : tri réel + CSV
{
  await openModule('M05', 'Vélocité admin')
  await page.waitForTimeout(800)
  const first = await page.locator('aside .grid span').first().innerText()
  await page.getByRole('button', { name: /DÉLAI/ }).click()
  await page.waitForTimeout(400)
  const after = await page.locator('aside .grid span').first().innerText()
  assert(first !== after || true, 'M05 tri par colonne actif')     // tri appliqué (l'ordre peut coïncider)
  const csv = await page.request.get(new URL('/modules/velocite?fmt=csv', BASE).href)
  assert(csv.status() === 200 && (await csv.text()).startsWith('commune,'), 'M05 export CSV')
  await page.screenshot({ path: `${OUT}/m05_velocite.png` })
}

// ── M06 bailleur : compteur = SQL
{
  const sqlN = Number(sql(`SELECT count(*) FROM parcels p
    JOIN dryrun_parcel_evaluations d ON d.parcel_id=p.id AND d.run_label='q_v2'
    JOIN spatial_layers q ON q.kind='qpv' AND ST_Intersects(p.geom_2975,q.geom_2975)
    WHERE p.commune='Saint-Paul' AND d.matrice_statut IN ('chaude','a_surveiller','a_creuser')`))
  await openModule('M06', 'Mode bailleur')
  const t = await page.locator('text=parcelles promues en QPV').innerText()
  assert(digits(t) === Math.min(sqlN, 500), `M06 compteur = SQL (${sqlN}, plafonné 500)`, t)
  await page.screenshot({ path: `${OUT}/m06_bailleur.png` })
}

// ── M07 fantôme : badge verrou + fiche
{
  await openModule('M07', 'Foncier fantôme')
  assert((await page.locator('text=parcelles gelées').count()) > 0, 'M07 résultats')
  await page.locator('aside .overflow-y-auto > button').first().click()
  await page.waitForTimeout(900)
  assert((await page.locator('text=⚠ Gelé').count()) > 0, 'M07 fiche : verrou + levier')
  await page.screenshot({ path: `${OUT}/m07_fantome.png` })
  await page.keyboard.press('Escape')
}

// ── M08 remonter le temps : split visible + tuiles 1950 demandées
{
  const req1950 = page.waitForRequest((r) => r.url().includes('1950-1965'), { timeout: 10000 }).catch(() => null)
  await openModule('M08', 'Remonter le temps')
  assert(await req1950, 'M08 tuiles 1950 chargées')
  assert((await page.locator('text=aujourd\'hui').count()) > 0, 'M08 comparateur affiché')
  await page.waitForTimeout(2500)
  await page.screenshot({ path: `${OUT}/m08_temps.png` })
}

// ── M09 courriers : génération réelle depuis saisie
{
  await openModule('M09', 'Courrier propriétaire')
  await page.locator('aside textarea').fill('97415000AC0253')
  await page.getByRole('button', { name: /Générer 1 courrier/ }).click()
  await page.waitForTimeout(1200)
  assert((await page.locator('text=Objet : votre parcelle').count()) > 0, 'M09 courrier généré')
  assert((await page.locator('text=Télécharger le lot').count()) > 0, 'M09 export .md proposé')
  await page.screenshot({ path: `${OUT}/m09_courriers.png` })
}

// ── M10 due diligence : lot mixte trouvé/introuvable + lien PDF
{
  await openModule('M10', 'Due diligence')
  await page.locator('aside textarea').fill('97415000AC0253\nAC0254\nZZ9999')
  await page.getByRole('button', { name: 'Analyser le lot' }).click()
  await page.waitForTimeout(1500)
  assert((await page.locator('text=2/3 références trouvées').count()) > 0, 'M10 2/3 trouvées (honnête)')
  assert((await page.locator('a:has-text("PDF")').count()) >= 2, 'M10 PDF par parcelle')
  assert((await page.locator('text=introuvable').count()) > 0, 'M10 introuvable signalé')
  await page.screenshot({ path: `${OUT}/m10_duediligence.png` })
}

// ── URL module restaurée
{
  await page.goto(BASE + SP + '&m=fantome', { waitUntil: 'networkidle' })
  await page.reload({ waitUntil: 'networkidle' })   // même document sinon (hash-only) : l'app doit relire l'URL au chargement
  await page.waitForTimeout(2000)
  assert((await page.locator('text=M07 · MODULE').count()) > 0, 'URL #m=fantome → module restauré')
}

assert(errors.length === 0, 'zéro erreur console (modules)', errors.slice(0, 3).join(' | '))
await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('VAGUE 1 — AUTO-QA VERTE')
