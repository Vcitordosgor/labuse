// CORRECTIFS REVUE VIC (07/07 soir) — C1..C7 en conditions réelles, assertions de VISIBILITÉ.
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

// ── C1 : serveur lancé (par le harnais) hors racine + env nu → provider RÉEL avec cause nulle
const st = await (await fetch(new URL('/ia/status', BASE).href)).json()
assert(st.provider === 'anthropic' && st.raison === null,
  `C1 : IA réelle quel que soit le lanceur (provider=${st.provider}, raison=${st.raison})`)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes', { timeout: 20000 })
await page.waitForTimeout(2500)

// ── C2 : UN seul logo (le path officiel) visible à l'écran
const logos = await page.evaluate(() =>
  [...document.querySelectorAll('svg path')].filter((p) =>
    (p.getAttribute('d') || '').startsWith('M2 15 C58')).filter((p) => {
    const r = p.closest('svg').getBoundingClientRect()
    return r.width > 0 && r.height > 0
  }).length)
assert(logos === 1, `C2 : un seul logo à l'écran (${logos})`)
await page.screenshot({ path: `${OUT}/correctif_c2_logo.png` })

// ── C3 : sous z10 en île, le fond actif est la variante SANS labels
const activeBm = await page.evaluate(() => {
  const m = window.__labuse_map
  return ['bm-carto', 'bm-carto-nolabels'].find((id) => m.getLayoutProperty(id, 'visibility') === 'visible')
})
assert(activeBm === 'bm-carto-nolabels', `C3 : fond sans labels sous z10 (${activeBm})`)
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.269, -21.01], zoom: 14 }))
await page.waitForTimeout(1500)
const activeBm2 = await page.evaluate(() => {
  const m = window.__labuse_map
  return ['bm-carto', 'bm-carto-nolabels'].find((id) => m.getLayoutProperty(id, 'visibility') === 'visible')
})
assert(activeBm2 === 'bm-carto', `C3 : labels de retour aux zooms parcellaires (${activeBm2})`)
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.53, -21.13], zoom: 9.5 }))
await page.waitForTimeout(1200)
await page.screenshot({ path: `${OUT}/correctif_c3_labels.png` })

// ── C4 : cadrage positif + popover entonnoir = SQL indépendant
assert((await page.locator('text=opportunités détectées').count()) > 0, 'C4 : cadrage positif « → opportunités détectées »')
assert((await page.locator('button:has-text("Opportunités")').count()) > 0, 'C4 : chip « Opportunités » (ex-Tout)')
await page.locator('[data-entonnoir-btn]').click()
await page.waitForSelector('[data-entonnoir-popover]', { timeout: 8000 })
await page.waitForTimeout(1200)
const sqlBaties = sql(`SELECT n FROM entonnoir_motifs WHERE run_label='q_v2' AND commune='__ile__' AND motif='déjà bâtie'`)
assert((await page.locator(`[data-entonnoir-popover] >> text=${Number(sqlBaties).toLocaleString('fr-FR')}`).count()) > 0,
  `C4 : motif « déjà bâtie » affiché = SQL (${sqlBaties})`)
assert((await page.locator('text=trié pour vous').count()) > 0, 'C4 : langage « LABUSE a trié pour vous »')
await page.screenshot({ path: `${OUT}/correctif_c4_entonnoir.png` })
await page.keyboard.press('Escape')
await page.mouse.click(700, 100)

// ── C5 : CR1231 (96 ha Saint-Pierre) raconte son histoire
await page.locator('input[placeholder*="Rechercher"]').fill('97416000CR1231')
await page.keyboard.press('Enter')
await page.waitForSelector('button[title="Analyse IA"]', { timeout: 12000 })
assert((await page.locator('text=· ÉVÉNEMENT').first().isVisible()), 'C5 : chip statut « · ÉVÉNEMENT » (fiche CR1231)')
const histoire = page.locator('[data-histoire-evenement]')
assert(await histoire.isVisible(), 'C5 : phrase-histoire visible (CR1231)')
const htxt = await histoire.innerText()
assert(htxt.includes('Chaude par') && htxt.includes('procédure'), 'C5 : la phrase dit propriétaire + procédure')
await page.screenshot({ path: `${OUT}/correctif_c5_evenement.png` })
await page.keyboard.press('Escape')

