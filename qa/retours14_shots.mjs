// RETOURS-14 — recette navigateur + captures S1-S11. PHASE=avant|apres.
// Lancer depuis frontend/ (copie locale) : CHROME=<exe> PHASE=apres node ./retours14_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-14/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean)   // ex. ONLY=S5,S6
const run = (s) => !ONLY.length || ONLY.includes(s)

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  shot', n, SUFFIX) }
const outil = async (key) => {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1200)
  await page.click('[data-rail="outils"]')
  await page.waitForTimeout(500)
  await page.click(`[data-outil="${key}"]`)
  await page.waitForTimeout(1400)
}
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2500)
  await page.mouse.click(400, 860)
  await page.waitForTimeout(300)
}
const drawer = async () => {
  if (!(await page.locator('[data-couches-drawer]').count())) { await page.click('[data-couches-toggle]'); await page.waitForTimeout(500) }
}
const toggleLayer = async (key) => { await drawer(); await page.click(`[data-layer="${key}"]`); await page.waitForTimeout(1800) }
const report = {}

// ── S1 — Communes : DEUX portes, DEUX tableaux distincts ──
if (run('S1')) {
  await outil('communes')
  await shot('S1-communes-portes')
  await page.click('[data-communes-porte="evolution"]')
  await page.waitForTimeout(2500)
  report.S1_titre_evolution = await page.locator('[data-modale] h2, [data-evolution-table] h2, h2').first().innerText().catch(() => '?')
  await shot('S1-evolution-modale')
  await outil('communes')
  const porteRadar = page.locator('[data-communes-porte="radar-marche"]')
  report.S1_porte_radar = await porteRadar.count()
  if (await porteRadar.count()) {
    await porteRadar.click()
    await page.waitForTimeout(3000)
    report.S1_titre_radar = await page.locator('[data-radar-table] h2, h2').first().innerText().catch(() => '?')
    await shot('S1-radar-modale')
  }
}

// ── S2 — liens secondaires JAUNES en permanence + survol opaque ──
if (run('S2')) {
  await outil('communes')
  await page.click('[data-communes-porte="comparaison"]')   // le tableau porte « Scan patrimoine → »
  await page.waitForTimeout(2500)
  let lien = page.locator('.hover-jaune').first()
  report.S2_liens = await page.locator('.hover-jaune').count()
  if (!(await lien.count())) lien = page.locator('button:has-text("Scan patrimoine")').first()   // avant : lien mint
  if (await lien.count()) {
    report.S2_couleur_repos = await lien.evaluate((el) => getComputedStyle(el).color)
    await shot('S2-lien-repos')
    await lien.hover()
    await page.waitForTimeout(400)
    report.S2_fond_survol = await lien.evaluate((el) => getComputedStyle(el).backgroundColor)
    await shot('S2-lien-survol')
  }
}

// ── S3 — annuaire PLU : 24 cartes uniformes, RNU cliquable ──
if (run('S3')) {
  await outil('plu')
  await page.click('[data-plu-voie="annuaire"]').catch(() => {})
  await page.waitForTimeout(2500)
  await shot('S3-annuaire')
  // la commune RNU est CLIQUABLE et son écran offre le lien Légifrance (après) — avant : cul-de-sac
  const rnuCard = page.locator('[data-plu-commune]', { hasText: 'RNU' }).first()
  if (await rnuCard.count()) {
    await rnuCard.click()
    await page.waitForTimeout(2000)
    report.S3_rnu_lien = await page.locator('[data-plu-rnu-lien]').count()
    await shot('S3-rnu-ecran')
  } else report.S3_rnu_lien = 'carte RNU introuvable'
}

// ── S4 — taxe d'aménagement : entrée = barre + clic carte + surface préremplie ──
if (run('S4')) {
  await outil('taxe-amenagement')
  report.S4_attente = await page.locator('[data-taxe-attente]').count()
  report.S4_barre = await page.locator('[data-taxe-parcelle]').count()
  await shot('S4-entree')
  await page.fill('[data-taxe-parcelle]', 'BZ1065')
  await page.press('[data-taxe-parcelle]', 'Enter')
  await page.waitForTimeout(2500)
  const cand = page.locator('[data-parcelinput-candidat]')
  if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(2500) }
  report.S4_surface = await page.locator('[data-taxe-field="surface"]').inputValue().catch(() => '')
  await shot('S4-parcelle-designee')
}

