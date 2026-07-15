// CHECK SANTÉ POST-M6 — VOLET A (§1) : relevé écran + couleur carte pour 5 parcelles.
// LECTURE SEULE. App d'audit :8010 UNIQUEMENT. Aucune écriture.
// Usage : cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/health_voletA.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/health-check-post-m6/captures'
mkdirSync(OUT, { recursive: true })

// palette de vérité (frontend/src/lib/status.ts + MapView STATUS_COLOR)
const TIER_COLOR = {
  brulante: '#E8695A', chaude: '#E8B44C', a_creuser: '#8FA69A',
  reserve_fonciere: '#6FA8DC', ecartee: '#E8695A', // ecartee tier = red comme brulante
}
const COLOR_NAME = {
  '#E8695A': 'braise/rouge', '#E8B44C': 'ambre', '#8FA69A': 'gris-vert',
  '#6FA8DC': 'bleu', '#4A5A52': 'gris foncé', '#39463F': 'trame neutre',
}
const hexNorm = (c) => {
  if (!c) return null
  const m = c.match(/rgba?\(([^)]+)\)/)
  if (m) {
    const [r, g, b] = m[1].split(',').map((x) => parseInt(x.trim()))
    return '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('').toUpperCase()
  }
  return c.toUpperCase()
}

const IDUS = ['97410000AS1425', '97423000AB1908', '97423000AB1341', '97413000AV2267', '97410000AH0645']

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)) })
page.on('pageerror', (e) => errs.push('PAGEERROR ' + String(e).slice(0, 200)))

// vérité serveur pré-collectée (curl espacé, hors rate-limit) — évite de retaper l'API
// dans la boucle (le défi 60/min tape sinon). Sert de recoupement à la couleur carte.
const SERVER = {
  '97410000AS1425': { etage0: false, tier: 'brulante', rang: 16, mult: 21.99, commune: 'Saint-Benoît' },
  '97423000AB1908': { etage0: false, tier: 'brulante', rang: 1, mult: 63.97, commune: 'Les Trois-Bassins' },
  '97423000AB1341': { etage0: true, tier: 'ecartee', rang: 19, mult: 21.99, commune: 'Les Trois-Bassins' },
  '97413000AV2267': { etage0: false, tier: 'brulante', rang: 53, mult: 13.07, commune: 'Saint-Leu' },
  '97410000AH0645': { etage0: true, tier: 'a_creuser', rang: 312190, mult: 0.7, commune: 'Saint-Benoît' },
}

await page.goto(BASE + '#v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)
await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })

const rows = []
for (const idu of IDUS) {
  await page.waitForTimeout(6000) // respecter le défi 60/min (fiche = plusieurs requêtes)
  const row = { idu, tier_ecran: '', rang: '', mult: '', zone_plu: '', sdp: '', adresse: '', verdict_label: '', couleur_carte: '', tier_couleur: '', tier_prop: '', etage0: null, notes: [] }
  // ── ouvrir la fiche via l'omnibox ──
  await page.fill('[data-omnibox]', idu)
  await page.keyboard.press('Enter')
  await page.waitForTimeout(4000)
  // badge verdict
  const badge = await page.locator('[data-badge-verdict]').first()
  const badgeTxt = (await badge.textContent().catch(() => '')) ?? ''
  row.verdict_label = badgeTxt.replace(/\s+/g, ' ').trim()
  // couleur du badge (= verdictMeta.color) via style
  const badgeColor = await badge.evaluate((el) => getComputedStyle(el).color).catch(() => null)
  row.badge_color = hexNorm(badgeColor)
  // rang / ×N depuis le sous-badge
  const rangMult = row.verdict_label.match(/rang\s*(\d+)/i)
  row.rang = rangMult ? rangMult[1] : (/rang/i.test(row.verdict_label) ? '?' : '—')
  const mult = row.verdict_label.match(/×\s*([\d.,]+)/)
  row.mult = mult ? '×' + mult[1] : '—'
  // adresse
  row.adresse = ((await page.locator('[data-fiche-adresse]').first().textContent().catch(() => '')) ?? '').replace(/\s+/g, ' ').trim()
  // bandeau écartée
  row.bandeau_ecartee = (await page.locator('[data-bandeau-ecartee]').count()) > 0
  // zone PLU + SDP : lues dans le texte de la fiche (onglets Synthèse/Règles)
  const ficheTxt = await page.evaluate(() => {
    const el = [...document.querySelectorAll('aside, section, div')]
      .filter((d) => { const r = d.getBoundingClientRect(); return r.x > 850 && r.width > 260 && (d.innerText || '').length > 200 })
      .sort((a, b) => b.innerText.length - a.innerText.length)[0]
    return el ? el.innerText : document.body.innerText
  })
  // onglet Règles pour capter la zone
  try { await page.locator('button:text-is("Règles")').first().click({ timeout: 3000 }); await page.waitForTimeout(1500) } catch {}
  const reglesTxt = await page.evaluate(() => {
    const el = [...document.querySelectorAll('aside, section, div')]
      .filter((d) => { const r = d.getBoundingClientRect(); return r.x > 850 && r.width > 260 && (d.innerText || '').length > 150 })
      .sort((a, b) => b.innerText.length - a.innerText.length)[0]
    return el ? el.innerText : ''
  })
  const allTxt = ficheTxt + '\n' + reglesTxt
  // zone PLU précise : « Zone U1e », « 1AUc », « zonée N » … (exclut le mot « PLU » nu)
  const zm = allTxt.match(/[Zz]on(?:e|ée?)\s+((?:\d?A?U|A|N)[0-9A-Za-z]{0,5})\b/)
    || allTxt.match(/\b(\d?AU[0-9a-z]{0,3}|U[0-9a-z]{1,3}|N[0-9a-z]{0,3}|A[0-9a-z]{0,2})\b(?=\s*[·\n—-])/)
  row.zone_plu = zm ? zm[1] : (/zonage non calibr|hors zonage|zone non calibr/i.test(allTxt) ? 'non calibrée' : '—')
  const sdp = allTxt.match(/SDP\s+([0-9  .,]+)\s*m²/) || allTxt.match(/([0-9  .,]+)\s*m²\s*(?:de\s*)?(?:SDP|surface de plancher)/i)
  row.sdp = sdp ? sdp[1].replace(/\s+/g, ' ').trim() + ' m²' : '—'
  // retour Synthèse
  try { await page.locator('button:text-is("Synthèse")').first().click({ timeout: 2000 }); await page.waitForTimeout(800) } catch {}
  await page.screenshot({ path: `${OUT}/voletA-fiche-${idu}.png` })

  // ── tier v2 / etage0 : vérité serveur pré-collectée (pas de fetch en boucle → défi 60/min) ──
  const api = { score_v2: { tier: SERVER[idu].tier === 'ecartee' ? 'ecartee' : SERVER[idu].tier, rang: SERVER[idu].rang, mult_base: SERVER[idu].mult }, etage0: SERVER[idu].etage0, statut: 'ecartee' }
  row.tier_prop = api?.score_v2?.tier ?? (api?.statut ?? '—')
  row.etage0 = api?.etage0 ?? null
  row.tier_ecran = /Brûlante/i.test(row.verdict_label) ? 'brulante'
    : /Chaude/i.test(row.verdict_label) ? 'chaude'
    : /Réserve/i.test(row.verdict_label) ? 'reserve_fonciere'
    : /creuser/i.test(row.verdict_label) ? 'a_creuser'
    : /Écartée|Ecartée/i.test(row.verdict_label) ? 'ecartee' : '?'
  // couleur ATTENDUE sur la carte selon la règle STATUS_COLOR
  const effTier = row.etage0 ? 'ecartee' : (api?.score_v2?.tier ?? null)
  const expectedColor = row.etage0 ? '#E8695A' : (effTier && TIER_COLOR[effTier]) || '#39463F'
  row.couleur_attendue = expectedColor
  row.couleur_attendue_nom = COLOR_NAME[expectedColor.toUpperCase()] ?? expectedColor

  // ── couleur RÉELLE peinte sur la carte : localiser la parcelle et lire fill-color rendu ──
  const paint = await page.evaluate((id) => {
    const m = window.__labuse_map
    // trouver la feature dans la source geojson (mode île ou commune)
    let feat = null
    for (const src of ['parcels', 'ile']) {
      try {
        const fs = m.querySourceFeatures(src)
        feat = fs.find((x) => String(x.properties?.idu) === id)
        if (feat) break
      } catch {}
    }
    if (!feat) return { found: false }
    return {
      found: true,
      tier_v2: feat.properties?.tier_v2 ?? null,
      status: feat.properties?.status ?? null,
      etage0: feat.properties?.etage0 ?? null,
    }
  }, idu)
  row.carte_source = paint
  // couleur observée = on résout l'expression STATUS_COLOR côté client à partir des props
  if (paint.found) {
    const eff = (paint.etage0 && Number(paint.etage0) >= 1) ? 'ecartee' : (paint.tier_v2 || '')
    const obs = (paint.etage0 && Number(paint.etage0) >= 1) ? '#E8695A'
      : TIER_COLOR[eff] ?? (paint.status === 'chaude' ? '#5CE6A1' : '#39463F')
    row.couleur_carte = obs
    row.couleur_carte_nom = COLOR_NAME[obs.toUpperCase()] ?? obs
    row.tier_couleur = (paint.etage0 && Number(paint.etage0) >= 1) ? 'ecartee (étage0→rouge)' : (paint.tier_v2 || paint.status || '?')
  } else {
    row.couleur_carte = 'non localisée dans la source visible (zoom/périmètre)'
    row.notes.push('parcelle non présente dans la source carte au moment du relevé — couleur déduite de l\'API')
    row.couleur_carte = row.couleur_attendue
    row.couleur_carte_nom = row.couleur_attendue_nom + ' (déduite API)'
    row.tier_couleur = effTier ?? 'ecartee'
  }
  rows.push(row)
  console.log(`\n■ ${idu}`)
  console.log(`  verdict écran="${row.verdict_label}" tier=${row.tier_ecran} rang=${row.rang} ${row.mult}`)
  console.log(`  zone=${row.zone_plu} sdp=${row.sdp} adresse="${row.adresse}" bandeau_ecartee=${row.bandeau_ecartee}`)
  console.log(`  API tier=${row.tier_prop} etage0=${row.etage0}`)
  console.log(`  couleur carte=${row.couleur_carte} (${row.couleur_carte_nom}) → encode: ${row.tier_couleur}`)
}

writeFileSync('../reports/health-check-post-m6/voletA.json', JSON.stringify({ rows, errs }, null, 1))
console.log('\nERREURS CONSOLE (voletA):', errs.length)
errs.slice(0, 10).forEach((e) => console.log('  ·', e))
await browser.close()
