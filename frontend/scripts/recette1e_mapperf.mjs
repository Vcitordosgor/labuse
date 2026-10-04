/**
 * MAPLIBRE-1 — mesure de PERFORMANCE en conditions réelles (Chrome non-headless, GPU matériel).
 * Même parcours que Vic ; compare v4 (main) et v6 (fix/maplibre-1). Chiffres fiables (frames, blocage
 * fil principal, workers, renderer WebGL) + un court trace DevTools best-effort.
 *
 * LANCEMENT (depuis frontend/) :
 *   LABEL=v4 BASE_URL=http://127.0.0.1:5895/socle/ node scripts/maplibre1_perf.mjs
 *   LABEL=v6 BASE_URL=http://127.0.0.1:5895/socle/ node scripts/maplibre1_perf.mjs
 *
 * headless:false + channel:chrome → vrai GPU. Le renderer WebGL est reporté (vérifie « Metal » = matériel).
 */
import pkg from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const LABEL = process.env.LABEL || 'v?'
const BASE = process.env.BASE_URL || 'http://127.0.0.1:5895/socle/'
const OUT = path.resolve(process.env.OUT || '../reports/maplibre1/perf')
const SP = [55.29, -21.02]
const log = (...a) => console.log(`[perf:${LABEL}]`, ...a)

function waitIdle(page, ms) {
  return page.evaluate((ms) => new Promise((res) => {
    const m = window.__labuse_map; if (!m) return res()
    let done = false; const fin = () => { if (!done) { done = true; res() } }
    const t = setTimeout(fin, ms); m.once('idle', () => { clearTimeout(t); fin() })
  }), ms)
}
async function timed(page, fn, idleMs = 8000) { const t0 = Date.now(); await fn(); await waitIdle(page, idleMs); return Date.now() - t0 }

