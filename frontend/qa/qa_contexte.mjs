// CONTEXTE COMMUNE (mandat promotrice) — volet VISIBLE sur 3 communes contrastées SRU
// (carencée / conforme / exemptée), chiffres croisés avec SQL indépendant, couche
// équipements visible + cliquable, PDF AC0253 avec bloc contexte.
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

// 3 communes contrastées — les statuts sortent de la BASE, pas d'un souvenir
const CAS = [
  { commune: 'Saint-Leu', attendu: 'CARENCÉE' },
  { commune: 'Le Port', attendu: 'CONFORME' },
  { commune: 'Salazie', attendu: 'EXEMPTÉE 2023-2025' },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))

for (const { commune, attendu } of CAS) {
  await page.goto(BASE + `#f=1&c=${encodeURIComponent(commune)}`, { waitUntil: 'domcontentloaded' })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForSelector('text=chaudes', { timeout: 25000 })
  await page.waitForTimeout(1500)
  await page.locator('[data-contexte-btn]').click()
  await page.waitForSelector('[data-contexte-panel]', { timeout: 10000 })
  await page.waitForTimeout(1800)
  // badge SRU VISIBLE + valeur = SQL indépendant
  const sqlTaux = sql(`SELECT taux_lls FROM commune_contexte_sru WHERE commune='${commune.replace("'", "''")}'`)
  const badge = page.locator(`[data-contexte-panel] >> text=${attendu}`).first()
  const vis = await badge.isVisible().catch(() => false)
  assert(vis, `${commune} : badge « ${attendu} » VISIBLE`)
  assert((await page.locator(`[data-contexte-panel] >> text=SRU ${Number(sqlTaux).toLocaleString('fr-FR')}`).count()) > 0,
    `${commune} : taux SRU affiché = SQL (${sqlTaux} %)`)
  // marché : logements = SQL
  const sqlLog = sql(`SELECT logements FROM commune_insee_logement WHERE commune='${commune.replace("'", "''")}'`)
  assert((await page.locator(`[data-contexte-panel] >> text=${Number(sqlLog).toLocaleString('fr-FR')}`).count()) > 0,
    `${commune} : logements INSEE affichés = SQL (${sqlLog})`)
  // sources cliquables
  assert((await page.locator('[data-contexte-panel] a[target="_blank"]').count()) >= 2,
    `${commune} : sources cliquables (≥2 liens)`)
  await page.screenshot({ path: `${OUT}/contexte_${commune.toLowerCase().replace(/[ '-]/g, '_')}.png` })
  await page.keyboard.press('Escape')
}

// ── NPNRU dans le volet (Le Port) + fiche parcelle « dans / adjacente »
await page.goto(BASE + '#f=1&c=Le%20Port', { waitUntil: 'domcontentloaded' })
await page.reload({ waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes', { timeout: 25000 })
await page.locator('[data-contexte-btn]').click()
await page.waitForSelector('[data-contexte-panel]', { timeout: 10000 })
await page.waitForTimeout(1500)
assert((await page.locator('text=1ère et 2ème Couronne').count()) > 0, 'volet Le Port : quartier NPNRU listé')
await page.keyboard.press('Escape')

// ── couche équipements : visible + cliquable à l'écran
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.29, -20.94], zoom: 14.5 }))
await page.waitForTimeout(1000)
await page.getByRole('button', { name: 'Équipements' }).click()
await page.waitForTimeout(2500)
const nEquip = await page.evaluate(() => window.__labuse_map.queryRenderedFeatures({ layers: ['ov-equip'] }).length)
assert(nEquip > 0, `équipements rendus à l'écran (${nEquip})`)
const pt = await page.evaluate(() => {
  const m = window.__labuse_map
  const f = m.queryRenderedFeatures({ layers: ['ov-equip'] })[0]
  const px = m.project(f.geometry.coordinates)
  const r = m.getCanvas().getBoundingClientRect()   // le cercle fait ~4 px : l'offset canvas compte
  return { x: r.left + px.x, y: r.top + px.y, cat: f.properties.subtype }
})
await page.mouse.click(pt.x, pt.y)
await page.waitForTimeout(800)
assert((await page.locator('.maplibregl-popup').count()) > 0, `clic équipement → popup (${pt.cat})`)
await page.screenshot({ path: `${OUT}/contexte_equipements.png` })