// ── C6 : clic couche désactivée (île) → toast VISIBLE
await page.getByRole('button', { name: 'Zonage PLU' }).click()
await page.waitForSelector('[data-toast]', { timeout: 5000 })
assert(await page.locator('[data-toast]').isVisible(), 'C6 : toast visible au clic sur couche désactivée')
assert((await page.locator('[data-toast]').innerText()).includes('commune'), 'C6 : le toast donne la marche à suivre')
await page.screenshot({ path: `${OUT}/correctif_c6_toast.png` })

// ── C7 : trame cadastrale + clic universel + écartées opt-in + omnibox écartée
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.269, -21.01], zoom: 14.5 }))
await page.waitForTimeout(3500)
const trame = await page.evaluate(() => window.__labuse_map.queryRenderedFeatures({ layers: ['ile-limites'] }).length)
assert(trame > 200, `C7 : trame cadastrale VISIBLE par défaut (${trame} contours rendus, mode île z14.5)`)
// clic sur une parcelle ÉCARTÉE de la trame (feature non promue) → fiche assumée
const ecartee = await page.evaluate(() => {
  const m = window.__labuse_map
  const f = m.queryRenderedFeatures({ layers: ['ile-fill'] }).find((x) => x.properties.status === 'ecartee')
  if (!f) return null
  const ring = f.geometry.type === 'Polygon' ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0]
  const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length
  const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length
  const px = m.project([cx, cy])
  const r = m.getCanvas().getBoundingClientRect()
  return { x: r.left + px.x, y: r.top + px.y, idu: f.properties.idu }
})
assert(!!ecartee, 'C7 : une écartée existe dans la trame rendue (z14.5)')
await page.mouse.click(ecartee.x, ecartee.y)
await page.waitForSelector('[data-bandeau-ecartee]', { timeout: 12000 })
assert(await page.locator('[data-bandeau-ecartee]').isVisible(), `C7 : fiche écartée assumée (« voici pourquoi ») — ${ecartee.idu}`)
await page.screenshot({ path: `${OUT}/correctif_c7_ecartee.png` })
await page.keyboard.press('Escape')
await page.locator('input[placeholder*="Rechercher"]').fill('')
// chip Écartées opt-in → la liste change
const before = await page.locator('.overflow-y-auto > button').count()
await page.getByRole('button', { name: /^Écartées/ }).click()
// pendant le refetch la liste montre des squelettes (div) — attendre les cartes, pas une durée
await page.waitForFunction(() => document.querySelectorAll('.overflow-y-auto > button').length > 0, null, { timeout: 20000 })
const after = await page.locator('.overflow-y-auto > button').count()
assert(after > 0 && (await page.locator('button:has-text("Écartées")').first().innerText()).length > 0,
  `C7 : chip Écartées opt-in → liste peuplée (${before}→${after})`)
await page.getByRole('button', { name: /^Écartées/ }).click()
// omnibox : une écartée cherchée explicitement doit sortir
const iduEcartee = sql(`SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
  WHERE d.run_label='q_v2' AND p.commune='Sainte-Rose' AND d.matrice_statut='ecartee' LIMIT 1`)
await page.locator('input[placeholder*="Rechercher"]').fill(iduEcartee)
await page.keyboard.press('Enter')
await page.waitForSelector('[data-bandeau-ecartee]', { timeout: 12000 })
assert(true, `C7 : omnibox remonte une écartée explicite (${iduEcartee})`)

// clic universel : un point SANS feature promue à z11 (tuiles promues-only) → résolution serveur
await page.keyboard.press('Escape')
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.47, -20.905], zoom: 11 }))
await page.waitForTimeout(2500)
const r = await page.evaluate(() => {
  const m = window.__labuse_map
  const rect = m.getCanvas().getBoundingClientRect()
  return { x: rect.left + rect.width * 0.5, y: rect.top + rect.height * 0.45 }
})
await page.mouse.click(r.x, r.y)
await page.waitForSelector('button[title="Analyse IA"]', { timeout: 12000 }).catch(() => null)
assert((await page.locator('button[title="Analyse IA"]').count()) > 0,
  'C7 : clic UNIVERSEL — un point sans feature vectorielle résout sa parcelle côté serveur')

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('CORRECTIFS REVUE VIC — VERTS')
