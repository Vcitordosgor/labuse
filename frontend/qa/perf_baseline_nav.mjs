// LA BUSE — M6.2 PERF, Lot 1 : BASELINE NAVIGATEUR (mesure pure, aucune optimisation).
// Instance dev-mode SANS rate-limit : http://127.0.0.1:8011/socle/  (NE PAS toucher 8000/8010)
//
// Méthode :
//  - FROID = nouveau context Chromium à chaque run (cache/HTTP disque neuf) + Cache-Control bypass
//    via page.route (Pragma:no-cache). CHAUD = 2e goto dans LE MÊME context (SW/HTTP-cache chauds).
//  - TTFB / FCP / TTI : PerformanceNavigationTiming + PerformancePaintTiming (FCP), TTI approximé
//    par « quiet window » (proxy documenté : 1er instant ≥ FCP où le réseau reste calme 500 ms,
//    borné par domInteractive) — le vrai TTI de Lighthouse n'est pas exposé par l'API navigateur.
//  - Poids/requêtes : page.on('response') + (encodedBodySize via Resource Timing, fallback body().length),
//    ventilés par type (js/css/pbf tuiles/fonts/images/json/autres).
//  - Carte : 1re tuile pbf = timing de la 1re réponse /map/tiles/…pbf après goto.
//    Fluidité pan/zoom : sampling requestAnimationFrame → frames rendues vs attendues à 60 fps
//    pendant 3 pans + 2 zooms programmés (proxy « frames perdues »).
//  - Couches : clic case → « rendu » = map idle (loaded && areTilesLoaded). Réseau : octets pbf/json
//    téléchargés pendant la bascule.
//  - Fiche : saisie IDU dans l'omnibox → [data-badge-verdict] présent = contenu complet.
//  - Panneau résultats : clic chip/commune → nombre de cartes stable (2 mesures identiques à 250 ms).
//
// Usage : cd frontend && node qa/perf_baseline_nav.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8011/socle/'
const OUT = process.env.OUT || '../reports/m62-perf'
const N = Number(process.env.REP || 5)
mkdirSync(OUT, { recursive: true })
const VIEWPORT = { width: 1440, height: 900 }

// ── stats ──────────────────────────────────────────────────────────────────
const median = (a) => { const s = [...a].filter((x) => x != null).sort((x, y) => x - y); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2) : null }
const pct = (a, p) => { const s = [...a].filter((x) => x != null).sort((x, y) => x - y); if (!s.length) return null; const i = Math.ceil((p / 100) * s.length) - 1; return s[Math.min(Math.max(i, 0), s.length - 1)] }
const r1 = (x) => x == null ? null : Math.round(x * 10) / 10
const KB = (b) => Math.round(b / 1024)

