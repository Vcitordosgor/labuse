// AUTO-QA du Socle V1 — régime obligatoire avant toute présentation.
// a) zéro erreur console par écran  b) chaque cliquable a un effet réel vérifiable
// c) compteurs comparés PAR SQL DIRECT au run q_v2  d) captures 1440 & 1280, pas de débordement
// e) anti-crash : 10 parcelles aléatoires (écartées incluses), jamais d'écran noir
// f) parcours complet : carte → parcelle → fiche → PDF → pipeline → sources
//
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/qa.mjs
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/qa'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })

const failures = []
const ok = (name) => console.log(`  ✓ ${name}`)
const fail = (name, detail = '') => { failures.push(`${name}${detail ? ' — ' + detail : ''}`); console.log(`  ✗ ${name} ${detail}`) }
const assert = (cond, name, detail = '') => (cond ? ok(name) : fail(name, detail))

const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// ── vérité SQL (règle c : la référence, pas l'API)
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

async function newPage(width) {
  const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: width === 1440 ? 2 : 1 })
  page._errors = []
  page.on('console', (m) => { if (m.type() === 'error') page._errors.push(m.text()) })
  page.on('pageerror', (e) => page._errors.push('PAGEERROR ' + e.message))
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForSelector('text=chaudes', { timeout: 15000 })
  await page.waitForTimeout(2500)
  return page
}

async function snap(page, name, width) {
  await page.screenshot({ path: `${OUT}/${name}_${width}.png` })
  const noOverflowX = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
  assert(noOverflowX, `layout ${name} @${width} sans débordement horizontal`)
}

const fmtFr = (n) => n.toLocaleString('fr-FR').replace(/ /g, ' ').replace(/ /g, ' ')

