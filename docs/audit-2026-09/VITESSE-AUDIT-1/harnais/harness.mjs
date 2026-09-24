// VITESSE-AUDIT-1 — harnais de mesure REJOUABLE (hors src/, ne touche pas l'app).
//
// Deux étages :
//   1) SWEEP endpoints (fetch direct) — tuiles des 56 couches (île z9 + rue z14) + endpoints
//      outils/fiche. Donne le temps CLIENT + le poids ; le temps SERVEUR (Python|SQL) vient du
//      CSV de la sonde (docs/.../MESURES/sonde/sonde_requests.csv), corrélé par chemin.
//   2) PARCOURS navigateur (Playwright, build de prod servi par FastAPI /socle) — TTFB/FCP/LCP,
//      long tasks, waterfall (HAR), pour les écrans page (boot, carte, fiche, un outil).
//
// Chaque cible est jouée 1× FROID puis N× CHAUD ; on garde la médiane. Sorties CSV+HAR dans OUT.
//
// Lancement (venv/app déjà démarrés sur 8305, cf. sonde_app.py) :
//   node docs/audit-2026-09/VITESSE-AUDIT-1/harnais/harness.mjs
// Variables : BASE (def http://127.0.0.1:8305), SOURCE (def q_v11_m137), OUT (def MESURES/),
//   WARM (def 2), WITNESS (def 97410000AN0347), PM_SIREN (def 452038805 = CBO Territoria),
//   SKIP_PW=1 pour sauter le volet navigateur.
import { mkdirSync, writeFileSync, appendFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import { tile, REUNION_ILE, STDENIS_RUE } from './lonlat_to_tile.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
// playwright vit dans frontend/node_modules (4 niveaux au-dessus de harnais/). createRequire
// résout depuis là → aucun chemin machine en dur, rejouable tel quel.
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const BASE = process.env.BASE ?? 'http://127.0.0.1:8305'
const SOURCE = process.env.SOURCE ?? 'q_v11_m137'
const OUT = process.env.OUT ?? join(HERE, '..', 'MESURES')
const WARM = Number(process.env.WARM ?? 2)
const WITNESS = process.env.WITNESS ?? '97410000AN0347'
const PM_SIREN = process.env.PM_SIREN ?? '452038805'
mkdirSync(OUT, { recursive: true })

const EP_CSV = join(OUT, 'sweep_endpoints.csv')
const PARC_CSV = join(OUT, 'parcours_browser.csv')
// N'écrase JAMAIS un CSV existant (rejouabilité : un SKIP_SWEEP ne doit pas effacer le sweep précédent).
if (!existsSync(EP_CSV)) writeFileSync(EP_CSV, 'group,label,url,phase,run,status,client_ms,bytes,enc\n')
if (!existsSync(PARC_CSV)) writeFileSync(PARC_CSV, 'parcours,phase,run,ttfb_ms,fcp_ms,lcp_ms,dom_ms,load_ms,longtasks_n,longtasks_ms,req_n,req_bytes\n')

const median = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0 }

async function timedFetch(url) {
  const t0 = performance.now()
  try {
    const r = await fetch(url, { headers: { 'Accept-Encoding': 'gzip, br' } })
    const buf = Buffer.from(await r.arrayBuffer())
    return { ms: performance.now() - t0, status: r.status, bytes: buf.length, enc: r.headers.get('content-encoding') || '' }
  } catch (e) {
    return { ms: performance.now() - t0, status: 0, bytes: 0, enc: `ERR:${e.code || e.message}` }
  }
}

// 1× froid + WARM× chaud, écrit chaque run, renvoie la médiane des chauds (ou du froid si WARM=0)
async function sweep(group, label, url) {
  const warm = []
  for (let i = 0; i <= WARM; i++) {
    const phase = i === 0 ? 'cold' : 'warm'
    const r = await timedFetch(url)
    appendFileSync(EP_CSV, `${group},${label},${url},${phase},${i},${r.status},${r.ms.toFixed(1)},${r.bytes},${r.enc}\n`)
    if (i > 0) warm.push(r.ms)
    if (r.status === 0) break
  }
  return median(warm)
}

