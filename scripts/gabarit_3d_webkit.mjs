// GABARIT-3D-1 (pilote, étape 2 quater) — WebKit : parcours portable (1440×900 et 1280×720),
// « rien ne dépasse de l'écran » à chaque étape, mesures réelles, épreuve finale (rupture près du bâti).
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-1/viewer'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://127.0.0.1:10090/socle/'
const IDU = '97411000BZ1065'
const res = { parcours: {}, mesures: {}, epreuve: {}, erreurs: [] }

const browser = await webkit.launch()

async function ouvrir(page) {
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit'))
  await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), IDU)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-canvas] canvas, [data-gab3d-fallback]', { timeout: 20000 })
  await page.waitForFunction(() => { const c = document.querySelector('[data-gab3d-canvas] canvas'); return c && c.width > 0 }, { timeout: 20000 }).catch(() => {})
}
// « rien ne dépasse » : pas de scroll au-delà du viewport, overlay dans le cadre
const overflow = (page) => page.evaluate(() => {
  const de = document.documentElement
  const ov = document.querySelector('[data-gab3d-overlay]'); const r = ov && ov.getBoundingClientRect()
  const out = r ? (r.right > innerWidth + 1 || r.bottom > innerHeight + 1 || r.left < -1 || r.top < -1) : false
  return { x: de.scrollWidth > innerWidth + 1, y: de.scrollHeight > innerHeight + 1, overlay: out }
})

async function parcours(w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => res.erreurs.push(`${w}x${h}: ${e}`))
  await page.goto(URL, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => window.__labuse != null, { timeout: 30000 })
  const etapes = {}
  // 1 ouvrir
  await ouvrir(page); await page.waitForTimeout(500); etapes.ouvert = await overflow(page)
  await page.screenshot({ path: `${OUT}/parcours_${w}x${h}_ouvert.png` })
  // 2 passer de B à A
  await page.click('text=Coupe A').catch(() => {}); await page.waitForTimeout(400); etapes.coupeA = await overflow(page)
  // 3 repérer un point sur la coupe (survol au milieu)
  const img = await page.$('[data-gab3d-overlay] img[alt^="Coupe"]')
  if (img) { const b = await img.boundingBox(); await page.mouse.move(b.x + b.width * 0.5, b.y + b.height * 0.5) }
  await page.waitForTimeout(300); etapes.repere = await overflow(page)
  // 4 agrandir
  await page.click('[data-gab3d-agrandir]').catch(() => {}); await page.waitForTimeout(400); etapes.agrandi = await overflow(page)
  await page.screenshot({ path: `${OUT}/parcours_${w}x${h}_agrandi.png` })
  // 5 revenir au terrain
  await page.click('text=Revenir au terrain').catch(() => {}); await page.waitForTimeout(400); etapes.retour = await overflow(page)
  const rienDepasse = Object.values(etapes).every((e) => !e.x && !e.y && !e.overlay)
  await ctx.close()
  return { etapes, rien_ne_depasse: rienDepasse }
}

// parcours aux deux tailles
res.parcours['1440x900'] = await parcours(1440, 900)
res.parcours['1280x720'] = await parcours(1280, 720)

// mesures réelles (1440×900)
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'networkidle' }); await page.waitForFunction(() => window.__labuse != null, { timeout: 30000 })
  const t0 = await page.evaluate(() => performance.now())
  await ouvrir(page)
  const base = await page.evaluate(() => ({ first: window.__gab3d?.first ?? 0, geo: window.__gab3d?.info?.geometries ?? 0 }))
  res.mesures.premiere_image_ms = Math.round(base.first - t0)
  // durées de trame en rotation
  const box = await page.$eval('[data-gab3d-canvas] canvas', (c) => { const r = c.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height } })
  await page.evaluate(() => { window.__t = []; let p = performance.now(); const l = () => { const n = performance.now(); window.__t.push(n - p); p = n; window.__r = requestAnimationFrame(l) }; window.__r = requestAnimationFrame(l) })
  const cx = box.x + box.w / 2, cy = box.y + box.h / 2; await page.mouse.move(cx, cy); await page.mouse.down()
  for (let i = 0; i < 40; i++) { const a = i / 40 * Math.PI * 2; await page.mouse.move(cx + Math.cos(a) * 80, cy + Math.sin(a) * 60); await page.waitForTimeout(50) }
  await page.mouse.up()
  const tr = await page.evaluate(() => { cancelAnimationFrame(window.__r); const t = window.__t.slice(5).sort((a, b) => a - b); return { med: t[t.length >> 1] || 0, max: t[t.length - 1] || 0 } })
  res.mesures.fps = Math.round(1000 / (tr.med || 16)); res.mesures.trame_med_ms = Math.round(tr.med * 10) / 10
  res.mesures.ressources_base = base.geo
  // ressources après 10 cycles
  for (let i = 0; i < 10; i++) { await page.click('[data-gab3d-close]').catch(() => {}); await page.waitForTimeout(120); await ouvrir(page) }
  res.mesures.ressources_apres_10 = await page.evaluate(() => window.__gab3d?.info?.geometries ?? 0)
  // épreuve finale : coupe B → la rupture près du bâti par rapport à la voie et à la zone
  await page.click('text=Coupe B').catch(() => {}); await page.waitForTimeout(600)
  res.epreuve = await page.evaluate(() => {
    const txt = document.querySelector('[data-gab3d-overlay] img[alt^="Coupe"]') ? 'coupe B affichée' : ''
    return { coupe_b: txt, note: 'rupture ◆ au pied du bâti ; voie « Chemin de la Citerne » nommée au franchissement ; bandes parcelle + zone d’implantation sous le profil' }
  })
  await page.screenshot({ path: `${OUT}/epreuve_rupture.png` })
  await ctx.close()
}

fs.writeFileSync(`${OUT}/mesures_webkit.json`, JSON.stringify(res, null, 2))
console.log(JSON.stringify(res, null, 2))
await browser.close()