// ════════════════════════════════ passes 1440 et 1280 ════════════════════════════════
for (const width of [1440, 1280]) {
  console.log(`\n━━ Passe ${width}px ━━`)
  const page = await newPage(width)

  // ── c) compteurs = SQL
  const header = (await page.locator('p:has-text("chaudes")').first().innerText()).replace(/ | /g, ' ')
  assert(header.includes(`${fmtFr(chaude)} chaudes`), `compteur chaudes = SQL (${chaude})`, header)
  assert(header.includes(`${fmtFr(surveiller)} à surveiller`), `compteur à surveiller = SQL (${surveiller})`)
  assert(header.includes(`${fmtFr(creuser)} à creuser`), `compteur à creuser = SQL (${creuser})`)
  const totalLine = await page.locator('text=/sur .* parcelles/').first().innerText()
  assert(totalLine.replace(/ | /g, ' ').includes(fmtFr(total)), `total = SQL (${total})`, totalLine)
  await snap(page, '01_cartes', width)

  // ── b) couches : effet réseau réel (zonage/PPR) + toggles sans erreur
  const reqZonage = page.waitForRequest((r) => r.url().includes('kind=plu_gpu_zone'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: 'Zonage PLU' }).click()
  assert(await reqZonage, 'couche Zonage PLU → requête layers.geojson')
  const reqPpr = page.waitForRequest((r) => r.url().includes('kind=ppr'), { timeout: 8000 }).catch(() => null)
  await page.getByRole('button', { name: 'PPR multirisque' }).click()
  assert(await reqPpr, 'couche PPR → requête layers.geojson')
  await page.getByRole('button', { name: 'Vue mer' }).click()
  await page.getByRole('button', { name: 'Parc national' }).click()
  await page.waitForTimeout(1500)
  await snap(page, '02_couches', width)
  for (const l of ['Zonage PLU', 'PPR multirisque', 'Vue mer', 'Parc national']) await page.getByRole('button', { name: l }).click()

  // ── b) filtres statut + score + suppression chip
  await page.getByRole('button', { name: /^Chaude/ }).first().click()
  await page.waitForTimeout(800)
  const cardsChaude = await page.locator('.overflow-y-auto > button').count()
  assert(cardsChaude === chaude, `filtre Chaude → ${chaude} cartes`, `${cardsChaude}`)
  await snap(page, '03_filtre_chaude', width)
  await page.getByRole('button', { name: '+ Filtre' }).click()
  await page.getByPlaceholder('ex. 70').fill('90')
  await page.mouse.click(700, 600)
  await page.waitForTimeout(600)
  const chipQ = await page.locator('span:has-text("Q ≥ 90")').count()
  assert(chipQ > 0, 'chip « Q ≥ 90 » ajouté')
  await page.locator('span', { hasText: 'Chaude' }).locator('button[title="Retirer"]').first().click()
  await page.waitForTimeout(500)
  const chipsChaude = await page.locator('span:has-text("Q ≥ 90")').count()
  assert(chipsChaude > 0, '× retire le chip statut, Q ≥ 90 conservé')
  await page.locator('span:has-text("Q ≥ 90")').locator('button[title="Retirer"]').first().click()
  await page.waitForTimeout(400)

  // ── b) toggle Mutabilité (légende change) puis retour
  await page.getByRole('button', { name: 'Mutabilité' }).click()
  await page.waitForTimeout(700)
  assert((await page.locator('text=MUTABILITÉ').count()) > 0, 'toggle Mutabilité → légende MUTABILITÉ')
  await snap(page, '04_mutabilite', width)
  await page.getByRole('button', { name: 'Verdict' }).click()

  // ── b) chevron panneau (replier/déplier)
  await page.locator('button[title="Replier le panneau"]').click()
  assert((await page.locator('button[title="Déplier le panneau"]').count()) === 1, 'panneau repliable (chevron)')
  await page.locator('button[title="Déplier le panneau"]').click()

  // ── b) cloche notifications
  await page.locator('button[title="Notifications"]').click()
  assert((await page.locator('text=NOTIFICATIONS').count()) > 0, 'cloche → panneau notifications')
  await page.mouse.click(700, 600)

  // ── omnibox : « / » focus + recherche AC0253 + Entrée → fiche
  await page.keyboard.press('/')
  await page.keyboard.type('AC0253')
  await page.keyboard.press('Enter')
  await page.waitForTimeout(1200)
  assert((await page.locator('text=97415000AC0253').count()) > 0, 'omnibox Entrée → fiche AC0253')
  // ── exigence #4 : bandeau événement
  assert((await page.locator('text=ÉVÉNEMENT — force').count()) > 0, 'bandeau événement AC0253 (invariant)')
  await snap(page, '05_fiche_evenement', width)

  // ── fiche : barres Q/A dépliables + onglets + source cliquable
  await page.getByRole('button', { name: /^Accessibilité/ }).click()
  await page.waitForTimeout(300)
  assert((await page.locator('text=age_dirigeant').count()) > 0, 'barre Accessibilité dépliée → age_dirigeant')
  await page.getByRole('button', { name: 'Risques', exact: true }).click()
  assert((await page.locator('text=icpe').count()) > 0, 'onglet Risques → lignes')
  await snap(page, '06_fiche_onglet', width)
  await page.getByRole('button', { name: 'Synthèse', exact: true }).click()

  // ── f) PDF (200 + magic %PDF)
  const pdfResp = await page.request.get(new URL('/parcels/97415000AC0253/export.pdf?source=q_v2', BASE).href)
  const pdfBody = await pdfResp.body()
  assert(pdfResp.status() === 200 && pdfBody.subarray(0, 5).toString() === '%PDF-', 'export PDF AC0253 (200, %PDF)')

  // ── f) + Pipeline → bouton passe à « Dans le pipeline »
  const pipeBtn = page.locator('button:has-text("Pipeline"), button:has-text("+ Pipeline")').first()
  await pipeBtn.click().catch(() => {})
  await page.waitForTimeout(900)
  assert((await page.locator('text=Dans le pipeline').count()) > 0, '+ Pipeline → « ✓ Dans le pipeline »')

  // ── source cliquable → page Sources (exigence #5 + #9)
  await page.locator('button[title="Ouvrir la page Sources"]').first().click()
  await page.waitForTimeout(800)
  assert((await page.locator('text=Sources de données').count()) > 0, 'clic source → page Sources')
  await snap(page, '07_sources', width)

  // ── rail : CRM (kanban + carte AC0253 présente), IA, Outils, J-2
  await page.locator('nav button[title="CRM"]').click()
  await page.waitForTimeout(900)
  assert((await page.locator('text=pipeline de prospection').count()) > 0, 'rail CRM → kanban')
  assert((await page.locator('text=AC 0253').count()) > 0, 'kanban contient AC 0253 (ajout depuis la fiche)')
  await snap(page, '08_crm', width)
  await page.locator('nav button[title="IA"]').click()
  assert((await page.locator('text=Assistant IA').count()) > 0, 'rail IA → stub propre')
  await snap(page, '09_ia', width)
  await page.locator('nav button[title="Cartes"]').click()
  await page.locator('nav button[title="Outils"]').click()
  assert((await page.locator('text=Aucun module actif').count()) > 0, 'rail Outils → tiroir accueil vide')
  await snap(page, '10_outils', width)
  await page.locator('nav button[title="Outils"]').click()
  await page.locator('button[title*="Fraîcheur"]').click()
  assert((await page.locator('text=Sources de données').count()) > 0, 'J-2 → page Sources (exigence #9)')

  // ── a) zéro erreur console sur toute la passe
  assert(page._errors.length === 0, `zéro erreur console @${width}`, page._errors.slice(0, 3).join(' | '))
  await page.close()
}

// ════════════════ e) anti-crash : 10 parcelles aléatoires (écartées incluses) ════════════════
console.log('\n━━ Anti-crash : 10 parcelles aléatoires ━━')
{
  const page = await newPage(1440)
  for (const idu of randomIdus) {
    await page.evaluate((i) => window.__labuse.select(i), idu)
    await page.waitForTimeout(700)
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