// ── S5 — permis : liste (badge « localisation approximative ») + hôtel posé par la géométrie ──
if (run('S5')) {
  // NB : cache-buster de query obligatoire — un goto qui ne change que le hash ne recharge pas la SPA
  await page.goto(`${BASE}?s5=1#m=permis`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(3000)
  await page.click('[data-permis-geo="nongeo"]').catch(() => {})
  await page.waitForTimeout(2000)
  report.S5_badges_approx = await page.locator('[data-permis-badge-nongeo]').count()
  await shot('S5-permis-liste-nongeo')
  // l'hôtel : PC 97441816A0077 rattaché par la géométrie d'époque → point sur le chantier (ortho)
  await page.click('[data-permis-geo="tous"]').catch(() => {})
  await page.waitForTimeout(1500)
  await basemap('Ortho IGN')
  await page.evaluate(() => window.__labuse_map?.jumpTo({ center: [55.512, -20.8942], zoom: 17.5 }))
  await page.waitForTimeout(4500)
  await shot('S5-hotel-ortho')
  // fiche parcelle actuelle → le PC de la parcelle d'origine remonte
  await page.goto(`${BASE}?s5=2#idu=97418000BC0331`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(3500)
  // le PC de la parcelle d'ORIGINE remonte dans « Autour de cette parcelle » (permis < 200 m, ici 0 m)
  const autour = page.locator('text=Autour de cette parcelle').first()
  if (await autour.count()) { await autour.scrollIntoViewIfNeeded(); await autour.click(); await page.waitForTimeout(2500) }
  const blocPermis = page.locator('[data-permis-proximite]').first()
  if (await blocPermis.count()) await blocPermis.scrollIntoViewIfNeeded()
  await page.waitForTimeout(800)
  report.S5_fiche_pc = await page.locator('text=97441816A0077').count()
  await shot('S5-fiche-BC0331')
  // clic sur le permis à 0 m → tiroir fiche permis (permit_id + provenance « parcelle d'origine »)
  await page.locator('[data-permis-proximite] button, [data-permis-proximite] [role="button"]').first().click().catch(() => {})
  await page.waitForTimeout(2500)
  report.S5_drawer_pc = await page.locator('text=97441816A0077').count()
  report.S5_drawer_origine = await page.locator("text=parcelle d'origine").count()
  await shot('S5-fiche-permis-drawer')
}

// ── S6 — toute couche s'affiche AU PREMIER clic, sur les 4 fonds (page rechargée à chaque fois) ──
if (run('S6')) {
  for (const [label, slug] of [['Sombre', 'sombre'], ['Clair', 'clair'], ['Plan IGN', 'plan'], ['Ortho IGN', 'ortho']]) {
    await page.goto(BASE + '?s6=' + slug, { waitUntil: 'networkidle' })
    await page.waitForTimeout(2000)
    if (label !== 'Sombre') await basemap(label)
    let ms = null
    const t0 = Date.now()
    const h = (r) => { if (r.url().includes('alea')) ms = Date.now() - t0 }
    page.on('response', h)
    await toggleLayer('alea_inondation')   // kind georisque_alea — LA couche lente (10,6 s à la volée)
    // avant : shot au 1er regard (~2,5 s) = couche muette ; après : shot au rendu (~6 s), obtenu
    // au PREMIER clic sans décocher/recocher (le reproche de Vic).
    await page.waitForTimeout(SUFFIX === 'avant' ? 700 : 4500)
    await shot(`S6-premier-clic-alea-${slug}`)
    await page.waitForTimeout(SUFFIX === 'avant' ? 12000 : 3000)
    page.off('response', h)
    report[`S6_${slug}_ms`] = ms
  }
}

// ── S7 — Transport public : lignes + arrêts dans UNE couche, arrêt cliquable ──
if (run('S7')) {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await drawer()
  await page.locator('[data-couches-drawer]').evaluate((el) => { el.scrollTop = el.scrollHeight * 0.55 })
  await page.waitForTimeout(300)
  report.S7_entree_arrets_separee = await page.locator('[data-layer="arrets"]').count()   // doit être 0 après
  report.S7_entree_lignes_mt = await page.locator('[data-layer="lignes_mt"]').count()      // doit être 0 après (S9)
  await shot('S7-couches-reseaux')
  await toggleLayer('transport')
  // viser un arrêt CONNU (Gare Routière 55.274771/-21.009909) : jumpTo puis clic au centre
  await page.evaluate(() => window.__labuse_map?.jumpTo({ center: [55.274771, -21.009909], zoom: 17 }))
  await page.waitForTimeout(3500)
  let popupOk = false
  const c = await page.locator('.maplibregl-canvas').first().boundingBox()
  for (const [dx, dy] of [[0, 0], [-6, 0], [6, 0], [0, -6], [0, 6], [-12, -6], [12, 6]]) {
    await page.mouse.click(c.x + c.width / 2 + dx, c.y + c.height / 2 + dy)
    await page.waitForTimeout(700)
    if (await page.locator('.maplibregl-popup').count()) { popupOk = true; break }
  }
  report.S7_popup_arret = popupOk
  await shot('S7-transport-arret')
}

// ── S8 — « Stationnement allégé » : zone 800 m dessinée + parcelles teintées, 4 fonds ──
if (run('S8')) {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await toggleLayer('tcsp')
  await page.click('[data-legend-toggle]').catch(() => {})
  await page.waitForTimeout(2500)
  // zoom Saint-Denis (le TCSP est au nord)
  await page.evaluate(() => window.__labuse_map?.jumpTo({ center: [55.455, -20.89], zoom: 13.5 }))
  await page.waitForTimeout(3000)
  await shot('S8-tcsp-sombre')
  for (const [label, slug] of [['Clair', 'clair'], ['Plan IGN', 'plan'], ['Ortho IGN', 'ortho']]) {
    await basemap(label)
    await page.waitForTimeout(2500)
    await shot(`S8-tcsp-${slug}`)
  }
  report.S8_libelle = await page.locator('[data-layer="tcsp"]').innerText().catch(() => '?')
}

// ── S9 — UNE couche « Lignes électriques (HTA / HTB) » ──
if (run('S9')) {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await toggleLayer('lignes_ht')
  await page.click('[data-legend-toggle]').catch(() => {})
  await page.waitForTimeout(3000)
  report.S9_libelle = await page.locator('[data-layer="lignes_ht"]').innerText().catch(() => '?')
  await shot('S9-lignes-electriques')
}

// ── S10 — procédure PLU : UN accordéon « Attention (2) » ──
if (run('S10')) {
  await outil('plu')
  await page.click('[data-plu-voie="procchg"]').catch(() => {})
  await page.waitForTimeout(1500)
  report.S10_accordeons = await page.locator('[data-procchg-attention]').count()
  await shot('S10-attention-ferme')
  await page.locator('[data-procchg-attention] summary').first().click().catch(() => {})
  await page.waitForTimeout(500)
  await shot('S10-attention-ouvert')
}

// ── S11 — fiche soleil : nature du toit DANS la grille, seuil de confiance ──
if (run('S11')) {
  await outil('prospection-solaire')
  await page.click('[data-solaire-mode="ensoleillement"]')
  await page.waitForTimeout(1200)
  await page.fill('[data-solaire-idu]', '97422000BD0800')
  await page.press('[data-solaire-idu]', 'Enter')
  await page.waitForTimeout(4000)
  const cand = page.locator('[data-parcelinput-candidat]')
  if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(4000) }
  report.S11_servie = await page.locator('text=simple pente').count()
  await shot('S11-fiche-toit-servi')
  await page.fill('[data-solaire-idu]', '97422000AZ0290')
  await page.press('[data-solaire-idu]', 'Enter')
  await page.waitForTimeout(4000)
  const cand2 = page.locator('[data-parcelinput-candidat]')
  if (await cand2.count()) { await cand2.first().click(); await page.waitForTimeout(4000) }
  report.S11_non_determinee = await page.locator('text=non déterminée (LiDAR)').count()
  await shot('S11-fiche-toit-non-determine')
}

console.log('REPORT', JSON.stringify(report, null, 1))
console.log('erreurs page:', JSON.stringify(errors.slice(0, 10)))
await browser.close()
