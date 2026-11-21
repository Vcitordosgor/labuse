// GABARIT-3D-3 (LOT 5) — TEMPS D'OUVERTURE 3D (hors réseau) : scène préchauffée côté serveur, puis on
// mesure dans le navigateur le délai entre le clic « Vue 3D » et la PREMIÈRE image (window.__gab3d.first).
// C'est le coût du MAILLAGE 3D (three.js), pas la coupe ni le WMS. Rapporte aussi la maille 3D et le
// nombre de sommets réellement servis. Usage : node scripts/gabarit_3d3_ouverture.mjs <idu...>
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'

const URL = 'http://localhost:10090/socle/'
const API = 'http://127.0.0.1:7290'
const IDUS = process.argv.slice(2)
if (!IDUS.length) IDUS.push('97411000BZ1065', '97412000CI0073', '97421000BN0236', '97414000HI0401')

async function warm(idu) {
  const r = await fetch(`${API}/outils/gabarit/scene/${idu}`)
  if (!r.ok) return null
  const s = await r.json()
  const f = s?.terrain?.faces_parcelle || {}
  return { verts: (f.vertices || []).length, tris: (f.triangles || []).length,
           maille3d: s?.terrain?.maille_3d_m ?? s?.meta?.maille_3d_m ?? s?.meta?.maille_m,
           coupe: s?.meta?.maille_m }
}

const browser = await webkit.launch()
// préchauffe du PROCESS WebKit/WebGL (création du contexte GL, JIT) sur une 1ʳᵉ ouverture JETÉE : les mesures
// suivantes isolent le coût du MAILLAGE, pas l'initialisation du navigateur.
try {
  const w = await browser.newContext({ viewport: { width: 1440, height: 900 } }); const wp = await w.newPage()
  await wp.goto(URL, { waitUntil: 'domcontentloaded' })
  await wp.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await wp.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await wp.evaluate(() => window.__labuse.setModule('gabarit')); await wp.waitForTimeout(400)
  await wp.evaluate(() => window.__labuse.select('97415000DX0049'))
  await wp.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 25000 }); await wp.click('[data-gabarit-viewer-3d]')
  await wp.waitForFunction(() => !!window.__gab3d?.first, { timeout: 40000 }).catch(() => {})
  await w.close()
} catch { /* préchauffe best-effort */ }
console.log(`\n════ LOT 5 — temps d'ouverture 3D (clic → 1ʳᵉ image), hors réseau ════`)
console.log(`${'idu'.padStart(16)} ${'sommets'.padStart(8)} ${'tris'.padStart(8)} ${'maille3D'.padStart(8)} ${'ouverture'.padStart(9)}`)
for (const idu of IDUS) {
  const info = await warm(idu)
  if (!info) { console.log(`${idu.padStart(16)}  (scène indisponible)`); continue }
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
  const page = await ctx.newPage()
  let ms = null, cote = []
  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded' })
    await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
    await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
    await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(400)
    for (let essai = 0; essai < 2; essai++) {         // le bouton n'apparaît qu'une fois la parcelle chargée (flaky)
      await page.evaluate((i) => window.__labuse.select(i), idu)
      try { await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 25000 }); break }
      catch (e) { if (essai === 1) throw e; await page.waitForTimeout(1500) }
    }
    await page.evaluate(() => { delete window.__gab3d; window.__tclick = performance.now() })
    await page.click('[data-gabarit-viewer-3d]')
    ms = await page.waitForFunction(() => (window.__gab3d?.first ? window.__gab3d.first - window.__tclick : null),
                                    { timeout: 60000 }).then((h) => h.jsonValue())
    cote = await page.evaluate(() => [...document.querySelectorAll('div')].map((d) => d.textContent || '')
      .filter((t) => /^\d+(,\d)?\s?m$/.test(t.trim())).slice(0, 4))
  } catch { /* on rapporte KO sans arrêter le run */ }
  console.log(`${idu.padStart(16)} ${String(info.verts).padStart(8)} ${String(info.tris).padStart(8)} `
    + `${String(info.maille3d).padStart(8)} ${(ms == null ? 'KO/>60s' : Math.round(ms) + 'ms').padStart(9)}  cotes=${cote.join(' ')}`)
  await ctx.close()
}
await browser.close()