const TYPE_OF = (url, ct = '') => {
  const u = url.split('?')[0]
  if (/\.pbf($|\/)/.test(u) || /\/map\/tiles\//.test(u)) return 'tiles_pbf'
  if (/\.(js|mjs)$/.test(u) || ct.includes('javascript')) return 'js'
  if (/\.css$/.test(u) || ct.includes('text/css')) return 'css'
  if (/\.(woff2?|ttf|otf|eot)$/.test(u) || ct.includes('font')) return 'fonts'
  if (/\.(png|jpe?g|webp|gif|svg|avif)$/.test(u) || ct.startsWith('image/')) return 'images'
  if (/\.json($|\?)/.test(u) || ct.includes('json') || /\/map\/layers|\/parcels\//.test(u)) return 'json'
  if (ct.includes('text/html') || u.endsWith('/socle/') || u.endsWith('/socle')) return 'html'
  return 'autres'
}

// ── métriques de navigation (dans le contexte page) ──────────────────────────
async function navMetrics(page) {
  return page.evaluate(async () => {
    const nav = performance.getEntriesByType('navigation')[0] || {}
    const paint = performance.getEntriesByType('paint')
    const fcp = paint.find((p) => p.name === 'first-contentful-paint')?.startTime ?? null
    const ttfb = nav.responseStart ?? null
    // TTI proxy : quiet-window de 500 ms de calme réseau, ≥ FCP, borné inf. par domInteractive
    let tti = null
    try {
      const res = performance.getEntriesByType('resource')
        .map((r) => ({ end: r.responseEnd })).filter((r) => r.end > 0).sort((a, b) => a.end - b.end)
      const floor = Math.max(fcp ?? 0, nav.domInteractive ?? 0)
      let last = floor
      for (const r of res) {
        if (r.end <= floor) continue
        if (r.end - last > 500) break
        last = r.end
      }
      tti = last
    } catch { tti = nav.domInteractive ?? null }
    return {
      ttfb, fcp, tti,
      domContentLoaded: nav.domContentLoadedEventEnd ?? null,
      loadEvent: nav.loadEventEnd ?? null,
      domInteractive: nav.domInteractive ?? null,
    }
  })
}

// collecteur réseau via CDP (source de vérité) :
//  transferred = encodedDataLength (octets RÉELS sur le fil, 0 sur cache-hit disque).
//  decoded     = dataLength cumulé (poids décodé).
//  cached      = response.fromDiskCache || fromServiceWorker (CDP) — fiable pour séparer FROID/CHAUD.
// Retour : { rows, detach() }.
async function attachNet(page) {
  const rows = []
  const meta = new Map()     // requestId -> {url, type, status, cached, mime}
  const decoded = new Map()  // requestId -> octets décodés cumulés
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Network.enable').catch(() => {})
  cdp.on('Network.responseReceived', (e) => {
    const r = e.response || {}
    const url = r.url || ''
    if (url.startsWith('data:') || url.startsWith('blob:')) return
    meta.set(e.requestId, { url, type: TYPE_OF(url, (r.mimeType || '').toLowerCase()), status: r.status, cached: !!r.fromDiskCache || !!r.fromServiceWorker })
  })
  cdp.on('Network.dataReceived', (e) => { decoded.set(e.requestId, (decoded.get(e.requestId) || 0) + (e.dataLength || 0)) })
  cdp.on('Network.loadingFinished', (e) => {
    const m = meta.get(e.requestId)
    if (!m) return
    rows.push({ url: m.url, type: m.type, status: m.status, cached: m.cached, transferred: e.encodedDataLength || 0, decoded: decoded.get(e.requestId) || 0 })
  })
  return { rows, detach: () => cdp.detach().catch(() => {}) }
}

const idle = (page) => page.evaluate(() => new Promise((res) => {
  const m = window.__labuse_map
  if (!m) return res(false)
  if (m.loaded() && m.areTilesLoaded()) return res(true)
  const to = setTimeout(() => res(true), 12000)
  m.once('idle', () => { clearTimeout(to); res(true) })
}))

const waitApp = (page) => page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 45000 })

async function launchCtx(browser, { bypassCache }) {
  const ctx = await browser.newContext({ viewport: VIEWPORT, bypassCSP: true })
  if (bypassCache) {
    await ctx.route('**/*', async (route) => {
      const h = { ...route.request().headers(), 'cache-control': 'no-cache', pragma: 'no-cache' }
      route.continue({ headers: h }).catch(() => {})
    })
  }
  return ctx
}

