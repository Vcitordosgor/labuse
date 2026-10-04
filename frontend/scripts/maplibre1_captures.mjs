/**
 * MAPLIBRE-1 — planche avant/après (maplibre 4 → 6) + vitesse + console.
 *
 * Pilote la carte via window.__labuse / window.__labuse_map (App.tsx) + la MapToolbar.
 * Best-effort par scène : une scène qui échoue est loggée, jamais fatale.
 *
 * PRÉREQUIS : API sur :5945, front (dev OU build servi par l'API) accessible via BASE_URL.
 * LANCEMENT (depuis frontend/) :
 *   PHASE=avant BASE_URL=http://localhost:8745/socle/ node scripts/maplibre1_captures.mjs
 *   PHASE=apres MODE=build BASE_URL=http://127.0.0.1:5945/socle/ node scripts/maplibre1_captures.mjs
 */
import { chromium } from 'playwright'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

// maplibre 6 EXIGE WebGL2 (maplibre 4 se repliait sur WebGL1). Chrome headless épuise ses contextes
// WebGL2 GPU au fil des pages → GPUInitializationError intermittent. On FORCE le rendu logiciel
// (ANGLE/SwiftShader) : WebGL2 toujours disponible, contextes illimités, backend IDENTIQUE avant↔après
// (comparaison pixel honnête). En navigateur réel (WebGL2 natif partout) le problème n'existe pas.
const GL_ARGS = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']

const EXE = process.env.PW_CHROME ||
  '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const PHASE = process.env.PHASE || 'avant'
const MODE = process.env.MODE || 'dev'
const BASE = process.env.BASE_URL || 'http://localhost:8745/socle/'
const OUT = process.env.OUT || path.resolve('..', 'reports', 'maplibre1', `${PHASE}_${MODE}`)
const IDU = process.env.IDU || '97415000ER1296'          // Saint-Paul (témoin fiche)
const SP = [55.29, -21.02]                                // centre urbain Saint-Paul
const VIEW = { width: 1440, height: 900 }
const log = (...a) => console.log(`[ml1:${PHASE}:${MODE}]`, ...a)

const consoleErrors = []