// ── PDF AC0253 : bloc contexte présent (texte extrait côté API)
const pdf = await page.request.get(new URL('/parcels/97415000AC0253/export.pdf?source=q_v2', BASE).href)
assert(pdf.status() === 200 && (await pdf.body()).subarray(0, 5).toString() === '%PDF-', 'PDF AC0253 : 200 + %PDF')
const pdfTxt = execFileSync('/Users/openclaw/Desktop/labuse/.venv/bin/python', ['-c', `
from pypdf import PdfReader
import io, urllib.request
data = urllib.request.urlopen('${new URL('/parcels/97415000AC0253/export.pdf?source=q_v2', BASE).href}').read()
t = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)
print('CONTEXTE COMMUNE' in t and 'SRU :' in t and 'INSEE RP 2023' in t)`], { encoding: 'utf8' }).trim()
assert(pdfTxt === 'True', 'PDF AC0253 : bloc CONTEXTE COMMUNE (SRU + INSEE) présent')

// ── RTAA DOM (5bis) : bloc VISIBLE dans le Bilan de la fiche + références cliquables
await page.goto(BASE + '#f=1&c=Saint-Paul', { waitUntil: 'domcontentloaded' })
await page.reload({ waitUntil: 'networkidle' })
await page.waitForSelector('.overflow-y-auto > button', { timeout: 25000 })
await page.keyboard.press('/'); await page.keyboard.type('AC0253'); await page.keyboard.press('Enter')
await page.waitForSelector('button[title="Analyse IA"]', { timeout: 12000 })
await page.getByRole('button', { name: 'Bilan', exact: true }).click()
await page.waitForSelector('[data-rtaa-block]', { timeout: 15000 })
const rtaaVisible = await page.locator('[data-rtaa-block]').isVisible()
assert(rtaaVisible, 'fiche Bilan : bloc RTAA DOM VISIBLE')
await page.locator('[data-rtaa-block] button').click()
await page.waitForTimeout(600)
const refs = await page.locator('[data-rtaa-block] a[target="_blank"]').count()
assert(refs >= 8, `RTAA : références Légifrance cliquables (${refs})`)
const legifrance = await page.locator('[data-rtaa-block] a[href*="legifrance"]').count()
assert(legifrance >= 8, `RTAA : liens Légifrance (${legifrance})`)
assert((await page.locator('text=seuils d’altitude 400/600 m').count()) + (await page.locator("text=400/600").count()) > 0,
  'RTAA : seuils d’altitude énoncés')
await page.screenshot({ path: `${OUT}/contexte_rtaa.png` })
await page.keyboard.press('Escape')

// PDF : bloc RTAA présent (espaces d'extraction tolérés)
const rtaaPdf = execFileSync('/Users/openclaw/Desktop/labuse/.venv/bin/python', ['-c', `
from pypdf import PdfReader
import io, re, urllib.request
data = urllib.request.urlopen('${new URL('/parcels/97415000AC0253/export.pdf?source=q_v2', BASE).href}').read()
t = re.sub(r'\\s+', ' ', ''.join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages))
print(all(k in t for k in ('RTAA DOM', 'chaleur renouvelables', 'R.192-2', '17/04/2009')))`], { encoding: 'utf8' }).trim()
assert(rtaaPdf === 'True', 'PDF AC0253 : bloc RTAA DOM (ECS renouvelable + références) présent')

// ── page Sources : nouvelles sources listées (note ZUS/ZFU incluse)
const sources = await (await fetch(new URL('/sources', BASE).href)).json()
const noms = sources.map((s) => s.name).join('|')
assert(noms.includes('Inventaire SRU'), 'Sources : Inventaire SRU (DHUP) listé')
assert(noms.includes('NPNRU'), 'Sources : NPNRU (DEAL/ANCT) listé')
assert(noms.includes('INSEE RP Logement 2023'), 'Sources : INSEE RP 2023 listé')
assert(noms.includes('RTAA DOM'), 'Sources : RTAA DOM (textes réglementaires) listé')

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('CONTEXTE COMMUNE — VERT')