// ════════════════════════════════════════════════════════════════════════════
//  1. PREMIER CHARGEMENT (froid / chaud)
// ════════════════════════════════════════════════════════════════════════════
async function measureLoad(browser) {
  const cold = { ttfb: [], fcp: [], tti: [], dcl: [], load: [] }
  const hot = { ttfb: [], fcp: [], tti: [], dcl: [], load: [] }
  const coldNetAgg = []  // par run : {byType:{...}, count, total}
  const hotNetAgg = []

  const aggregate = (rows) => {
    const byType = {}
    let total = 0, totalDecoded = 0, count = 0, cachedN = 0
    for (const r of rows) {
      byType[r.type] = byType[r.type] || { bytes: 0, decoded: 0, n: 0 }
      byType[r.type].bytes += r.transferred; byType[r.type].decoded += r.decoded; byType[r.type].n += 1
      total += r.transferred; totalDecoded += r.decoded; count += 1
      if (r.cached) cachedN += 1
    }
    return { byType, total, totalDecoded, count, cachedN }
  }

  for (let i = 0; i < N; i++) {
    // ── FROID : context NEUF + bypass cache (no-cache) sur TOUTES les requêtes ──
    const ctxCold = await launchCtx(browser, { bypassCache: true })
    const pageCold = await ctxCold.newPage()
    const netCold = await attachNet(pageCold)
    await pageCold.goto(BASE + '#v=1', { waitUntil: 'load', timeout: 60000 })
    await waitApp(pageCold).catch(() => {})
    await idle(pageCold).catch(() => {})
    await pageCold.waitForTimeout(1200) // laisser le réseau tuiles/json se stabiliser
    const mc = await navMetrics(pageCold)
    cold.ttfb.push(mc.ttfb); cold.fcp.push(mc.fcp); cold.tti.push(mc.tti); cold.dcl.push(mc.domContentLoaded); cold.load.push(mc.loadEvent)
    await pageCold.waitForTimeout(400)
    coldNetAgg.push(aggregate(netCold.rows))
    await ctxCold.close()

    // ── CHAUD : context NEUF SANS bypass — warm-up goto (peuple le cache navigateur,
    //    tuiles Cache-Control max-age=3600), PUIS goto mesuré (assets/tuiles servis du cache).
    const ctxHot = await launchCtx(browser, { bypassCache: false })
    const pageHot = await ctxHot.newPage()
    await pageHot.goto(BASE + '#v=1', { waitUntil: 'load', timeout: 60000 })
    await waitApp(pageHot).catch(() => {})
    await idle(pageHot).catch(() => {})
    await pageHot.waitForTimeout(1200)
    // goto mesuré (caches chauds)
    await pageHot.goto('about:blank')
    const netHot = await attachNet(pageHot)
    await pageHot.goto(BASE + '#v=1', { waitUntil: 'load', timeout: 60000 })
    await waitApp(pageHot).catch(() => {})
    await idle(pageHot).catch(() => {})
    await pageHot.waitForTimeout(1200)
    const mh = await navMetrics(pageHot)
    hot.ttfb.push(mh.ttfb); hot.fcp.push(mh.fcp); hot.tti.push(mh.tti); hot.dcl.push(mh.domContentLoaded); hot.load.push(mh.loadEvent)
    const aggH = aggregate(netHot.rows)
    hotNetAgg.push(aggH)
    await ctxHot.close()

    const aggC = aggregate(netCold.rows)
    process.stdout.write(`  load run ${i + 1}/${N}: FROID fcp=${r1(mc.fcp)} tti=${r1(mc.tti)} transf=${KB(aggC.total)}KB (${aggC.cachedN}/${aggC.count} cache) | CHAUD fcp=${r1(mh.fcp)} transf=${KB(aggH.total)}KB (${aggH.cachedN}/${aggH.count} cache)\n`)
  }

  const summNet = (arr) => {
    const types = {}
    let totals = [], decodeds = [], counts = [], cachedNs = []
    for (const run of arr) {
      totals.push(run.total); decodeds.push(run.totalDecoded); counts.push(run.count); cachedNs.push(run.cachedN)
      for (const [t, v] of Object.entries(run.byType)) {
        types[t] = types[t] || { bytes: [], decoded: [], n: [] }
        types[t].bytes.push(v.bytes); types[t].decoded.push(v.decoded); types[t].n.push(v.n)
      }
    }
    const byType = {}
    for (const [t, v] of Object.entries(types)) byType[t] = { transferKB: KB(median(v.bytes) || 0), decodedKB: KB(median(v.decoded) || 0), medianReq: median(v.n) }
    return { byType, medianTransferKB: KB(median(totals) || 0), medianDecodedKB: KB(median(decodeds) || 0), medianReq: median(counts), medianCacheHits: median(cachedNs), p95TransferKB: KB(pct(totals, 95) || 0) }
  }

  const summ = (o) => ({
    ttfb: { median: r1(median(o.ttfb)), p95: r1(pct(o.ttfb, 95)) },
    fcp: { median: r1(median(o.fcp)), p95: r1(pct(o.fcp, 95)) },
    tti: { median: r1(median(o.tti)), p95: r1(pct(o.tti, 95)) },
    domContentLoaded: { median: r1(median(o.dcl)), p95: r1(pct(o.dcl, 95)) },
    load: { median: r1(median(o.load)), p95: r1(pct(o.load, 95)) },
  })

  return {
    cold: { timing: summ(cold), network: summNet(coldNetAgg) },
    hot: { timing: summ(hot), network: summNet(hotNetAgg) },
    raw: { cold, hot },
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  2. CARTE : 1re tuile, fluidité pan/zoom, bascule couches
// ════════════════════════════════════════════════════════════════════════════
async function measureMap(browser) {
  const firstTile = []
  const panzoom = []
  const layerTimes = {}  // label -> [ms]
  const layerNet = {}    // label -> [bytes]
  const layerReq = {}    // label -> [nb requêtes pbf/geojson]

  const LAYERS = [
    'Zonage PLU (parcelles)',
    '50 pas géométriques',
    'PPR multirisque',
    'Vue mer',
    'Équipements',
    'ANRU (NPNRU)',
  ]
  for (const l of LAYERS) { layerTimes[l] = []; layerNet[l] = []; layerReq[l] = [] }

  for (let i = 0; i < N; i++) {
    const ctx = await launchCtx(browser, { bypassCache: false })
    const page = await ctx.newPage()

    // ── 1re tuile pbf : horodater le goto puis la 1re réponse /map/tiles/…pbf ──
    let tGoto = 0, tFirstTile = null
    page.on('response', (r) => {
      const u = r.url()
      if (tFirstTile == null && /\/map\/tiles\/.*\.pbf/.test(u.split('?')[0])) tFirstTile = Date.now() - tGoto
    })
    tGoto = Date.now()
    await page.goto(BASE + '#v=1', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await waitApp(page).catch(() => {})
    await idle(page).catch(() => {})
    firstTile.push(tFirstTile)

    // ── fluidité pan/zoom : 3 pans + 2 zooms programmés ──
    //  Métrique fiable en headless = compteur d'événements MapLibre 'render' (1 par frame RÉELLEMENT
    //  dessinée par la carte, indépendant du throttling rAF headless) + durée totale d'animation.
    //  fpsRender = render/s pendant les animations. On mesure aussi le temps inter-frame max (pire à-coup).
    const fluid = await page.evaluate(async () => {
      const m = window.__labuse_map
      let renders = 0, last = performance.now(), maxGap = 0
      const gaps = []
      const onRender = () => { const now = performance.now(); const g = now - last; if (renders > 0) { gaps.push(g); if (g > maxGap) maxGap = g } last = now; renders++ }
      m.on('render', onRender)
      const t0 = performance.now()
      const moves = [
        () => m.panBy([260, 0], { duration: 500 }),
        () => m.panBy([0, 240], { duration: 500 }),
        () => m.panBy([-200, -160], { duration: 500 }),
        () => m.zoomTo(m.getZoom() + 1.5, { duration: 600 }),
        () => m.zoomTo(m.getZoom() - 1.2, { duration: 600 }),
      ]
      for (const mv of moves) {
        await new Promise((res) => { let done = false; const fin = () => { if (!done) { done = true; res() } }; m.once('moveend', fin); mv(); setTimeout(fin, 1400) })
      }
      m.off('render', onRender)
      const elapsed = performance.now() - t0
      const fpsRender = renders / (elapsed / 1000)
      // p95 du temps inter-frame (ms) : > 16.7 ms = frame perdue à 60 fps
      gaps.sort((a, b) => a - b)
      const p95gap = gaps.length ? gaps[Math.min(Math.ceil(0.95 * gaps.length) - 1, gaps.length - 1)] : null
      const dropped = gaps.filter((g) => g > 16.7).length
      return {
        renderFrames: renders, elapsedMs: Math.round(elapsed),
        fpsRender: Math.round(fpsRender * 10) / 10,
        interFrameP95Ms: p95gap == null ? null : Math.round(p95gap * 10) / 10,
        interFrameMaxMs: Math.round(maxGap * 10) / 10,
        framesOver16ms: dropped, totalGaps: gaps.length,
        droppedPct: gaps.length ? Math.round((dropped / gaps.length) * 1000) / 10 : null,
      }
    })
    panzoom.push(fluid)

    // reset vue avant les bascules couches
    await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.53, -21.13], zoom: 10.5 }))
    await idle(page).catch(() => {})

    // ── bascule de chaque couche : temps clic → idle + octets réseau ──
    for (const label of LAYERS) {
      let bytes = 0, reqN = 0
      const onResp = async (r) => {
        const u = r.url().split('?')[0]
        if (/\.pbf$/.test(u) || /layers\.geojson/.test(u) || /\/map\/layers/.test(u)) {
          reqN++
          try { const b = await r.body(); bytes += b.length } catch {}
        }
      }
      page.on('response', onResp)
      const t0 = Date.now()
      await page.locator(`aside button:has-text("${label}")`).first().click().catch(() => {})
      await idle(page).catch(() => {})
      await page.waitForTimeout(300)
      const dt = Date.now() - t0
      page.off('response', onResp)
      layerTimes[label].push(dt)
      layerNet[label].push(bytes)
      layerReq[label].push(reqN)
      // re-toggle OFF pour repartir propre
      await page.locator(`aside button:has-text("${label}")`).first().click().catch(() => {})
      await page.waitForTimeout(200)
    }

    await ctx.close()
    process.stdout.write(`  map run ${i + 1}/${N}: 1re tuile=${tFirstTile} ms · render fps~${fluid.fpsRender} · inter-frame p95 ${fluid.interFrameP95Ms} ms (dropped ${fluid.droppedPct}%)\n`)
  }

  const layerSumm = {}
  for (const l of LAYERS) {
    layerSumm[l] = {
      msMedian: median(layerTimes[l]), msP95: pct(layerTimes[l], 95),
      netMedianKB: KB(median(layerNet[l]) || 0),
      reqMedian: median(layerReq[l]),
      declencheReseau: (median(layerNet[l]) || 0) > 2048,
    }
  }
  return {
    firstTileMs: { median: median(firstTile), p95: pct(firstTile, 95) },
    panzoom: {
      // NB headless : le compositeur navigateur ne pilote pas un vsync 60 fps continu ;
      // fpsRender = nb d'événements MapLibre 'render'/s (frames RÉELLEMENT dessinées) — borne
      // BASSE (un run headed en montrerait davantage). interFrame p95/max = à-coups réels observés.
      fpsRenderMedian: median(panzoom.map((p) => p.fpsRender)),
      interFrameP95MsMedian: median(panzoom.map((p) => p.interFrameP95Ms)),
      interFrameMaxMsMedian: median(panzoom.map((p) => p.interFrameMaxMs)),
      droppedPctMedian: median(panzoom.map((p) => p.droppedPct)),
      renderFramesMedian: median(panzoom.map((p) => p.renderFrames)),
      caveat: 'headless : fpsRender = frames MapLibre réellement dessinées (borne basse, pas de vsync continu). Proxy jank = interFrame p95/max ms.',
    },
    layers: layerSumm,
    raw: { firstTile, panzoom, layerTimes, layerNet, layerReq },
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  3. FICHE PARCELLE (10 parcelles variées) — P50/P95
// ════════════════════════════════════════════════════════════════════════════
const PARCELLES = [
  '97410000AS1425', // mandaté — Saint-Benoît, brûlante
  '97423000AB1908', // mandaté — Les Trois-Bassins, brûlante
  '97423000AB1341', // mandaté — Les Trois-Bassins, écartée
  '97404000AT0870', // L'Étang-Salé, chaude
  '97411000KA0296', // Saint-Denis, brûlante
  '97413000AV2267', // Saint-Leu, brûlante
  '97408000AP1647', // La Possession, chaude
  '97416000EY1406', // Saint-Pierre, brûlante
  '97419000AE0500', // Sainte-Rose, chaude
  '97406000AI0941', // La Plaine-des-Palmistes, chaude
]

// « contenu complet » = l'en-tête de fiche affiche EXACTEMENT l'IDU cherché (<div>{idu}</div> mono)
// ET le badge verdict est rendu (n'apparaît qu'une fois la data `f` chargée depuis /parcels/{idu}).
// La data fiche est mise en cache côté client (React Query) : rouvrir le MÊME IDU dans la session
// mesure le cache (~200 ms), pas l'ouverture réelle. On mesure donc :
//  - froid : 1 ouverture par parcelle dans un CONTEXTE NEUF (cache client + HTTP vierges) → P50/P95
//            sur les 10 parcelles = latence d'ouverture d'une fiche jamais consultée (cas réel).
//  - chaud : réouverture immédiate du même IDU (même page) = fiche déjà en cache client.
async function measureFiche(browser) {
  const waitFiche = async (page, idu) => page.waitForFunction((target) => {
    const badge = document.querySelector('[data-badge-verdict]')
    if (!badge || !badge.textContent || !badge.textContent.trim()) return false
    const heads = [...document.querySelectorAll('.font-mono')].map((e) => (e.textContent || '').trim())
    return heads.includes(target)
  }, idu, { timeout: 30000 }).then(() => true).catch(() => false)

  const coldPerParcel = {}, warmPerParcel = {}
  const cold = [], warm = []

  for (const idu of PARCELLES) {
    // ── FROID : contexte neuf par parcelle (cache client vierge) ──
    const ctx = await launchCtx(browser, { bypassCache: false })
    const page = await ctx.newPage()
    await page.goto(BASE + '#f=1&v=1', { waitUntil: 'load', timeout: 60000 })
    await waitApp(page).catch(() => {})
    await idle(page).catch(() => {})
    await page.waitForTimeout(1200)
    const input = page.locator('input[title^="Recherche du dashboard"]')
    await input.fill(idu).catch(() => {})
    const t0 = Date.now()
    await page.keyboard.press('Enter')
    const okCold = await waitFiche(page, idu)
    const dtCold = okCold ? Date.now() - t0 : null
    coldPerParcel[idu] = dtCold; if (dtCold != null) cold.push(dtCold)

    // ── CHAUD : refermer + rouvrir le MÊME IDU (data déjà en cache client) ──
    await page.keyboard.press('Escape').catch(() => {})
    await page.waitForFunction(() => !document.querySelector('[data-badge-verdict]'), null, { timeout: 8000 }).catch(() => {})
    await input.fill('').catch(() => {}); await input.fill(idu).catch(() => {})
    const t1 = Date.now()
    await page.keyboard.press('Enter')
    const okWarm = await waitFiche(page, idu)
    const dtWarm = okWarm ? Date.now() - t1 : null
    warmPerParcel[idu] = dtWarm; if (dtWarm != null) warm.push(dtWarm)

    await ctx.close()
    process.stdout.write(`  fiche ${idu}: FROID=${dtCold} ms · CHAUD(réouv.)=${dtWarm} ms\n`)
  }

  return {
    cold: { p50: median(cold), p95: pct(cold, 95), n: cold.length, perParcel: coldPerParcel },
    warmReopen: { p50: median(warm), p95: pct(warm, 95), n: warm.length, perParcel: warmPerParcel },
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  4. PANNEAU RÉSULTATS : application d'un filtre → compteur + liste stable
// ════════════════════════════════════════════════════════════════════════════
async function measureFilters(browser) {
  const tierT = [], communeT = []
  const ctx = await launchCtx(browser, { bypassCache: false })

  const stableCount = async (page) => {
    // attend un nombre de cartes stable sur 2 lectures espacées
    let prev = -1
    for (let k = 0; k < 40; k++) {
      const n = await page.locator('[data-results-scroll] button').count()
      if (n > 0 && n === prev) return n
      prev = n
      await page.waitForTimeout(250)
    }
    return prev
  }

  for (let i = 0; i < N; i++) {
    const page = await ctx.newPage()
    await page.goto(BASE + '#v=1', { waitUntil: 'load', timeout: 60000 })
    await waitApp(page).catch(() => {})
    await idle(page).catch(() => {})
    // attendre la liste initiale
    await page.waitForFunction(() => document.querySelectorAll('[data-results-scroll] button').length > 0, null, { timeout: 20000 }).catch(() => {})
    await page.waitForTimeout(800)

    // filtre tier = brûlante (clic chip)
    const t0 = Date.now()
    await page.locator('button', { hasText: 'Brûlantes v2' }).first().click().catch(() => {})
    await stableCount(page)
    tierT.push(Date.now() - t0)

    // puis filtre commune (via omnibox → bascule périmètre)
    const t1 = Date.now()
    const input = page.locator('input[title^="Recherche du dashboard"]')
    await input.fill('Saint-Paul').catch(() => {})
    await page.keyboard.press('Enter')
    await stableCount(page)
    communeT.push(Date.now() - t1)

    await page.close()
    process.stdout.write(`  filtre run ${i + 1}/${N}: tier=${tierT.at(-1)} ms · commune=${communeT.at(-1)} ms\n`)
  }
  await ctx.close()
  return {
    tierBrulante: { median: median(tierT), p95: pct(tierT, 95), samples: tierT },
    commune: { median: median(communeT), p95: pct(communeT, 95), samples: communeT },
  }
}

// ════════════════════════════════════════════════════════════════════════════
;(async () => {
  const browser = await chromium.launch()
  console.log(`\n=== M6.2 PERF baseline navigateur — ${BASE} (${N} répétitions, ${VIEWPORT.width}×${VIEWPORT.height}) ===\n`)

  console.log('[1/4] Premier chargement (froid/chaud)…')
  const load = await measureLoad(browser)

  console.log('\n[2/4] Carte (1re tuile, pan/zoom, couches)…')
  const map = await measureMap(browser)

  console.log('\n[3/4] Fiche parcelle (10 parcelles)…')
  const fiche = await measureFiche(browser)

  console.log('\n[4/4] Panneau résultats (filtres)…')
  const filters = await measureFilters(browser)

  await browser.close()

  const data = { meta: { base: BASE, repetitions: N, viewport: VIEWPORT, date: new Date().toISOString(), branch: 'feat/m62-perf' }, load, map, fiche, filters }
  writeFileSync(`${OUT}/baseline-navigateur.json`, JSON.stringify(data, null, 2))
  console.log(`\n→ ${OUT}/baseline-navigateur.json écrit.`)

  // ── petit récap console ──
  console.log('\n─── RÉCAP ───')
  console.log('FROID fcp median', load.cold.timing.fcp.median, 'ms · tti', load.cold.timing.tti.median, 'ms · transféré', load.cold.network.medianTransferKB, 'KB (décodé', load.cold.network.medianDecodedKB, 'KB) /', load.cold.network.medianReq, 'req')
  console.log('CHAUD fcp median', load.hot.timing.fcp.median, 'ms · transféré', load.hot.network.medianTransferKB, 'KB /', load.hot.network.medianReq, 'req')
  console.log('1re tuile', map.firstTileMs.median, 'ms · pan/zoom render', map.panzoom.fpsRenderMedian, 'fps · inter-frame p95', map.panzoom.interFrameP95MsMedian, 'ms')
  console.log('fiche FROID p50', fiche.cold.p50, 'ms · p95', fiche.cold.p95, 'ms | réouv. p50', fiche.warmReopen.p50, 'ms')
  console.log('filtre tier', filters.tierBrulante.median, 'ms · commune', filters.commune.median, 'ms')
})().catch((e) => { console.error(e); process.exit(1) })
