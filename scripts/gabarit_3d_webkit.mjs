// GABARIT-3D-1 (pilote, étape 2 quinquies) — MESURES WebKit : chaque critère mesuré sur l'ouverture,
// chiffre donné ; un critère non atteint se dit. BZ1065, 1440×900 et 1280×720, coupe A et B, aperçu+détail.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-1/viewer'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://127.0.0.1:10090/socle/'
const IDU = '97411000BZ1065'
const browser = await webkit.launch()
const mesures = {}

async function ouvrir(page) {
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), IDU)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-canvas] canvas', { timeout: 20000 })
  await page.waitForFunction(() => window.__gab3d?.probe?.pf > 0, { timeout: 20000 }).catch(() => {})
}
// taille de texte min à l'écran + chevauchement, pour un <img> de coupe
async function mesureCoupe(page, sel) {
  const img = await page.$(sel); if (!img) return null
  const b = await img.boundingBox()
  const url = await img.evaluate((e) => e.src)
  const svg = await (await fetch(url)).text()
  const fonts = [...svg.matchAll(/font-size="([\d.]+)"/g)].map((m) => +m[1])
  const vb = +(svg.match(/viewBox="0 0 (\d+)/)?.[1] || 960)
  const scale = b.width / vb
  const minPx = Math.min(...fonts) * scale
  // chevauchement des cotes : <text ...>X,X m</text> ; positions x (px écran), même ligne ~ y
  const cotes = [...svg.matchAll(/<text x="([\d.]+)" y="([\d.]+)"[^>]*>[\d,]+ m<\/text>/g)].map((m) => ({ x: +m[1] * scale, y: +m[2] * scale }))
  let overlaps = 0
  for (let i = 0; i < cotes.length; i++) for (let j = i + 1; j < cotes.length; j++)
    if (Math.abs(cotes[i].x - cotes[j].x) < 22 && Math.abs(cotes[i].y - cotes[j].y) < 11) overlaps++
  return { largeur_img_px: Math.round(b.width), texte_min_px: Math.round(minPx * 10) / 10, n_cotes: cotes.length, chevauchements: overlaps }
}

async function parSize(w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'networkidle' }); await page.waitForFunction(() => window.__labuse != null, { timeout: 30000 })
  await ouvrir(page); await page.waitForTimeout(600)
  const scene = await (await fetch(`http://127.0.0.1:7290/outils/gabarit/scene/${IDU}`)).json()
  const m = { cadrage_parcelle_largeur_pct: 0, coupes: {} }
  // 1. cadrage : largeur projetée de la parcelle
  m.cadrage_parcelle_largeur_pct = Math.round((await page.evaluate(() => window.__gab3d.probe.pf)) * 1000) / 10
  // 2. contour : couverture — parcelle couverte à 100 % → contour continu (plein visible + pointillé caché)
  m.contour_couverture_pct = Math.round((scene.terrain?.couverture_parcelle ?? 0) * 100)
  // 4. coupes A et B, aperçu (bas) et détail (agrandir)
  for (const ax of ['A', 'B']) {
    await page.click(`text=Coupe ${ax}`).catch(() => {}); await page.waitForTimeout(500)
    const apercu = await mesureCoupe(page, '[data-gab3d-overlay] img[alt^="Coupe"]')
    await page.screenshot({ path: `${OUT}/mesure_${w}x${h}_coupe${ax}.png` })
    await page.click('[data-gab3d-agrandir]').catch(() => {}); await page.waitForTimeout(500)
    const detail = await mesureCoupe(page, '[data-gab3d-overlay] img[alt="Agrandie"]')
    if (ax === 'B') await page.screenshot({ path: `${OUT}/mesure_${w}x${h}_detailB.png` })
    await page.click('text=Revenir au terrain').catch(() => {}); await page.waitForTimeout(300)
    m.coupes[ax] = { apercu, detail }
  }
  // 5. survol de la coupe → écart entre le point survolé et le point montré en 3D (critère < 0,5 m)
  await page.click('text=Coupe B').catch(() => {}); await page.waitForTimeout(400)
  const imgB = await page.$('[data-gab3d-overlay] img[alt^="Coupe"]'); const b = await imgB.boundingBox()
  const svgB = await (await fetch(await imgB.evaluate((e) => e.src))).text()
  const x0 = +(svgB.match(/data-plot-x0="([\d.]+)"/)?.[1] || 58), x1 = +(svgB.match(/data-plot-x1="([\d.]+)"/)?.[1] || 900)
  const aB = scene.axes_plan.B, fr = 0.7
  const ex = aB.p0[0] + (aB.p1[0] - aB.p0[0]) * fr, ey = aB.p0[1] + (aB.p1[1] - aB.p0[1]) * fr
  const px = b.x + (x0 + (x1 - x0) * fr) / 960 * b.width
  await page.mouse.move(px, b.y + b.height * 0.5); await page.waitForTimeout(250)
  const mk = await page.evaluate(() => window.__gab3d.probe)
  m.rupture_marqueur_pose = mk.mon
  m.survol_ecart_m = mk.mon ? Math.round(Math.hypot(mk.mx - ex, mk.my - ey) * 100) / 100 : null
  // 6. parité : les img plan/coupe transmettent sid
  m.parite_sid = await page.evaluate(() => [...document.querySelectorAll('[data-gab3d-overlay] img')].some((i) => /[?&]sid=/.test(i.src)))
  // overflow à chaque taille
  m.rien_ne_depasse = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1 && document.documentElement.scrollHeight <= innerHeight + 1)
  await page.screenshot({ path: `${OUT}/mesure_${w}x${h}_ouvert.png` })
  await ctx.close()
  return m
}

mesures['1440x900'] = await parSize(1440, 900)
mesures['1280x720'] = await parSize(1280, 720)
fs.writeFileSync(`${OUT}/mesures_webkit.json`, JSON.stringify(mesures, null, 2))
console.log(JSON.stringify(mesures, null, 2))
await browser.close()
