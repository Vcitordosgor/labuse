// AUTO-QA du Socle V1 (+ cycle polish) — régime obligatoire avant toute présentation.
// a) zéro erreur console par écran  b) chaque cliquable a un effet réel vérifiable
// c) compteurs comparés PAR SQL DIRECT au run q_v2  d) captures 1440 & 1280, pas de débordement
// e) anti-crash : 10 parcelles aléatoires  f) parcours complet fiche→PDF→pipeline→sources
// g) polish : drawer source, fonds IGN + orthos historiques, 3D, mesure, zone, filtres v2, URL, identité
//
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/qa.mjs
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&v=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = process.env.OUT || '../docs/design/captures/qa'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const failures = []
const ok = (name) => console.log(`  ✓ ${name}`)
const fail = (name, detail = '') => { failures.push(`${name}${detail ? ' — ' + detail : ''}`); console.log(`  ✗ ${name} ${detail}`) }
const assert = (cond, name, detail = '') => (cond ? ok(name) : fail(name, detail))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

const [chaude, surveiller, creuser, total] = sql(
  `SELECT count(*) FILTER (WHERE matrice_statut='chaude'),
          count(*) FILTER (WHERE matrice_statut='a_surveiller'),
          count(*) FILTER (WHERE matrice_statut='a_creuser'), count(*)
   FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
   WHERE d.run_label='q_v2' AND p.commune='Saint-Paul'`).split('|').map(Number)
console.log(`SQL q_v2 : ${chaude} chaudes · ${surveiller} à surveiller · ${creuser} à creuser · ${total} total`)

const randomIdus = sql(
  `SELECT string_agg(idu, ',') FROM (
     SELECT p.idu FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
     WHERE d.run_label='q_v2' AND p.commune='Saint-Paul' ORDER BY md5(p.idu) LIMIT 10) t`).split(',')

const browser = await chromium.launch()

async function newPage(width, url = BASE + SP) {
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: width === 1440 ? 2 : 1 })
  page._errors = []
  page.on('console', (m) => { if (m.type() === 'error') page._errors.push(m.text()) })
  page.on('pageerror', (e) => page._errors.push('PAGEERROR ' + e.message))
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForSelector('text=chaudes', { timeout: 15000 })
  await page.waitForTimeout(2200)
  return page
}

async function snap(page, name, width) {
  await page.screenshot({ path: `${OUT}/${name}_${width}.png` })
  const noOverflowX = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
  assert(noOverflowX, `layout ${name} @${width} sans débordement horizontal`)
}

const fmtFr = (n) => n.toLocaleString('fr-FR').replace(/ /g, ' ').replace(/ /g, ' ')
const mapClick = (page, x, y) => page.mouse.click(x, y)