async function sweepEndpoints() {
  // — liste des couches servies (dynamique, rejouable) —
  let kinds = []
  try {
    const r = await fetch(`${BASE}/map/tuyau/couches`)
    const j = await r.json()
    const arr = Array.isArray(j) ? j : (j.couches || j.layers || Object.values(j).find(Array.isArray) || [])
    kinds = arr.map((c) => c.kind || c.id || c.name).filter(Boolean)
  } catch { /* keep empty */ }
  console.log(`couches servies découvertes: ${kinds.length}`)

  const ile = tile(REUNION_ILE.lon, REUNION_ILE.lat, 9)
  const rue = tile(STDENIS_RUE.lon, STDENIS_RUE.lat, 14)
  const mid = tile(REUNION_ILE.lon, REUNION_ILE.lat, 11)

  // parcelles (couche reine) aux 3 zooms
  await sweep('tuile_parcelles', 'parcelles@z9_ile', `${BASE}/map/tiles/${ile.z}/${ile.x}/${ile.y}.pbf?source=${SOURCE}`)
  await sweep('tuile_parcelles', 'parcelles@z11', `${BASE}/map/tiles/${mid.z}/${mid.x}/${mid.y}.pbf?source=${SOURCE}`)
  await sweep('tuile_parcelles', 'parcelles@z14_rue', `${BASE}/map/tiles/${rue.z}/${rue.x}/${rue.y}.pbf?source=${SOURCE}`)

  // chaque couche : île z9 + rue z14
  for (const k of kinds) {
    await sweep('tuile_couche_ile', `${k}@z9`, `${BASE}/map/tiles/${k}/${ile.z}/${ile.x}/${ile.y}.pbf`)
    await sweep('tuile_couche_rue', `${k}@z14`, `${BASE}/map/tiles/${k}/${rue.z}/${rue.x}/${rue.y}.pbf`)
  }
  // ortho (fond de plan)
  await sweep('tuile_ortho', 'ortho_express@z14', `${BASE}/map/tiles/ortho/express/${rue.z}/${rue.x}/${rue.y}`)

  // — endpoints fiche (témoin) —
  const f = WITNESS
  const ficheEps = [
    ['fiche', 'parcels', `/parcels/${f}?source=${SOURCE}`],
    ['fiche', 'exposition', `/parcels/${f}/exposition`],
    ['fiche', 'faisabilite', `/modules/faisabilite/${f}`],
    ['fiche', 'mon-secteur', `/outils/mon-secteur?idu=${f}`],
    ['fiche', 'zone-pied', `/parcels/${f}/zone?mode=pied&minutes=15`],
    ['fiche', 'v2-score', `/v2/score/${f}`],
    ['fiche', 'anti-fiche', `/anti-fiche/${f}`],
    ['fiche', 'permis-parcel', `/modules/permis/parcel/${f}`],
    ['fiche', 'gabarit', `/outils/gabarit/${f}`],
    ['fiche', 'watch', `/events/watch/${f}`],
    ['fiche', 'pipeline-parcel', `/pipeline/parcel/${f}`],
    ['fiche', 'projets-parcelle', `/projets-parcelle/${f}`],
  ]
  for (const [g, l, p] of ficheEps) await sweep(g, l, `${BASE}${p}`)

  // — endpoints outils (résultat sur témoin) —
  const outilsEps = [
    ['outil', 'patrimoine-CBO', `/modules/patrimoine?siren=${PM_SIREN}&limit=200&offset=0`],
    ['outil', 'communes-liste', `/communes`],
    ['outil', 'comparateur-communes', `/comparateur-communes`],
    ['outil', 'permis-carte', `/modules/permis?months=240&limit=300`],
    ['outil', 'permis-count', `/modules/permis?months=240&count_only=true`],
    ['outil', 'blocs', `/modules/blocs?limit=50`],
    ['outil', 'successions', `/modules/successions?limit=50`],
    ['outil', 'plu-annuaire-communes', `/modules/plu-annuaire/communes`],
    ['outil', 'assemblage-voisines', `/moteurs/assemblage/voisines?idu=${f}`],
    ['outil', 'renouvellement-liste', `/outils/renouvellement/liste?commune=Saint-Denis&limit=50`],
    ['outil', 'solaire', `/modules/prospection-solaire?commune=Saint-Denis`],
    ['outil', 'piscines-points', `/modules/prospection-piscines/points?commune=Saint-Denis`],
    ['outil', 'gabarit-outil', `/outils/gabarit/${f}`],
  ]
  for (const [g, l, p] of outilsEps) await sweep(g, l, `${BASE}${p}`)

  // — filtre / analyse (compteur vivier) —
  await sweep('filtre', 'compteur-ile', `${BASE}/filtre/compteur?source=${SOURCE}`)
  await sweep('filtre', 'parcels-list-200', `${BASE}/parcels?source=${SOURCE}&limit=200&offset=0`)

  // — omnibox —
  await sweep('omnibox', 'adresse-autocomplete', `${BASE}/adresses/autocomplete?q=8+rue+de+la+source`)
}

