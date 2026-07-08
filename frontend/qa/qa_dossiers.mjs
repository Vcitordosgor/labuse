// VAGUE 2 — DOSSIERS PROPRIÉTAIRES : compteurs croisés avec une requête SQL INDÉPENDANTE,
// en-tête « N dossiers (+X sans identité) », badge cluster VISIBLE À L'ÉCRAN sur le cas
// réel SICN (La Possession, 18 parcelles chaudes d'un même vendeur en procédure).
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// ── croisement API vs SQL indépendant (île)
const stats = await (await fetch(new URL('/stats?source=q_v2', BASE).href)).json()
const sqlDossiers = Number(sql(`
  SELECT count(DISTINCT pm.siren) FROM dryrun_parcel_evaluations d
  JOIN parcels p ON p.id=d.parcel_id
  JOIN parcelle_personne_morale pm ON pm.idu=p.idu AND pm.siren IS NOT NULL
  WHERE d.run_label='q_v2' AND d.matrice_statut='chaude'`))
const sqlSansId = Number(sql(`
  SELECT count(*) FROM dryrun_parcel_evaluations d
  JOIN parcels p ON p.id=d.parcel_id
  LEFT JOIN parcelle_personne_morale pm ON pm.idu=p.idu
  WHERE d.run_label='q_v2' AND d.matrice_statut='chaude' AND pm.siren IS NULL`))
assert(stats.dossiers_chaudes === sqlDossiers, `dossiers île API = SQL indépendant (${sqlDossiers})`, String(stats.dossiers_chaudes))
assert(stats.chaudes_sans_identite === sqlSansId, `sans-identité île API = SQL (${sqlSansId})`, String(stats.chaudes_sans_identite))
assert(stats.dossiers_chaudes + stats.chaudes_sans_identite <= stats.chaude,
  'honnêteté : dossiers + sans-identité ≤ chaudes (jamais un total prétendu exact)')

// ── /communes : La Possession porte ses dossiers
const communes = await (await fetch(new URL('/communes', BASE).href)).json()
const lp = communes.find((c) => c.commune === 'La Possession')
const lpSql = Number(sql(`
  SELECT count(DISTINCT pm.siren) FROM dryrun_parcel_evaluations d
  JOIN parcels p ON p.id=d.parcel_id
  JOIN parcelle_personne_morale pm ON pm.idu=p.idu AND pm.siren IS NOT NULL
  WHERE d.run_label='q_v2' AND d.matrice_statut='chaude' AND p.commune='La Possession'`))
assert(lp.dossiers === lpSql, `/communes La Possession : dossiers = SQL (${lpSql})`, String(lp.dossiers))

// ── UI : en-tête dossiers (île) + badge SICN VISIBLE (La Possession)
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes', { timeout: 20000 })
await page.waitForTimeout(2500)
assert((await page.locator(`text=${stats.dossiers_chaudes.toLocaleString('fr-FR')} dossiers propriétaire`).count()) > 0,
  `en-tête île : « ${stats.dossiers_chaudes} dossiers propriétaires identifiés »`)
assert((await page.locator('text=sans identité').count()) > 0, 'en-tête île : reliquat « sans identité » affiché')

await page.goto(BASE + '#f=1&c=La%20Possession&st=chaude', { waitUntil: 'domcontentloaded' })
await page.reload({ waitUntil: 'networkidle' })
await page.waitForSelector('.overflow-y-auto > button', { timeout: 25000 })
await page.waitForTimeout(2500)
const badge = page.locator('text=même proprio ×18').first()
const visible = await badge.isVisible().catch(() => false)
const box = visible ? await badge.boundingBox() : null
assert(visible && box && box.width > 0 && box.y >= 0 && box.y <= 900,
  'badge « même proprio ×18 » (SICN) VISIBLE à l’écran dans la liste La Possession')
await page.screenshot({ path: `${OUT}/dossiers_sicn.png` })
const title = await badge.getAttribute('title').catch(() => '')
assert((title ?? '').includes('SICN'), 'tooltip du badge : le nom du propriétaire (SICN)')

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('DOSSIERS PROPRIÉTAIRES — VERT')
