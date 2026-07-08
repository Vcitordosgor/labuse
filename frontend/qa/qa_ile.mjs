// AUTO-QA ÎLE — le mode « Toute l'île » en conditions utilisateur réelles : sélecteur,
// tuiles MVT, compteurs SQL-exacts, liste serveur, omnibox distante, copilote → commune,
// honnêteté des outils commune-scopés. À lancer de préférence APRÈS le run complet.
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

// ── API /communes : les 24, bbox, chaudes
const communes = await (await fetch(new URL('/communes', BASE).href)).json()
assert(communes.length === 24, `/communes → 24 (${communes.length})`)
assert(communes.every((c) => /^974\d\d$/.test(c.insee) && Array.isArray(c.bbox) && c.bbox.length === 4),
  '/communes → insee + bbox pour chacune')

// ── UI : défaut île
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
const consoleErrors = []
page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 120)) })
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes', { timeout: 20000 })
await page.waitForTimeout(2500)
assert((await page.locator('[data-commune-select]').innerText()).includes('Toute l’île'), 'défaut = « Toute l’île »')

// compteurs = SQL île (le /stats est mis en cache 30 s : on compare à l'API, source affichée)
const stats = await (await fetch(new URL('/stats?source=q_v2', BASE).href)).json()
const head = await page.locator('text=chaudes').first().innerText()
assert(head.includes(Number(stats.chaude).toLocaleString('fr-FR')), `compteur chaudes île = API (${stats.chaude})`, head)
await page.screenshot({ path: `${OUT}/ile_defaut.png` })

// ── MVT : tuiles rendues + clic → fiche
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.269, -21.01], zoom: 15.2 }))
await page.waitForTimeout(3500)
const nFeat = await page.evaluate(() => window.__labuse_map.queryRenderedFeatures({ layers: ['ile-fill'] }).length)
assert(nFeat > 500, `MVT rendu @z15 (${nFeat} features)`)
const pt = await page.evaluate(() => {
  const m = window.__labuse_map
  const f = m.queryRenderedFeatures({ layers: ['ile-fill'] })[12]
  if (!f) return null
  const ring = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0]
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length
  const px = m.project([cx, cy])
  const r = m.getCanvas().getBoundingClientRect()   // coords PAGE — sans l'offset, le clic
  return { x: r.left + px.x, y: r.top + px.y, idu: f.properties.idu }   // tombait dans la LISTE
})
await page.mouse.click(pt.x, pt.y)
await page.waitForSelector('button[title="Analyse IA"]', { timeout: 10000 })
assert((await page.locator('button[title="Analyse IA"]').count()) > 0, `clic tuile MVT → fiche (${pt.idu})`)
await page.screenshot({ path: `${OUT}/ile_fiche_mvt.png` })
await page.keyboard.press('Escape')

// ── honnêteté mode île : zone + couches commune-scopées désactivées AVEC marche à suivre
assert(await page.locator('button[title*="sélectionnez d’abord une commune"]').count() > 0,
  'outil zone désactivé avec marche à suivre')
assert(await page.locator('button[title*="couche servie par commune"]').count() >= 3,
  'couches zonage/PPR/parc désactivées avec marche à suivre')

// ── omnibox distante : un IDU d'une AUTRE commune que celles à l'écran
const remoteIdu = sql(`SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
  WHERE d.run_label='q_v2' AND p.commune='Sainte-Rose' AND d.matrice_statut='a_creuser' LIMIT 1`)
if (remoteIdu) {
  await page.keyboard.press('/')
  await page.keyboard.type(remoteIdu.slice(8))
  await page.keyboard.press('Enter')
  await page.waitForSelector('button[title="Analyse IA"]', { timeout: 10000 })
  assert(true, `omnibox île → fiche distante (${remoteIdu})`)
  await page.keyboard.press('Escape')
} else assert(false, 'omnibox île : IDU Sainte-Rose introuvable en base (run incomplet ?)')

// ── sélecteur → Saint-Pierre : compteurs SQL-exacts + URL + recadrage
await page.locator('[data-commune-select]').click()
await page.waitForTimeout(500)
await page.getByRole('button', { name: /^Saint-Pierre/ }).click()
await page.waitForTimeout(5000)
const spCounts = sql(`SELECT count(*) FILTER (WHERE matrice_statut='chaude') FROM dryrun_parcel_evaluations d
  JOIN parcels p ON p.id=d.parcel_id WHERE d.run_label='q_v2' AND p.commune='Saint-Pierre'`)
const head2 = await page.locator('text=chaudes').first().innerText()
assert(head2.includes(Number(spCounts).toLocaleString('fr-FR')), `compteur chaudes Saint-Pierre = SQL (${spCounts})`, head2)
assert(page.url().includes('c=Saint-Pierre'), 'URL porte la commune (c=Saint-Pierre)')
const center = await page.evaluate(() => { const c = window.__labuse_map.getCenter(); return [c.lng, c.lat] })
const spBbox = communes.find((c) => c.commune === 'Saint-Pierre').bbox
assert(center[0] > spBbox[0] - 0.02 && center[0] < spBbox[2] + 0.02 && center[1] > spBbox[1] - 0.02 && center[1] < spBbox[3] + 0.02,
  'carte recadrée sur Saint-Pierre')
await page.screenshot({ path: `${OUT}/ile_saint_pierre.png` })

// ── copilote (réel ou stub) : « les chaudes de Saint-Denis » → périmètre + chip
await page.locator('nav button[title="IA"]').click()
await page.waitForTimeout(600)
await page.locator('input[placeholder*="vue mer"]').fill('les chaudes de Saint-Denis')
await page.keyboard.press('Enter')
await page.waitForSelector('header span:has-text("Chaude")', { timeout: 20000 })
assert((await page.locator('[data-commune-select]').innerText()).includes('Saint-Denis'),
  'copilote « les chaudes de Saint-Denis » → périmètre Saint-Denis')
assert((await page.locator('header span:has-text("Chaude")').count()) > 0, 'copilote → chip Chaude')
await page.screenshot({ path: `${OUT}/ile_copilote_commune.png` })

// ── retour « Toute l'île »
await page.locator('[data-commune-select]').click()
await page.waitForTimeout(500)
await page.getByRole('button', { name: 'Toute l’île 24 communes' }).click()
await page.waitForTimeout(2500)
assert((await page.locator('[data-commune-select]').innerText()).includes('Toute l’île'), 'retour « Toute l’île »')
assert(!page.url().includes('c='), 'URL sans commune en mode île')

assert(consoleErrors.length === 0, 'zéro erreur console (mode île)', consoleErrors.slice(0, 3).join(' | '))
await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('MODE ÎLE — AUTO-QA VERTE')