// ————————————— Volet navigateur —————————————
const VITALS = `(() => new Promise((res) => {
  const out = { fcp: 0, lcp: 0, lt_n: 0, lt_ms: 0 }
  try {
    const nav = performance.getEntriesByType('navigation')[0]
    out.ttfb = nav ? nav.responseStart : 0
    out.dom = nav ? nav.domContentLoadedEventEnd : 0
    out.load = nav ? nav.loadEventEnd : 0
    const fcp = performance.getEntriesByName('first-contentful-paint')[0]
    out.fcp = fcp ? fcp.startTime : 0
  } catch {}
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) out.lcp = e.startTime }).observe({ type: 'largest-contentful-paint', buffered: true })
    new PerformanceObserver((l) => { for (const e of l.getEntries()) { out.lt_n++; out.lt_ms += e.duration } }).observe({ type: 'longtask', buffered: true })
  } catch {}
  setTimeout(() => res(out), 1200)
}))()`

async function runParcours(browser, name, phase, run, fn, harPath) {
  const context = await browser.newContext(
    phase === 'cold'
      ? (harPath ? { recordHar: { path: harPath, content: 'embed' } } : {})
      : {},
  )
  const page = await context.newPage()
  let reqN = 0, reqBytes = 0
  page.on('response', async (r) => { reqN++; try { const b = await r.body(); reqBytes += b.length } catch {} })
  await fn(page)
  let v = {}
  try { v = await page.evaluate(VITALS) } catch {}
  appendFileSync(PARC_CSV,
    `${name},${phase},${run},${(v.ttfb || 0).toFixed(0)},${(v.fcp || 0).toFixed(0)},${(v.lcp || 0).toFixed(0)},${(v.dom || 0).toFixed(0)},${(v.load || 0).toFixed(0)},${v.lt_n || 0},${(v.lt_ms || 0).toFixed(0)},${reqN},${reqBytes}\n`)
  await context.close()
}

async function browserParcours() {
  // La version playwright installée peut attendre un build de chromium différent de celui présent.
  // CHROME_BIN permet de pointer le binaire réellement installé (ex. chromium_headless_shell-1217).
  const launchOpts = { headless: true }
  if (process.env.CHROME_BIN) launchOpts.executablePath = process.env.CHROME_BIN
  const browser = await chromium.launch(launchOpts)
  const harDir = join(OUT, 'har'); mkdirSync(harDir, { recursive: true })

  const parcours = [
    ['1_boot_accueil', async (p) => {
      await p.goto(`${BASE}/socle/`, { waitUntil: 'load', timeout: 60000 })
      await p.waitForTimeout(2500) // laisser la carte se peindre
    }],
    ['6_fiche_temoin', async (p) => {
      await p.goto(`${BASE}/socle/#/parcelle/${WITNESS}`, { waitUntil: 'load', timeout: 60000 }).catch(() => {})
      // repli : ouvrir via l'omnibox si le deep-link ne monte pas la fiche
      await p.waitForTimeout(3500)
    }],
  ]

  for (const [name, fn] of parcours) {
    for (let i = 0; i <= WARM; i++) {
      const phase = i === 0 ? 'cold' : 'warm'
      const har = i === 0 ? join(harDir, `${name}.har`) : null
      try { await runParcours(browser, name, phase, i, fn, har) }
      catch (e) { appendFileSync(PARC_CSV, `${name},${phase},${i},ERR,${e.message?.slice(0, 40)},,,,,,,\n`) }
    }
  }
  await browser.close()
}

// ————————————— main —————————————
console.log(`BASE=${BASE} SOURCE=${SOURCE} WARM=${WARM} OUT=${OUT}`)
if (!process.env.SKIP_SWEEP) { await sweepEndpoints(); console.log('sweep endpoints OK →', EP_CSV) }
if (!process.env.SKIP_PW) { await browserParcours(); console.log('parcours navigateur OK →', PARC_CSV) }
console.log('FINI. Corréler le temps serveur via MESURES/sonde/sonde_requests.csv (par chemin).')