async function main() {
  await mkdir(OUT, { recursive: true })
  const browser = await chromium.launch({ headless: false, channel: 'chrome' })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const client = await ctx.newCDPSession(page)

  const workers = new Set()
  await client.send('Target.setDiscoverTargets', { discover: true })
  client.on('Target.targetCreated', ({ targetInfo }) => {
    if (targetInfo.type === 'worker' || targetInfo.type === 'shared_worker') workers.add(targetInfo.url)
  })
  page.on('console', (m) => { if (m.type() === 'error' && !/40[0-4]/.test(m.text())) log('ERR', m.text().slice(0, 120)) })

  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
  await waitIdle(page, 10000)
  await page.waitForTimeout(2000)

  const diag = await page.evaluate(() => {
    const m = window.__labuse_map
    let webglRenderer = 'n/a'
    try {
      const c = document.createElement('canvas'); const gl = c.getContext('webgl2') || c.getContext('webgl')
      const dbg = gl.getExtension('WEBGL_debug_renderer_info'); webglRenderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)
    } catch { /* noop */ }
    const res = performance.getEntriesByType('resource').filter((r) => /maplibre-gl-worker/.test(r.name))
    return {
      webglRenderer, hardwareConcurrency: navigator.hardwareConcurrency, devicePixelRatio: window.devicePixelRatio,
      canvasPixelRatio: m?.getPixelRatio ? m.getPixelRatio() : null, workerScriptLoads: res.length,
    }
  })
  log('DIAG', JSON.stringify(diag))

  // sonde frames (scopée aux animations) + long tasks (blocage fil principal)
  await page.evaluate(() => {
    window.__perf = { frames: [], longtasks: [] }
    try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__perf.longtasks.push(e.duration) }).observe({ entryTypes: ['longtask'] }) } catch { /* noop */ }
    window.__frOn = () => { window.__perf.frames.length = 0; window.__fr = true; let last = performance.now(); const tk = (t) => { window.__perf.frames.push(t - last); last = t; if (window.__fr) requestAnimationFrame(tk) }; requestAnimationFrame(tk) }
    window.__frOff = () => { window.__fr = false }
    window.__ltReset = () => { window.__perf.longtasks.length = 0 }
  })

  // PARCOURS — on échantillonne les frames UNIQUEMENT pendant les animations (zoom/pan), pas les attentes.
  await page.evaluate(() => { window.__ltReset(); window.__frOn() })
  const tZoom = await timed(page, async () => {
    await page.evaluate((c) => window.__labuse_map.flyTo({ center: c, zoom: 16, duration: 3000 }), SP)
    await page.waitForTimeout(3200)
  })
  const tPan = await timed(page, async () => {
    await page.evaluate(async () => { const m = window.__labuse_map; for (let i = 0; i < 8; i++) { m.panBy([280, i % 2 ? 160 : -160], { duration: 320 }); await new Promise((r) => setTimeout(r, 360)) } })
  })
  const tZoomOut = await timed(page, async () => {
    await page.evaluate((c) => window.__labuse_map.flyTo({ center: c, zoom: 12, duration: 1500 }), SP); await page.waitForTimeout(1700)
    await page.evaluate((c) => window.__labuse_map.flyTo({ center: c, zoom: 16, duration: 1500 }), SP); await page.waitForTimeout(1700)
  })
  await page.evaluate(() => window.__frOff())
  const tLayers = await timed(page, async () => {
    await page.evaluate(() => { for (const k of ['sup', 'icpe', 'zonage_parcelle']) window.__labuse.toggleTuyau(k) })
  }, 10000)

  const perfAnim = await page.evaluate(() => window.__perf)

  // ── nb de workers maplibre RÉELLEMENT configurés ──
  const workerCount = await page.evaluate(() => { const g = window.__mlgl; return g && g.getWorkerCount ? g.getWorkerCount() : null })

  // ── IDLE-REPAINT : la carte redessine-t-elle en continu AU REPOS ? (0 attendu ; >0 = busy-loop) ──
  await waitIdle(page, 6000); await page.waitForTimeout(600)
  const idleRenders = await page.evaluate(() => new Promise((res) => {
    const m = window.__labuse_map; let n = 0; const h = () => n++; m.on('render', h)
    setTimeout(() => { m.off('render', h); res(n) }, 2000)
  }))

  // ── INTERACTION RÉELLE : molette (zoom) + glisser (pan) = le chemin de l'utilisateur ──
  await page.mouse.move(720, 450)
  await page.evaluate(() => { window.__ltReset(); window.__frOn() })
  for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(110) }   // zoom avant
  for (let i = 0; i < 12; i++) { await page.mouse.wheel(0, 120); await page.waitForTimeout(110) }    // zoom arrière
  await page.mouse.move(720, 450); await page.mouse.down()
  for (let i = 0; i < 24; i++) { await page.mouse.move(720 + i * 14, 450 + (i % 2 ? 70 : -70), { steps: 1 }); await page.waitForTimeout(28) }
  await page.mouse.up(); await page.waitForTimeout(600)
  await page.evaluate(() => window.__frOff())
  const perfInteract = await page.evaluate(() => window.__perf)

  const stat = (arr) => {
    const f = arr.filter((d) => d > 0 && d < 3000); const s = [...f].sort((a, b) => a - b)
    const pc = (p) => s.length ? +s[Math.floor(s.length * p)].toFixed(1) : null
    const slow = f.filter((d) => d > 33).length
    return { n: f.length, medianMs: pc(0.5), p95Ms: pc(0.95), p99Ms: pc(0.99), slowOver33ms: slow, pctSlow: +(slow / Math.max(1, f.length) * 100).toFixed(1) }
  }
  const metrics = {
    label: LABEL, base: BASE, diag, workerCount, workersCDP: workers.size,
    idleRendersIn2s: idleRenders,   // ★ 0 = on-demand (bon) ; ~120 = repaint continu (régression)
    framesAnim: stat(perfAnim.frames),
    framesInteract: stat(perfInteract.frames),
    longtasksInteract: { n: perfInteract.longtasks.length, totalMs: +perfInteract.longtasks.reduce((a, b) => a + b, 0).toFixed(0), maxMs: +Math.max(0, ...perfInteract.longtasks).toFixed(0) },
    parcours_ms: { zoom: tZoom, pan: tPan, zoomOutIn: tZoomOut, layers: tLayers },
  }
  await writeFile(path.join(OUT, `perf_${LABEL}.json`), JSON.stringify(metrics, null, 2))   // TOUJOURS écrit
  log('METRICS', JSON.stringify(metrics, null, 2))

  // ── trace DevTools COURT + best-effort (petit = pas de dépassement de buffer CDP) ──
  try {
    const traceDone = new Promise((res, rej) => { client.once('Tracing.tracingComplete', (e) => res(e.stream)); setTimeout(() => rej(new Error('trace timeout')), 15000) })
    await client.send('Tracing.start', { traceConfig: { recordMode: 'recordAsMuchAsPossible', includedCategories: ['devtools.timeline', 'blink.user_timing'] }, transferMode: 'ReturnAsStream' })
    await page.evaluate((c) => window.__labuse_map.flyTo({ center: c, zoom: 12, duration: 2500 }), SP); await page.waitForTimeout(2700)
    await client.send('Tracing.end')
    const stream = await traceDone
    const chunks = []
    while (stream) { const r = await client.send('IO.read', { handle: stream, size: 512 * 1024 }); chunks.push(Buffer.from(r.data, r.base64Encoded ? 'base64' : 'utf8')); if (r.eof) break }
    if (stream) { await client.send('IO.close', { handle: stream }); await writeFile(path.join(OUT, `trace_${LABEL}.json`), Buffer.concat(chunks)); log('trace écrit', Buffer.concat(chunks).length, 'o') }
  } catch (e) { log('trace ignoré (best-effort):', String(e).slice(0, 80)) }

  await browser.close()
}
main().catch((e) => { console.error(e); process.exit(1) })