// ════════════════════════════════ passes 1440 et 1280 ════════════════════════════════
for (const width of [1440, 1280]) {
  console.log(`\n━━ Passe ${width}px ━━`)
  const page = await newPage(width)

  // identité
  assert((await page.title()) === 'LABUSE — Radar foncier', 'titre d’onglet LABUSE')
  const fav = await page.request.get(new URL('/socle/favicon-32.png', BASE).href)
  assert(fav.status() === 200, 'favicon 32px servi')

  // c) compteurs = SQL
  const header = (await page.locator('p:has-text("chaudes")').first().innerText()).replace(/ | /g, ' ')
  assert(header.includes(`${fmtFr(chaude)} chaudes`), `compteur chaudes = SQL (${chaude})`, header)
  assert(header.includes(`${fmtFr(surveiller)} à surveiller`), `compteur à surveiller = SQL (${surveiller})`)
  assert(header.includes(`${fmtFr(creuser)} à creuser`), `compteur à creuser = SQL (${creuser})`)
  // C4 (revue Vic) : cadrage positif « N parcelles analysées → M opportunités détectées »
  const totalLine = await page.locator('text=/parcelles analysées/').first().innerText()
  assert(totalLine.replace(/ | /g, ' ').includes(fmtFr(total)), `total = SQL (${total})`)
  await snap(page, '01_cartes', width)

  // b) couches (effet réseau réel)
  const reqZonage = page.waitForRequest((r) => r.url().includes('kind=plu_gpu_zone'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: 'Zonage PLU' }).click()
  assert(await reqZonage, 'couche Zonage PLU → requête layers.geojson')
  const reqPpr = page.waitForRequest((r) => r.url().includes('kind=ppr'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: 'PPR multirisque' }).click()
  assert(await reqPpr, 'couche PPR → requête layers.geojson')
  await page.getByRole('button', { name: 'Vue mer' }).click()
  await page.getByRole('button', { name: 'Parc national' }).click()
  await page.getByRole('button', { name: 'Limites parcelles' }).click()
  await page.waitForTimeout(1400)
  await snap(page, '02_couches', width)
  for (const l of ['Zonage PLU', 'PPR multirisque', 'Vue mer', 'Parc national', 'Limites parcelles']) await page.getByRole('button', { name: l }).click()

  // g) fonds de plan IGN + remonter le temps (tuiles Géoplateforme réellement demandées)
  const reqPlan = page.waitForRequest((r) => r.url().includes('PLANIGNV2'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: /Fond de plan|Sombre/ }).click()
  await page.getByRole('button', { name: 'Plan IGN' }).click()
  assert(await reqPlan, 'fond Plan IGN → tuiles Géoplateforme')
  await page.waitForTimeout(1200)
  await snap(page, '11_fond_plan_ign', width)
  const req1950 = page.waitForRequest((r) => r.url().includes('1950-1965'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: '1950-1965' }).click()
  assert(await req1950, 'remonter le temps → ortho 1950-1965')
  await page.waitForTimeout(1600)
  await snap(page, '12_ortho_1950', width)
  await page.getByRole('button', { name: 'Sombre (Carto)' }).click()
  await page.mouse.click(700, 600)

  // g) relief 3D (tuiles MNT demandées, aucun crash)
  const reqDem = page.waitForRequest((r) => r.url().includes('elevation-tiles-prod'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: '3D' }).click()
  assert(await reqDem, 'relief 3D → tuiles MNT terrarium')
  await page.waitForTimeout(1600)
  await snap(page, '13_relief_3d', width)
  await page.getByRole('button', { name: '3D' }).click()
  await page.waitForTimeout(800)

  // g) mesure distance : 2 clics → lecture en mètres/km
  await page.locator('button[title^="Distance"]').click()
  await mapClick(page, width - 500, 400)
  await mapClick(page, width - 380, 460)
  await page.waitForTimeout(400)
  const readout = await page.locator('div.border-mint').first().innerText().catch(() => '')
  assert(/\d+(\s?m|,\d+\s?km|\.\d+\s?km)/.test(readout.replace(/ /g, ' ')), 'mesure distance → lecture', readout)
  await page.keyboard.press('Escape')

  // g) zone : triangle + double-clic → chip Zone active + compteurs « dans la zone »
  await page.locator('button[title^="Zone"]').click()
  await mapClick(page, width - 560, 330)
  await mapClick(page, width - 360, 350)
  await mapClick(page, width - 430, 520)
  await page.mouse.dblclick(width - 430, 520)
  await page.waitForTimeout(900)
  assert((await page.locator('text=Zone active').count()) > 0, 'zone dessinée → chip « Zone active »')
  assert((await page.locator('text=(dans la zone)').count()) > 0, 'compteurs libellés « dans la zone »')
  await snap(page, '14_zone', width)
  await page.locator('button[title="Retirer le filtre de zone"]').click()

  // b) filtres statut (multi) + score + suppression chip
  await page.getByRole('button', { name: /^Chaude/ }).first().click()
  await page.waitForTimeout(800)
  const cardsChaude = await page.locator('.overflow-y-auto > button').count()
  // la liste affiche 200 cartes max (« Tout voir » au-delà) — 375 chaudes à SP depuis l'île
  assert(cardsChaude === Math.min(chaude, 200), `filtre Chaude → ${Math.min(chaude, 200)} cartes affichées (${chaude} au total)`, `${cardsChaude}`)
  await snap(page, '03_filtre_chaude', width)
  await page.getByRole('button', { name: '+ Filtre' }).click()
  await page.getByPlaceholder('70').fill('90')
  await page.mouse.click(700, 640)
  await page.waitForTimeout(600)
  assert((await page.locator('span:has-text("Q ≥ 90")').count()) > 0, 'chip « Q ≥ 90 » ajouté')
  await page.locator('span', { hasText: 'Chaude' }).locator('button[title="Retirer ce filtre"]').first().click()
  await page.waitForTimeout(500)
  assert((await page.locator('span:has-text("Q ≥ 90")').count()) > 0, '× retire le chip statut, Q ≥ 90 conservé')

  // g) filtres v2 : vue mer + flag pollution + URL partageable (rechargement)
  await page.getByRole('button', { name: '+ Filtre' }).click()
  await page.getByRole('button', { name: 'Vue mer dégagée' }).click()
  await page.getByRole('button', { name: '⚑ Pollution' }).click()
  await page.mouse.click(700, 640)
  await page.waitForTimeout(700)
  assert((await page.locator('span:has-text("Vue mer")').count()) > 0, 'chip « Vue mer » ajouté')
  const url = page.url()
  assert(url.includes('vm=1') && url.includes('sol_pollue') && url.includes('q=90'), 'filtres sérialisés dans l’URL', url)
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForSelector('text=chaudes')
  await page.waitForTimeout(1500)
  assert((await page.locator('span:has-text("Vue mer")').count()) > 0, 'URL rechargée → filtres restaurés')
  await snap(page, '15_filtres_v2', width)
  // reset via popover
  await page.getByRole('button', { name: '+ Filtre' }).click()
  await page.getByRole('button', { name: 'Réinitialiser tous les filtres' }).click()
  await page.waitForTimeout(500)

  // b) toggle Mutabilité + panneau + cloche
  await page.getByRole('button', { name: 'Mutabilité' }).click()
  await page.waitForTimeout(700)
  assert((await page.locator('text=MUTABILITÉ').count()) > 0, 'toggle Mutabilité → légende')
  await snap(page, '04_mutabilite', width)
  await page.getByRole('button', { name: 'Verdict' }).click()
  await page.locator('button[title="Replier le panneau"]').click()
  assert((await page.locator('button[title="Déplier le panneau"]').count()) === 1, 'panneau repliable')
  await page.locator('button[title="Déplier le panneau"]').click()
  await page.locator('button[title="Notifications"]').click()
  assert((await page.locator('text=NOTIFICATIONS').count()) > 0, 'cloche → notifications')
  await page.mouse.click(700, 640)

  // omnibox → fiche AC0253 (invariant événement)
  await page.keyboard.press('/')
  await page.keyboard.type('AC0253')
  await page.keyboard.press('Enter')
  await page.waitForTimeout(1200)
  assert((await page.locator('text=97415000AC0253').count()) > 0, 'omnibox Entrée → fiche AC0253')
  assert((await page.locator('text=ÉVÉNEMENT — force').count()) > 0, 'bandeau événement AC0253 (invariant)')
  await snap(page, '05_fiche_evenement', width)

  // fiche : barres + onglets
  await page.getByRole('button', { name: /^Accessibilité/ }).click()
  assert((await page.locator('text=age_dirigeant').count()) > 0, 'barre Accessibilité → age_dirigeant')
  await page.getByRole('button', { name: 'Risques', exact: true }).click()
  assert((await page.locator('text=icpe').count()) > 0, 'onglet Risques → lignes')
  await page.getByRole('button', { name: 'Synthèse', exact: true }).click()

  // g) drawer source : ouvre PAR-DESSUS la fiche, Échap ferme, fiche conservée
  await page.locator('button[title="Voir la source (drawer)"]').first().click()
  await page.waitForTimeout(600)
  assert((await page.locator('text=EXTRAIT').count()) > 0, 'clic source → drawer (extrait + identité)')
  await snap(page, '16_drawer_source', width)
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
  assert((await page.locator('text=EXTRAIT').count()) === 0, 'Échap ferme le drawer')
  assert((await page.locator('text=97415000AC0253').count()) > 0, 'fiche conservée après le drawer')
  // clic-extérieur ferme aussi
  await page.locator('button[title="Voir la source (drawer)"]').first().click()
  await page.waitForTimeout(400)
  await page.mouse.click(300, 400)
  await page.waitForTimeout(400)
  assert((await page.locator('text=EXTRAIT').count()) === 0, 'clic-extérieur ferme le drawer')

  // f) PDF (200 + %PDF) — palette impression validée visuellement
  const pdfResp = await page.request.get(new URL('/parcels/97415000AC0253/export.pdf?source=q_v2', BASE).href)
  const pdfBody = await pdfResp.body()
  assert(pdfResp.status() === 200 && pdfBody.subarray(0, 5).toString() === '%PDF-', 'export PDF AC0253 (200, %PDF)')

  // f) + Pipeline / Google deep-link présent
  assert((await page.locator('a[title*="Google Maps"]').count()) === 1, 'deep-link Google Maps (fiche)')
  const pipeBtn = page.locator('button:has-text("Pipeline"), button:has-text("+ Pipeline")').first()
  await pipeBtn.click().catch(() => {})
  await page.waitForTimeout(900)
  assert((await page.locator('text=Dans le pipeline').count()) > 0, '+ Pipeline → « ✓ Dans le pipeline »')

  // Échap ferme la fiche (chasse libre)
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
  assert((await page.locator('text=97415000AC0253').count()) === 0, 'Échap ferme la fiche')

  // rail : CRM / IA / Outils / J-2
  await page.locator('nav button[title="CRM"]').click()
  await page.waitForTimeout(900)
  assert((await page.locator('text=pipeline de prospection').count()) > 0, 'rail CRM → kanban')
  assert((await page.locator('text=AC 0253').count()) > 0, 'kanban contient AC 0253')
  await snap(page, '08_crm', width)
  await page.locator('nav button[title="IA"]').click()
  assert((await page.locator('text=Copilote').count()) > 0, 'rail IA → Copilote (recherche NL)')
  await page.locator('nav button[title="Cartes"]').click()
  await page.locator('nav button[title="Outils"]').click()
  assert((await page.locator('text=M01').count()) > 0, 'rail Outils → catalogue de modules')
  await page.locator('nav button[title="Outils"]').click()
  await page.locator('button[title*="Fraîcheur"]').click()
  assert((await page.locator('text=Sources de données').count()) > 0, 'J-2 → page Sources')
  await snap(page, '07_sources', width)

  assert(page._errors.length === 0, `zéro erreur console @${width}`, page._errors.slice(0, 3).join(' | '))
  await page.close()
}

// ════════════════ e) anti-crash : 10 parcelles aléatoires ════════════════
console.log('\n━━ Anti-crash : 10 parcelles aléatoires ━━')
{
  const page = await newPage(1440)
  for (const idu of randomIdus) {
    await page.evaluate((i) => window.__labuse.select(i), idu)
    await page.waitForTimeout(650)
    const shown = (await page.locator(`text=${idu}`).count()) > 0
    const black = await page.evaluate(() => document.body.innerText.trim().length < 40)
    assert(shown && !black, `fiche ${idu} rendue sans écran noir`)
    await page.evaluate(() => window.__labuse.select(null))
  }
  assert(page._errors.length === 0, 'zéro erreur console (anti-crash)', page._errors.slice(0, 3).join(' | '))
  await page.close()
}

await browser.close()
console.log(`\n${'═'.repeat(60)}`)
if (failures.length) {
  console.log(`ÉCHEC — ${failures.length} problème(s) :`)
  failures.forEach((f) => console.log('  ✗ ' + f))
  process.exit(1)
}
console.log('AUTO-QA 100 % VERTE')
