// CARTE-VITESSE-2 — mesure une scène de chargement carte et l'ajoute au CSV.
// MODE=cold  : 1 contexte NEUF (cache navigateur vide) — à lancer juste après un (re)démarrage
//              de l'API (LRU serveur vide) → « premier visiteur » vrai froid.
// MODE=warm  : 1 contexte, 1 nav d'échauffement, puis PASSES navs réutilisant le contexte
//              (cache disque navigateur + LRU serveur chauds).
// Écrit une ligne/nav dans MESURES/bench.csv. Le shell run_bench.sh orchestre les redémarrages.
//
// env : BASE (def 8495), LABEL (ex "avant"/"apresA"), MODE (cold|warm), PASSES (def 3), CHROME_BIN
import { mkdirSync, appendFileSync, existsSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const HERE = dirname(fileURLToPath(import.meta.url))
const require = createRequire(join(HERE, '..', '..', '..', '..', 'frontend') + '/')
const { chromium } = require('playwright')
const BASE = process.env.BASE ?? 'http://127.0.0.1:8495'
const LABEL = process.env.LABEL ?? 'x'
const MODE = process.env.MODE ?? 'cold'
const PASSES = Number(process.env.PASSES ?? 3)
const OUT = join(HERE, '..', 'MESURES'); mkdirSync(OUT, { recursive: true })
const CSV = join(OUT, 'bench.csv')
if (!existsSync(CSV)) writeFileSync(CSV, 'label,mode,phase,run,fcp_ms,load_ms,derniere_tuile_ms,depart_tuile_ms,idle_ms,lt_n,lt_ms,n_req,octets,n_tuiles\n')

const estTuileParcelle = (u) => /\/map\/tiles\/\d+\/\d+\/\d+\.pbf/.test(u)

const VITALS = `(() => new Promise((res) => {
  const out = { fcp: 0, load: 0, lt_n: 0, lt_ms: 0 }
  try {
    const nav = performance.getEntriesByType('navigation')[0]
    out.load = nav ? nav.loadEventEnd : 0
    const fcp = performance.getEntriesByName('first-contentful-paint')[0]
    out.fcp = fcp ? fcp.startTime : 0
  } catch {}
  try { new PerformanceObserver((l) => { for (const e of l.getEntries()) { out.lt_n++; out.lt_ms += e.duration } }).observe({ type: 'longtask', buffered: true }) } catch {}
  setTimeout(() => res(out), 50)
}))()`

async function unePasse(context, phase, run) {
  const page = await context.newPage()
  const t0 = performance.now()
  let depart = 0, derniere = 0, nTuiles = 0, nReq = 0, octets = 0
  page.on('response', async (r) => {
    const u = r.url(); nReq++
    let b = 0; try { b = (await r.body()).length } catch {}
    octets += b
    if (estTuileParcelle(u)) { const t = performance.now() - t0; if (!depart) depart = t; derniere = t; nTuiles++ }
  })
  await page.goto(`${BASE}/socle/`, { waitUntil: 'load', timeout: 60000 })
  let last = -1, stable = performance.now(), idle = 0
  while (performance.now() - t0 < 20000) {
    await page.waitForTimeout(250)
    if (nReq !== last) { last = nReq; stable = performance.now() }
    else if (performance.now() - stable > 1500) { idle = performance.now() - t0; break }
  }
  if (!idle) idle = performance.now() - t0
  let v = {}; try { v = await page.evaluate(VITALS) } catch {}
  appendFileSync(CSV, [LABEL, MODE, phase, run, (v.fcp||0).toFixed(0), (v.load||0).toFixed(0),
    derniere.toFixed(0), depart.toFixed(0), idle.toFixed(0), v.lt_n||0, (v.lt_ms||0).toFixed(0),
    nReq, octets, nTuiles].join(',') + '\n')
  console.log(`[${LABEL}/${MODE}/${phase}#${run}] fcp=${(v.fcp||0).toFixed(0)} depart_tuile=${depart.toFixed(0)} derniere_tuile=${derniere.toFixed(0)} idle=${idle.toFixed(0)} lt=${(v.lt_ms||0).toFixed(0)}ms tuiles=${nTuiles}`)
  await page.close()
}

const launchOpts = { headless: true }
if (process.env.CHROME_BIN) launchOpts.executablePath = process.env.CHROME_BIN
const browser = await chromium.launch(launchOpts)

if (MODE === 'cold') {
  const ctx = await browser.newContext()
  await unePasse(ctx, 'froid', 0)
  await ctx.close()
} else {
  const ctx = await browser.newContext()
  await unePasse(ctx, 'echauffement', 0) // amorce cache
  for (let i = 1; i <= PASSES; i++) await unePasse(ctx, 'chaud', i)
  await ctx.close()
}
await browser.close()
