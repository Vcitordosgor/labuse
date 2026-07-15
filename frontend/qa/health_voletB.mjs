// CHECK SANTÉ POST-M6 — VOLET B (§3) : parcours utilisateur a-f. LECTURE SEULE, :8010.
// Usage : cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/health_voletB.mjs
import { mkdirSync, writeFileSync, existsSync, statSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/health-check-post-m6/captures'
const DL = '../reports/health-check-post-m6/downloads'
mkdirSync(OUT, { recursive: true }); mkdirSync(DL, { recursive: true })

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, acceptDownloads: true })
const page = await ctx.newPage()
const errs = [], netErr = []
const hook = (p) => {
  p.on('console', (m) => { if (m.type() === 'error') { const t = m.text(); if (!/glyph|CORS|font/i.test(t)) errs.push(t.slice(0, 200)) } })
  p.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)))
  p.on('response', (r) => { const u = r.url().replace(/^https?:\/\/[^/]+/, ''); if (r.status() >= 400 && !u.startsWith('/socle') && !u.includes('.pbf')) netErr.push(`${r.status()} ${u.slice(0, 120)}`) })
}
hook(page)
const rep = { a_nl: {}, a_pdf: {}, b_popup: {}, c_couches: [], d_filtres: [], e_export: {}, f_vue: {} }
const pause = (ms = 4000) => page.waitForTimeout(ms)

