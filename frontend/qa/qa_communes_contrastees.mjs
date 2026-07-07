// PARCOURS COMPLET × COMMUNES CONTRASTÉES (mandat île, phase 3c) — le trajet carte → fiche
// → PDF → module → copilote rejoué sur une urbaine dense (Le Port), une rurale (Bras-Panon),
// une des Hauts (Cilaos), + Saint-Paul (non-régression). Compteurs vs SQL à chaque fois.
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

const COMMUNES = [
  { nom: 'Le Port', profil: 'urbaine dense' },
  { nom: 'Bras-Panon', profil: 'rurale Est' },
  { nom: 'Cilaos', profil: 'les Hauts (cirque)' },
  { nom: 'Saint-Paul', profil: 'référence (non-régression)' },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))

for (const { nom, profil } of COMMUNES) {
  console.log(`━━ ${nom} (${profil}) ━━`)
  const slug = nom.toLowerCase().replace(/[ '-]/g, '_')
  await page.goto(BASE + `#f=1&c=${encodeURIComponent(nom)}`, { waitUntil: 'domcontentloaded' })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForSelector('text=chaudes', { timeout: 25000 })
  await page.waitForTimeout(3000)

  // 1. compteurs = SQL (par statut)
  const [ch, sv, cr] = ['chaude', 'a_surveiller', 'a_creuser'].map((s) => Number(sql(
    `SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
     WHERE d.run_label='q_v2' AND p.commune='${nom.replace("'", "''")}' AND d.matrice_statut='${s}'`)))
  const head = await page.locator('text=chaudes').first().innerText()
  assert(head.includes(ch.toLocaleString('fr-FR')) && head.includes(sv.toLocaleString('fr-FR')) && head.includes(cr.toLocaleString('fr-FR')),
    `compteurs = SQL (${ch} · ${sv} · ${cr})`, head)

  // 2. carte : parcelles colorées (source geojson commune)
  const nFeat = await page.evaluate(() => {
    const m = window.__labuse_map
    return m ? m.queryRenderedFeatures({ layers: ['parcels-fill'] }).length : -1
  })
  assert(nFeat > 20, `carte colorée (${nFeat} features rendues)`)

  // 3. liste → fiche (première promue) → onglets porteurs
  const nCards = await page.locator('.overflow-y-auto > button').count()
  assert(nCards > 0, `liste non vide (${nCards} cartes)`)
  await page.locator('.overflow-y-auto > button').first().click()
  await page.waitForSelector('button[title="Analyse IA"]', { timeout: 12000 })
  const idu = await page.evaluate(() => document.querySelector('[class*="font-mono"]')?.textContent ?? '')
  assert((await page.locator('button[title="Analyse IA"]').count()) > 0, 'fiche ouverte depuis la liste')
  await page.getByRole('button', { name: 'Bilan', exact: true }).click()
  await page.waitForTimeout(2500)
  assert((await page.locator('text=CAPACITÉ').count()) > 0, 'fiche : Bilan promoteur rempli')
  await page.screenshot({ path: `${OUT}/contraste_${slug}_fiche.png` })

  // 4. PDF de la fiche courante (HTTP + %PDF)
  const pdfHref = await page.locator('a:has-text("PDF")').first().getAttribute('href')
  const pdf = await page.request.get(new URL(pdfHref, BASE).href)
  const body = await pdf.body()
  assert(pdf.status() === 200 && body.subarray(0, 5).toString() === '%PDF-', 'export PDF (200, %PDF)')
  await page.keyboard.press('Escape')

  // 5. module (M03 permis — commune-scopé) : total = SQL
  await page.locator('nav button[title="Outils"]').click()
  await page.getByRole('button', { name: /Radar permis/ }).click()
  await page.waitForSelector('text=permis', { timeout: 15000 })
  await page.waitForTimeout(1500)
  const permisSql = Number(sql(`SELECT count(*) FROM sitadel_permits WHERE commune='${nom.replace("'", "''")}'
    AND date >= (SELECT max(date) FROM sitadel_permits) - interval '24 months'`))
  const modTxt = await page.locator(`text=/\\d+ permis/`).first().innerText().catch(() => '?')
  assert(modTxt.includes(permisSql.toLocaleString('fr-FR')), `M03 total permis = SQL (${permisSql})`, modTxt)
  await page.screenshot({ path: `${OUT}/contraste_${slug}_module.png` })

  // 6. copilote : « les chaudes de <commune> » → périmètre + chip (réel ou stub)
  await page.locator('nav button[title="IA"]').click()
  await page.waitForTimeout(600)
  await page.locator('input[placeholder*="vue mer"]').fill(`les chaudes de ${nom}`)
  await page.keyboard.press('Enter')
  await page.waitForSelector('header span:has-text("Chaude")', { timeout: 25000 })
  assert((await page.locator('[data-commune-select]').innerText()).includes(nom),
    `copilote « les chaudes de ${nom} » → périmètre conservé/affiché`)
  void idu
}

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('COMMUNES CONTRASTÉES — PARCOURS COMPLET VERT')