async function newPage(browser) {
  const ctx = await browser.newContext({ viewport: VIEW, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  page.on('console', (m) => {
    if (m.type() === 'error') { const t = m.text(); consoleErrors.push(t); log('CONSOLE-ERR:', t.slice(0, 160)) }
  })
  page.on('pageerror', (e) => { consoleErrors.push('pageerror: ' + e.message); log('PAGE-ERR:', e.message.slice(0, 160)) })
  return page
}

async function ready(page) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
  await idle(page, 9000)
  await page.waitForTimeout(1800)   // laisse le plan tuyau + l'init des toggles se poser
}

function idle(page, ms = 8000) {
  return page.evaluate((ms) => new Promise((res) => {
    const m = window.__labuse_map
    if (!m) return res()
    let done = false
    const fin = () => { if (!done) { done = true; res() } }
    const t = setTimeout(fin, ms)
    m.once('idle', () => { clearTimeout(t); fin() })
  }), ms)
}

async function clickByText(page, text) {
  await page.evaluate((text) => {
    const btns = [...document.querySelectorAll('button')]
    const b = btns.find((x) => x.textContent?.trim() === text)
    if (b) b.click()
  }, text)
}

async function shot(page, name) {
  const file = path.join(OUT, `${name}.png`)
  await page.screenshot({ path: file })
  log('shot', name)
}

const SCENES = [
  ['01_ile_dark', async (page) => { /* défaut */ }],
  ['02_ile_ortho', async (page) => {
    await page.click('button[aria-label="Fond de plan"]')
    await page.waitForTimeout(250)
    await clickByText(page, 'Ortho IGN')
    await page.waitForTimeout(400)
    await page.keyboard.press('Escape').catch(() => {})
  }],
  ['03_stpaul_contours', async (page) => {
    await page.evaluate((c) => { window.__labuse_map.jumpTo({ center: c, zoom: 15 }); window.__labuse.toggleTuyau('courbes_niveau') }, SP)
  }],
  ['04_sup', async (page) => {
    await page.evaluate((c) => { window.__labuse_map.jumpTo({ center: c, zoom: 14 }); window.__labuse.toggleTuyau('sup') }, SP)
  }],
  ['05_icpe', async (page) => {
    await page.evaluate((c) => { window.__labuse_map.jumpTo({ center: c, zoom: 14 }); window.__labuse.toggleTuyau('icpe') }, SP)
  }],
  ['06_plu_calibre', async (page) => {
    await page.evaluate((c) => { window.__labuse_map.jumpTo({ center: c, zoom: 15 }); window.__labuse.toggleTuyau('zonage_parcelle') }, SP)
  }],
  ['07_erc', async (page) => {
    await page.evaluate((c) => { window.__labuse_map.jumpTo({ center: c, zoom: 13 }); window.__labuse.toggleTuyau('mesures_compensatoires') }, SP)
  }],
  ['08_reseaux', async (page) => {
    await page.evaluate((c) => {
      window.__labuse_map.jumpTo({ center: c, zoom: 13 })
      for (const k of ['ligne_ht', 'ligne_mt', 'pylone']) window.__labuse.toggleTuyau(k)
    }, SP)
  }],
  ['09_fiche_lisere', async (page) => {
    await page.evaluate((idu) => window.__labuse.select(idu), IDU)
    await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(() => log('⚠ fiche absente'))
    await page.waitForTimeout(1500)
  }],
  ['10_3d', async (page) => {
    await page.evaluate((c) => window.__labuse_map.jumpTo({ center: c, zoom: 16, pitch: 0, bearing: -18 }), SP)
    await page.click('button[aria-label="Relief 3D"]')
    await page.waitForTimeout(250)
    await page.click('[data-relief="bati"]').catch(() => {})
    await page.waitForTimeout(3500)   // setTerrain + easeTo pitch + fetch bâti BBOX
  }],
  ['11_mesure_distance', async (page) => {
    await page.evaluate((c) => window.__labuse_map.jumpTo({ center: c, zoom: 15 }), SP)
    await idle(page, 6000)
    await page.click('button[aria-label="Distance"]')
    await page.waitForTimeout(300)
    for (const [x, y] of [[560, 360], [760, 430], [700, 600]]) {
      await page.mouse.click(x, y)
      await page.waitForTimeout(400)
    }
    await page.waitForTimeout(800)
  }],
  ['12_remonter_temps', async (page) => {
    await page.evaluate((c) => { window.__labuse.setFlyTo({ center: c }); window.__labuse.setModule('temps') }, SP)
    await page.waitForTimeout(4000)   // deux cartes TimeMachine + fonds anciens IGN
  }],
]

async function captures(browser) {
  for (const [name, run] of SCENES) {
    let ok = false
    for (let attempt = 0; attempt < 2 && !ok; attempt++) {
      const page = await newPage(browser)
      try {
        await ready(page)
        await run(page)
        if (!name.startsWith('11') && !name.startsWith('12')) await idle(page, 8000)
        await page.waitForTimeout(1400)   // settle raster IGN
        await shot(page, name)
        ok = true
      } catch (e) {
        log('⚠ scène', name, `tentative ${attempt + 1} échec:`, String(e).slice(0, 140))
        if (attempt === 1) { try { await shot(page, name + '_ERR') } catch { /* noop */ } }
      } finally {
        await page.close()
      }
    }
  }
}

async function timed(page, fn) {
  const t0 = Date.now()
  await fn()
  await idle(page, 12000)
  return Date.now() - t0
}

async function speed(browser) {
  const runs = { ouverture_ile: [], zoom_stpaul: [], depl_5_z15: [], activ_3_couches: [], clic_fiche: [] }
  for (let r = 0; r < 3; r++) {
    const page = await newPage(browser)
    try {
      // ouverture île = goto → premier idle
      let t0 = Date.now()
      await page.goto(BASE, { waitUntil: 'domcontentloaded' })
      await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
      await idle(page, 12000)
      runs.ouverture_ile.push(Date.now() - t0)
      await page.waitForTimeout(1200)

      runs.zoom_stpaul.push(await timed(page, () => page.evaluate((c) => window.__labuse_map.jumpTo({ center: c, zoom: 15 }), SP)))

      runs.depl_5_z15.push(await timed(page, async () => {
        await page.evaluate(() => {
          const m = window.__labuse_map
          const offs = [[120, 0], [0, 120], [-120, 0], [0, -120], [90, 90]]
          let i = 0; const step = () => { if (i < offs.length) { m.panBy(offs[i], { duration: 0 }); i++; setTimeout(step, 50) } }
          step()
        })
        await page.waitForTimeout(400)
      }))

      runs.activ_3_couches.push(await timed(page, () => page.evaluate(() => {
        for (const k of ['sup', 'icpe', 'zonage_parcelle']) window.__labuse.toggleTuyau(k)
      })))

      let tf = Date.now()
      await page.evaluate((idu) => window.__labuse.select(idu), IDU)
      await page.waitForSelector('[data-fiche-idu]', { timeout: 15000 }).catch(() => {})
      runs.clic_fiche.push(Date.now() - tf)
    } catch (e) {
      log('⚠ speed run', r, 'échec:', String(e).slice(0, 160))
    } finally {
      await page.close()
    }
  }
  const median = (a) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : null }
  const out = {}
  for (const [k, v] of Object.entries(runs)) out[k] = { runs: v, median_ms: median(v) }
  return out
}

async function main() {
  await mkdir(OUT, { recursive: true })
  const browser = await chromium.launch({ headless: true, executablePath: EXE, args: GL_ARGS })
  try {
    await captures(browser)
    const sp = await speed(browser)
    await writeFile(path.join(OUT, '_speed.json'), JSON.stringify(sp, null, 2))
    await writeFile(path.join(OUT, '_console.json'), JSON.stringify({ errors: consoleErrors }, null, 2))
    log('SPEED', JSON.stringify(sp))
    log('CONSOLE ERRORS:', consoleErrors.length)
  } finally {
    await browser.close()
  }
  log('done →', OUT)
}

main().catch((e) => { console.error(e); process.exit(1) })