// ══════════ B(a) — recherche NL « brûlantes de Saint-Paul » + P v2 + PDF ══════════
console.log('\n════ B(a) NL « brûlantes de Saint-Paul » ════')
await page.goto(BASE + '#v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(3000)
await page.fill('[data-omnibox]', 'brûlantes de Saint-Paul')
await page.keyboard.press('Enter')
await pause(3500)
const toastNL = (await page.locator('[data-toast]').textContent().catch(() => '')) ?? ''
const communeApres = await page.evaluate(() => window.__labuse?.commune ?? window.__labuse?.getState?.()?.commune ?? null)
rep.a_nl.toast = toastNL.replace(/\s+/g, ' ').trim()
rep.a_nl.commune_apres_recherche = communeApres
await page.screenshot({ path: `${OUT}/B-a-nl-recherche.png` })
console.log('  toast NL:', rep.a_nl.toast || '(aucun)', '| commune=', communeApres)

// chemin PRODUIT équivalent : périmètre Saint-Paul + chip Brûlantes v2
await page.goto(BASE + '#v=1&c=' + encodeURIComponent('Saint-Paul'), { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(5000)
await page.locator('button', { hasText: 'Brûlantes v2' }).first().click()
await pause(5000) // laisser la liste se re-filtrer (évite un état vide transitoire)
const nCards = await page.locator('[data-results-scroll] button').count()
const chipTxt = (await page.locator('button', { hasText: 'Brûlantes v2' }).first().textContent().catch(() => '')) ?? ''
rep.a_nl.saint_paul_brulantes_cartes = nCards
rep.a_nl.chip_brulantes = chipTxt.replace(/\s+/g, ' ').trim()
// vérifier que toutes sont Saint-Paul + brûlante v2
const firstCards = []
for (let i = 0; i < Math.min(3, nCards); i++) firstCards.push((await page.locator('[data-results-scroll] button').nth(i).textContent()).replace(/\s+/g, ' ').trim().slice(0, 80))
rep.a_nl.premieres_cartes = firstCards
await page.screenshot({ path: `${OUT}/B-a-saintpaul-brulantes.png` })
console.log(`  Saint-Paul + Brûlantes v2 → ${nCards} cartes | chip="${rep.a_nl.chip_brulantes}"`)
firstCards.forEach((c) => console.log('   ·', c))

// clic 1re fiche → bloc P v2 présent ? (ignorer un éventuel bouton d'état vide)
const firstReal = page.locator('[data-results-scroll] button').filter({ hasText: 'Brûlante v2' }).first()
await firstReal.click({ timeout: 8000 }).catch(async () => { await page.locator('[data-results-scroll] button').first().click() })
await page.waitForSelector('[data-badge-verdict]', { timeout: 20000 }).catch(() => {})
await pause(3500)
const verdictFiche = ((await page.locator('[data-badge-verdict]').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').trim()
const pv2Count = await page.locator('[data-score-v2]').count()
const pv2Txt = pv2Count ? ((await page.locator('[data-score-v2]').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').trim() : ''
rep.a_pdf.verdict_fiche = verdictFiche
rep.a_pdf.p_v2_affiche = pv2Count > 0
rep.a_pdf.p_v2_extrait = pv2Txt.slice(0, 160)
await page.screenshot({ path: `${OUT}/B-a-fiche-pv2.png` })
console.log(`  fiche verdict="${verdictFiche}" | P v2 affiché=${pv2Count > 0} | "${pv2Txt.slice(0, 100)}"`)

// PDF : le bouton PDF est un <a href target=_blank> → capter le download / la nav
const pdfHref = await page.locator('a:has-text("PDF")').first().getAttribute('href').catch(() => null)
rep.a_pdf.pdf_href = pdfHref
let pdfStatus = null, pdfBytes = null, pdfCT = null
if (pdfHref) {
  const abs = pdfHref.startsWith('http') ? pdfHref : (new URL(pdfHref, page.url())).toString()
  const resp = await page.request.get(abs).catch((e) => ({ err: String(e) }))
  if (resp && resp.status) {
    pdfStatus = resp.status()
    pdfCT = resp.headers()['content-type']
    const body = await resp.body().catch(() => null)
    pdfBytes = body ? body.length : null
    if (body && body.length > 100) { writeFileSync(`${DL}/fiche.pdf`, body) }
  }
}
rep.a_pdf.pdf_status = pdfStatus; rep.a_pdf.pdf_content_type = pdfCT; rep.a_pdf.pdf_bytes = pdfBytes
console.log(`  PDF: href=${pdfHref} status=${pdfStatus} ct=${pdfCT} bytes=${pdfBytes}`)

// ══════════ B(b) — popup carte vs tier fiche ══════════
console.log('\n════ B(b) popup carte vs fiche ════')
// on prend AB1908 (brûlante rang 1, Trois-Bassins) : cliquer sur la carte doit ouvrir SA fiche
await page.goto(BASE + '#v=1&c=' + encodeURIComponent('Les Trois-Bassins'), { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(4000)
await page.waitForFunction(() => { try { return window.__labuse_map.querySourceFeatures('parcels').some((x) => String(x.properties?.idu) === '97423000AB1908') } catch { return false } }, null, { timeout: 60000 }).catch(() => {})
const cible = await page.evaluate(() => {
  const m = window.__labuse_map
  const f = m.querySourceFeatures('parcels').find((x) => String(x.properties?.idu) === '97423000AB1908')
  if (!f) return null
  const g = f.geometry, c = g.type === 'Polygon' ? g.coordinates[0][0] : g.coordinates[0][0][0]
  return { lng: c[0], lat: c[1], tier_v2: f.properties?.tier_v2, etage0: f.properties?.etage0 }
})
if (cible) {
  await page.evaluate((c) => window.__labuse_map.jumpTo({ center: [c.lng, c.lat], zoom: 18 }), cible)
  await pause(2500)
  const px = await page.evaluate((c) => { const p = window.__labuse_map.project([c.lng, c.lat]); return { x: p.x, y: p.y } }, cible)
  const canvas = await page.locator('.maplibregl-canvas').boundingBox()
  await page.mouse.click(canvas.x + px.x, canvas.y + px.y)
  await pause(3000)
  const badge2 = ((await page.locator('[data-badge-verdict]').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').trim()
  rep.b_popup.clic_carte_ouvre_fiche = /Brûlante|Chaude|Écartée|creuser|Réserve/.test(badge2)
  rep.b_popup.verdict_fiche_apres_clic = badge2
  rep.b_popup.carte_tier_v2 = cible.tier_v2
  rep.b_popup.coherent = (cible.tier_v2 === 'brulante') && /Brûlante/.test(badge2)
  await page.screenshot({ path: `${OUT}/B-b-clic-carte-fiche.png` })
  console.log(`  carte tier_v2=${cible.tier_v2} → fiche verdict="${badge2}" | cohérent=${rep.b_popup.coherent}`)
} else { rep.b_popup.err = 'AB1908 non localisée'; console.log('  AB1908 non localisée') }

// ══════════ B(c) — chaque couche une à une ══════════
console.log('\n════ B(c) couches une à une (île) ════')
const COUCHES = ['Zonage PLU', 'Zonage PLU (parcelles)', 'Parcelles', 'PPR multirisque', 'Vue mer', 'Parc national', 'Limites parcelles', 'Limites communes', 'ANRU (NPNRU)', '50 pas géométriques', 'Équipements']
await page.goto(BASE + '#v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(3500)
for (const label of COUCHES) {
  const before = netErr.length, beforeErr = errs.length
  const netSeen = []
  const listener = (r) => { const u = r.url().replace(/^https?:\/\/[^/]+/, ''); if (/layers|parc|tiles|ppr|anru|equip|geojson/.test(u.toLowerCase())) netSeen.push(r.status()) }
  page.on('response', listener)
  try {
    await page.locator(`aside button:has-text("${label}")`).first().click({ timeout: 5000 })
  } catch (e) {
    rep.c_couches.push({ couche: label, err: 'bouton introuvable: ' + e.message.slice(0, 60) }); page.off('response', listener); continue
  }
  await pause(3500)
  // toast état-vide légitime ?
  const toast = (await page.locator('[data-toast]').textContent().catch(() => '')) ?? ''
  // rendu visible : au moins une feature rendue OU un toast honnête
  const rendu = await page.evaluate(() => {
    const m = window.__labuse_map
    const ids = m.getStyle().layers.map((l) => l.id)
    let n = 0
    for (const id of ids) { try { if (m.getLayoutProperty(id, 'visibility') !== 'none') n += m.queryRenderedFeatures(undefined, { layers: [id] }).length } catch {} }
    return n
  })
  page.off('response', listener)
  await page.screenshot({ path: `${OUT}/B-c-couche-${label.normalize('NFD').replace(/[^a-zA-Z0-9]/g, '_')}.png` })
  const row = {
    couche: label,
    reseau_status: [...new Set(netSeen)].join(',') || '—',
    reseau_erreur: netErr.length > before,
    rendu_features: rendu,
    toast: toast.replace(/\s+/g, ' ').trim().slice(0, 90) || '',
    console_err: errs.length > beforeErr,
  }
  rep.c_couches.push(row)
  console.log(`  ${label}: net=${row.reseau_status} rendu=${rendu} feats toast="${row.toast}" errNew=${row.console_err}`)
  // re-toggle OFF pour isoler la suivante
  try { await page.locator(`aside button:has-text("${label}")`).first().click({ timeout: 4000 }); await pause(1500) } catch {}
}

// ══════════ B(d) — filtres empilés, compteurs ══════════
console.log('\n════ B(d) filtres empilés ════')
await page.goto(BASE + '#v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(3500)
const compteur = async () => {
  const body = await page.textContent('body')
  const opp = body.match(/([\d   ]+)\s*opportunités/)
  const cards = await page.locator('[data-results-scroll] button').count()
  return { opportunites: opp ? opp[1].replace(/\s+/g, ' ').trim() : '?', cartes_affichees: cards }
}
rep.d_filtres.push({ etape: 'initial (île)', ...(await compteur()) })
// tier = brûlante seul
await page.locator('button', { hasText: 'Brûlantes v2' }).first().click()
await pause(3000)
rep.d_filtres.push({ etape: 'tier=Brûlantes v2', ...(await compteur()), chip: ((await page.locator('button', { hasText: 'Brûlantes v2' }).first().textContent()) ?? '').replace(/\s+/g, ' ').trim() })
// + commune Saint-Paul (nav directe pour éviter le reset omnibox, puis re-appliquer la chip)
await page.goto(BASE + '#v=1&c=' + encodeURIComponent('Saint-Paul'), { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(5000)
await page.locator('button', { hasText: 'Brûlantes v2' }).first().click(); await pause(5000)
rep.d_filtres.push({ etape: '+ commune=Saint-Paul (tier brûlante)', ...(await compteur()), chip: ((await page.locator('button', { hasText: 'Brûlantes v2' }).first().textContent()) ?? '').replace(/\s+/g, ' ').trim() })
// + masquer copropriétés
const toggle = page.locator('[data-toggle-copro]')
if (await toggle.count()) { await toggle.check(); await page.waitForFunction(() => document.querySelectorAll('[data-results-scroll] button').length >= 0, null, { timeout: 12000 }).catch(() => {}); await pause(2500) }
rep.d_filtres.push({ etape: '+ masquer copropriétés', ...(await compteur()) })
await page.screenshot({ path: `${OUT}/B-d-filtres-empiles.png` })
rep.d_filtres.forEach((r) => console.log(`  ${r.etape}: opp=${r.opportunites} cartes=${r.cartes_affichees}${r.chip ? ' chip=' + r.chip : ''}`))

// ══════════ B(e) — export CSV liste ══════════
console.log('\n════ B(e) export CSV ════')
await page.goto(BASE + '#v=1&c=' + encodeURIComponent('Saint-Paul'), { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
await pause(3500)
// export de la liste = lien « ⬇ CSV » (<a href download>) dans le pied du panneau résultats
const expBtn = page.locator('a[href*="export.csv"], a:has-text("CSV")').first()
let csvInfo = { trouve: false }
// href direct pour un check HTTP fiable (le <a download> peut ne pas déclencher d'event en headless)
const csvHref = await expBtn.getAttribute('href').catch(() => null)
csvInfo.href = csvHref
if (csvHref) {
  const abs = csvHref.startsWith('http') ? csvHref : (new URL(csvHref, page.url())).toString()
  const resp = await page.request.get(abs).catch((e) => ({ err: String(e) }))
  if (resp && resp.status) {
    const body = await resp.text().catch(() => '')
    const lignes = body.split(/\r?\n/).filter(Boolean).length
    const { writeFileSync: wf } = await import('node:fs')
    wf(`${DL}/liste-saintpaul-http.csv`, body)
    csvInfo.http = { status: resp.status(), content_type: resp.headers()['content-type'], octets: body.length, lignes, entete: body.split(/\r?\n/)[0].slice(0, 220), accents_ok: !/Ã©|Ã¨|Ã /.test(body), echantillon: body.split(/\r?\n/).slice(1, 3).map((l) => l.slice(0, 120)) }
  }
}
if (await expBtn.count()) {
  csvInfo.trouve = true
  try {
    const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 8000 }), expBtn.click()])
    const p = `${DL}/liste-saintpaul.csv`; await dl.saveAs(p)
    const bytes = statSync(p).size
    const { readFileSync } = await import('node:fs')
    const txt = readFileSync(p, 'utf8')
    const lignes = txt.split(/\r?\n/).filter(Boolean).length
    csvInfo = { trouve: true, fichier: dl.suggestedFilename(), octets: bytes, lignes, entete: txt.split(/\r?\n/)[0].slice(0, 200), accents_ok: /[éèàûîô]/.test(txt) || !/Ã©|Ã¨/.test(txt), echantillon: txt.split(/\r?\n/).slice(1, 3).map((l) => l.slice(0, 120)) }
  } catch (e) { csvInfo.err = e.message.slice(0, 120) }
}
rep.e_export.liste = csvInfo
console.log('  export liste:', JSON.stringify(csvInfo).slice(0, 300))

// ══════════ B(f) — vue métier piscinistes ══════════
console.log('\n════ B(f) vue métier piscinistes ════')
await page.goto(BASE + '#v=1', { waitUntil: 'networkidle', timeout: 60000 })
await pause(2500)
// aller sur l'onglet Vues (Rail)
await page.locator('button:has-text("Vues")').first().click().catch(() => {})
await pause(3500)
await page.screenshot({ path: `${OUT}/B-f-vues-home.png` })
// chercher un preset piscine
const presets = await page.evaluate(() => [...document.querySelectorAll('[data-seg-preset]')].map((el) => el.getAttribute('data-seg-preset')))
rep.f_vue.presets_disponibles = presets
const slugPisc = presets.find((s) => /piscin/i.test(s))
console.log('  presets:', presets.join(', '))
if (slugPisc) {
  await page.locator(`[data-seg-preset="${slugPisc}"] [data-seg-preset-open]`).click()
  await pause(4500)
  // onglet Résultats
  const count = (await page.locator('[data-seg-count]').first().textContent().catch(() => '')) ?? ''
  rep.f_vue.slug = slugPisc
  rep.f_vue.compte_servi = count.replace(/\s+/g, ' ').trim()
  await page.screenshot({ path: `${OUT}/B-f-vue-piscinistes.png` })
  console.log(`  vue ${slugPisc} → compte servi=${rep.f_vue.compte_servi}`)
  // export CSV de la vue métier (data-seg-export)
  const segExp = page.locator('[data-seg-export]').first()
  if (await segExp.count() && !(await segExp.isDisabled())) {
    try {
      const [dl] = await Promise.all([page.waitForEvent('download', { timeout: 15000 }), segExp.click()])
      const p = `${DL}/vue-${slugPisc}.csv`; await dl.saveAs(p)
      const { readFileSync } = await import('node:fs')
      const txt = readFileSync(p, 'utf8'); const lignes = txt.split(/\r?\n/).filter(Boolean).length
      rep.e_export.vue_metier = { fichier: dl.suggestedFilename(), octets: statSync(p).size, lignes, entete: txt.split(/\r?\n/)[0].slice(0, 200), accents_ok: !/Ã©|Ã¨/.test(txt) }
      console.log('  export vue:', JSON.stringify(rep.e_export.vue_metier).slice(0, 250))
    } catch (e) { rep.e_export.vue_metier = { err: e.message.slice(0, 120) } }
  }
} else { rep.f_vue.err = 'aucun preset piscine trouvé' }

rep.erreurs_console = errs
rep.erreurs_reseau = netErr
writeFileSync('../reports/health-check-post-m6/voletB.json', JSON.stringify(rep, null, 1))
console.log('\n════ ERREURS CONSOLE (hors glyphs/CORS):', errs.length)
errs.slice(0, 12).forEach((e) => console.log('  ·', e))
console.log('════ ERREURS RÉSEAU >=400:', netErr.length)
netErr.slice(0, 12).forEach((e) => console.log('  ·', e))
await browser.close()
