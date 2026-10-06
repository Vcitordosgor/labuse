// CARTE-VITESSE-1 — chronologie fine du chargement de la carte (LECTURE SEULE).
// Ouvre /socle/, capture chaque réponse (t début relatif, durée, taille, encodage, famille),
// mesure le temps jusqu'à « carte complète » = dernier tuile parcelle peinte + réseau calme.
// 1 passe CACHE VIDE (contexte neuf) + 1 passe CACHE CHAUD (même contexte réutilisé).
// Sorties : MESURES/boot_requests.csv (une ligne/réponse) + MESURES/boot_resume.csv (synthèse) + HAR.
//
// node docs/audit-2026-09/CARTE-VITESSE-1/harnais/boot_waterfall.mjs
import { mkdirSync, writeFileSync, appendFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const HERE = dirname(fileURLToPath(import.meta.url))
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const BASE = process.env.BASE ?? 'http://127.0.0.1:8475'
const OUT = process.env.OUT ?? join(HERE, '..', 'MESURES')
const CHROME_BIN = process.env.CHROME_BIN
mkdirSync(OUT, { recursive: true })
const harDir = join(OUT, 'har'); mkdirSync(harDir, { recursive: true })

const REQ_CSV = join(OUT, 'boot_requests.csv')
const RESUME_CSV = join(OUT, 'boot_resume.csv')
writeFileSync(REQ_CSV, 'passe,famille,method,status,from_cache,t_start_ms,dur_ms,bytes,enc,url\n')
writeFileSync(RESUME_CSV, 'passe,fcp_ms,dom_ms,load_ms,ready_ms,derniere_tuile_parcelle_ms,idle_ms,n_req,n_tuiles_parcelles,octets_total,octets_tuiles_parcelles,lt_n,lt_ms\n')

function famille(url) {
  if (/\/map\/tiles\/\d+\/\d+\/\d+\.pbf/.test(url)) return 'tuile_parcelle'
  if (/\/map\/tiles\/[a-z_]+\/\d+\/\d+\/\d+\.pbf/.test(url)) return 'tuile_couche'
  if (/\/map\/tiles\/ortho/.test(url)) return 'basemap_ortho'
  if (/wmts|geopf|ign|geoplateforme|GEOGRAPHICALGRID/i.test(url)) return 'basemap_ign'
  if (/amazonaws|terrarium|elevation-tiles/i.test(url)) return 'dem'
  if (/\.pbf$/.test(url) && /fonts/.test(url)) return 'glyphs'
  if (/\.js(\?|$)/.test(url)) return 'js'
  if (/\.css(\?|$)/.test(url)) return 'css'
  if (/fonts\.(googleapis|gstatic)/.test(url)) return 'google_fonts'
  if (/\.(png|jpg|jpeg|webp|svg|ico)(\?|$)/.test(url)) return 'image'
  if (/\.geojson(\?|$)/.test(url)) return 'geojson_local'
  if (new RegExp(`^${BASE}/(moi|sources|communes|events|v2|map/tuyau|map/tiles/meta|filtre|filters|adresses|parcels|modules|outils)`).test(url)) return 'api'
  return 'autre'
}

const VITALS = `(() => new Promise((res) => {
  const out = { fcp: 0, dom: 0, load: 0, lt_n: 0, lt_ms: 0 }
  try {
    const nav = performance.getEntriesByType('navigation')[0]
    out.dom = nav ? nav.domContentLoadedEventEnd : 0
    out.load = nav ? nav.loadEventEnd : 0
    const fcp = performance.getEntriesByName('first-contentful-paint')[0]
    out.fcp = fcp ? fcp.startTime : 0
  } catch {}
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) { out.lt_n++; out.lt_ms += e.duration } }).observe({ type: 'longtask', buffered: true })
  } catch {}
  setTimeout(() => res(out), 50)
}))()`

async function passe(browser, nom, context) {
  const page = await context.newPage()
  const t0 = performance.now()
  let readyMs = 0
  let derniereTuile = 0
  const rows = []
  const compteur = { n: 0, octets: 0, nTuiles: 0, octetsTuiles: 0 }

  await page.exposeFunction('__ready', () => { readyMs = performance.now() - t0 }).catch(() => {})
  await page.addInitScript(() => {
    window.addEventListener('labuse:ready', () => { try { window.__ready() } catch {} }, { once: true })
  })

  page.on('response', async (r) => {
    const req = r.request()
    const url = r.url()
    const fam = famille(url)
    const timing = req.timing()
    const tStart = timing ? (performance.now() - t0) : 0 // approx: capture au moment de la réponse
    let bytes = 0
    try { const b = await r.body(); bytes = b.length } catch {}
    const fromCache = r.fromServiceWorker() || false
    const enc = (r.headers()['content-encoding'] || '')
    const status = r.status()
    const tRel = performance.now() - t0
    rows.push([nom, fam, req.method(), status, fromCache, tRel.toFixed(0), (timing ? (timing.responseEnd - timing.requestStart).toFixed(0) : '0'), bytes, enc, url])
    compteur.n++; compteur.octets += bytes
    if (fam === 'tuile_parcelle') { compteur.nTuiles++; compteur.octetsTuiles += bytes; derniereTuile = tRel }
  })

  await page.goto(`${BASE}/socle/`, { waitUntil: 'load', timeout: 60000 })
  // attendre le calme réseau : pas de nouvelle requête pendant 1500 ms, ou plafond 20 s
  let lastCount = -1, stableSince = performance.now(), idleMs = 0
  while (performance.now() - t0 < 20000) {
    await page.waitForTimeout(250)
    if (compteur.n !== lastCount) { lastCount = compteur.n; stableSince = performance.now() }
    else if (performance.now() - stableSince > 1500) { idleMs = performance.now() - t0; break }
  }
  if (!idleMs) idleMs = performance.now() - t0

  let v = {}
  try { v = await page.evaluate(VITALS) } catch {}
  for (const row of rows) appendFileSync(REQ_CSV, row.map((c) => String(c).replace(/,/g, '%2C')).join(',') + '\n')
  appendFileSync(RESUME_CSV, [nom, (v.fcp||0).toFixed(0), (v.dom||0).toFixed(0), (v.load||0).toFixed(0),
    readyMs.toFixed(0), derniereTuile.toFixed(0), idleMs.toFixed(0), compteur.n, compteur.nTuiles,
    compteur.octets, compteur.octetsTuiles, v.lt_n||0, (v.lt_ms||0).toFixed(0)].join(',') + '\n')
  console.log(`${nom}: fcp=${(v.fcp||0).toFixed(0)} ready=${readyMs.toFixed(0)} derniere_tuile=${derniereTuile.toFixed(0)} idle=${idleMs.toFixed(0)} n_req=${compteur.n} tuiles=${compteur.nTuiles} octets=${(compteur.octets/1e6).toFixed(2)}Mo`)
  await page.close()
}

const launchOpts = { headless: true }
if (CHROME_BIN) launchOpts.executablePath = CHROME_BIN
const browser = await chromium.launch(launchOpts)

// PASSE 1 : cache vidé (contexte neuf, HAR)
const ctxCold = await browser.newContext({ recordHar: { path: join(harDir, 'boot_cold.har'), content: 'embed' } })
await passe(browser, 'cache_vide', ctxCold)
// PASSE 2 : cache chaud (MÊME contexte → cache disque HTTP conservé)
await passe(browser, 'cache_chaud', ctxCold)
await ctxCold.close()

await browser.close()
console.log('FINI →', RESUME_CSV)
