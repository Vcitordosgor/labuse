// GABARIT-3D-1 (pilote, étape 3) — MESURES WebKit : chaque critère mesuré sur l'ouverture, chiffre donné ;
// un critère non atteint se dit. BZ1065 et CM1658, 1440×900 et 1280×720, coupe A et B, aperçu+détail,
// RELIEF puis PHOTO aérienne. Sorties : viewer/mesures_webkit.json + captures viewer/mesure_*.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-1/viewer'
fs.mkdirSync(OUT, { recursive: true })
const URL = 'http://127.0.0.1:10090/socle/'
const API = 'http://127.0.0.1:7290'
const IDUS = [['BZ1065', '97411000BZ1065'], ['CM1658', '97415000CM1658']]
const browser = await webkit.launch()
const mesures = {}

async function ouvrir(page, idu) {
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(250)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 15000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-canvas] canvas', { timeout: 20000 })
  await page.waitForFunction(() => window.__gab3d?.probe?.pf > 0, { timeout: 20000 }).catch(() => {})
}

// taille de texte min à l'écran (échelle object-contain RÉELLE) + chevauchement des cotes + remplissage du
// bandeau. `bandSel` (facultatif) : conteneur dont on mesure le remplissage par le contenu de la coupe.
async function mesureCoupe(page, sel, bandSel) {
  const img = await page.$(sel); if (!img) return null
  const b = await img.boundingBox()
  const url = await img.evaluate((e) => e.src)
  const svg = await (await fetch(url)).text()
  const fonts = [...svg.matchAll(/font-size="([\d.]+)"/g)].map((m) => +m[1])
  const vbm = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/); const vbW = +(vbm?.[1] || 960), vbH = +(vbm?.[2] || 520)
  const scale = Math.min(b.width / vbW, b.height / vbH)                 // object-contain : la plus petite échelle
  const minPx = Math.min(...fonts) * scale
  const contentW = vbW * scale, contentH = vbH * scale
  const cotes = [...svg.matchAll(/<text x="([\d.]+)" y="([\d.]+)"[^>]*>[\d,]+ m<\/text>/g)].map((m) => ({ x: +m[1] * scale, y: +m[2] * scale }))
  let overlaps = 0
  for (let i = 0; i < cotes.length; i++) for (let j = i + 1; j < cotes.length; j++)
    if (Math.abs(cotes[i].x - cotes[j].x) < 22 && Math.abs(cotes[i].y - cotes[j].y) < 11) overlaps++
  const out = { contenu_px: [Math.round(contentW), Math.round(contentH)], texte_min_px: Math.round(minPx * 10) / 10, n_cotes: cotes.length, chevauchements: overlaps }
  if (bandSel) {
    const band = await page.$(bandSel)
    if (band) { const bc = await band.boundingBox(); const bw = bc.width - 16, bh = bc.height - 16   // p-2
      out.remplissage_pct = Math.round(Math.max(contentW / bw, contentH / bh) * 1000) / 10 }
  }
  return out
}
// lisibilité d'un <img> SVG (plan-clé, légende) : plus petit texte à l'écran (échelle object-contain)
async function minTextePx(page, sel) {
  const img = await page.$(sel); if (!img) return null
  const b = await img.boundingBox(); if (!b) return null
  const svg = await (await fetch(await img.evaluate((e) => e.src))).text()
  const fonts = [...svg.matchAll(/font-size="([\d.]+)"/g)].map((m) => +m[1]); if (!fonts.length) return null
  const vbm = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/); const vbW = +(vbm?.[1] || 380), vbH = +(vbm?.[2] || 320)
  return Math.round(Math.min(...fonts) * Math.min(b.width / vbW, b.height / vbH) * 10) / 10
}

// lettres de l'axe (B/B′, A/A′) DANS la vue : centre du libellé à l'intérieur du cadre du canvas 3D
// (l'ancien contrôle width>0 comptait un libellé posé HORS écran comme « visible » → le bug non vu).
async function lettresAxe(page) {
  return page.evaluate(() => {
    const cv = document.querySelector('[data-gab3d-canvas]'); if (!cv) return []
    const r = cv.getBoundingClientRect()
    return [...cv.querySelectorAll('div')]
      .filter((d) => /^[AB]′?$/.test((d.textContent || '').trim()) && d.style.display !== 'none')
      .map((d) => { const b = d.getBoundingClientRect(), cx = b.x + b.width / 2, cy = b.y + b.height / 2
        return { t: d.textContent.trim(), dansLaVue: cx >= r.x && cx <= r.x + r.width && cy >= r.y && cy <= r.y + r.height } })
  })
}

// A2 — aucun libellé traversé par un trait : les boîtes de fond (rx="2") sont émises APRÈS tous les traits
// (<line>/<polyline>/<polygon>/<path>) → dessinées PAR-DESSUS, rien ne les traverse.
function a2Control(svg) {
  const lastStroke = Math.max(svg.lastIndexOf('<line'), svg.lastIndexOf('<polyline'), svg.lastIndexOf('<polygon'), svg.lastIndexOf('<path'))
  const rects = [...svg.matchAll(/<rect [^>]*rx="2"/g)].map((m) => m.index)
  return { libelles_proteges: rects.length, traits_au_travers: rects.filter((i) => i < lastStroke).length }
}
// bornes (d) des bandes parcelle/zone portées en attribut → comparables aperçu ↔ détail
function bandeBornes(svg) {
  return [...svg.matchAll(/data-band="([^"]+)" data-d0="([\d.]+)" data-d1="([\d.]+)"/g)]
    .map((m) => `${m[1]}:${(+m[2]).toFixed(2)}-${(+m[3]).toFixed(2)}`).sort()
}
// 3 ter — les LONGUEURS de bande (« 9,3 m »…) ne doivent JAMAIS croiser les graduations de distance
// (« 40 », « 80 ») : bug « 4020,2 m » / « 33,4 m80 » que l'ancien contrôle (rx="2" seulement) n'a pas vu.
function bandeGradControl(svg) {
  const T = [...svg.matchAll(/<text x="([\d.-]+)" y="([\d.-]+)" text-anchor="middle" font-size="([\d.]+)"[^>]*>([^<]+)<\/text>/g)]
    .map((m) => ({ x: +m[1], y: +m[2], fs: +m[3], t: m[4] }))
  const grads = T.filter((e) => e.fs === 9.5 && /^\d+$/.test(e.t))            // graduations de distance
  if (!grads.length) return { graduations: 0, longueurs: 0, chevauchements: 0 }
  const gy = Math.max(...grads.map((g) => g.y))
  const lens = T.filter((e) => Math.abs(e.fs - 9) < 0.01 && /^[\d,]+ m$/.test(e.t) && e.y > gy - 2)  // longueurs de bande
  const bb = (e) => { const w = e.t.length * e.fs * 0.55; return { x0: e.x - w / 2, x1: e.x + w / 2, y0: e.y - e.fs, y1: e.y + 2 } }
  let n = 0
  for (const g of grads) for (const l of lens) { const a = bb(g), b = bb(l); if (a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1) n++ }
  return { graduations: grads.length, longueurs: lens.length, chevauchements: n }
}
// pt 4 — AUCUNE étiquette (boîte rx="2") sur la COURBE : segment du terrain / du profil sous bâti ∩ boîte ?
function segCoupeRect([ax, ay], [bx, by], r) {       // Liang-Barsky : le segment traverse-t-il le rectangle ?
  let t0 = 0, t1 = 1; const dx = bx - ax, dy = by - ay
  const p = [-dx, dx, -dy, dy], q = [ax - r.x, r.x + r.w - ax, ay - r.y, r.y + r.h - ay]
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) { if (q[i] < 0) return false }
    else { const t = q[i] / p[i]; if (p[i] < 0) { if (t > t1) return false; if (t > t0) t0 = t } else { if (t < t0) return false; if (t < t1) t1 = t } }
  }
  return t0 <= t1
}
function etiquettesSurCourbe(svg) {
  const segs = []
  for (const m of svg.matchAll(/<polyline points="([^"]+)" fill="none"[^>]*stroke-width="(?:1\.8|2\.2)"/g)) {   // terrain + profil sous bâti
    const pts = m[1].trim().split(/\s+/).map((s) => s.split(',').map(Number))
    for (let i = 0; i < pts.length - 1; i++) segs.push([pts[i], pts[i + 1]])
  }
  const boxes = [...svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.]+)" height="([\d.]+)" rx="2"/g)]
    .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }))
  return { boites: boxes.length, segments: segs.length, sur_courbe: boxes.filter((b) => segs.some((s) => segCoupeRect(s[0], s[1], b))).length }
}
// chevauchement des libellés à fond opaque (rupture, emprise bâtie, voie, pente max) : rects rx="2"
function labelsChevauchent(svg) {
  const r = [...svg.matchAll(/<rect x="([\d.-]+)" y="([\d.-]+)" width="([\d.]+)" height="([\d.]+)" rx="2"/g)]
    .map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }))
  let n = 0
  for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) {
    const a = r[i], b = r[j]
    if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) n++
  }
  return { boites: r.length, chevauchements: n }
}

// altitude du profil à partir des graduations gauches du SVG : étiquettes d'altitude posées à x=off_x-6
// (text-anchor end) avec y = Y(z)+3 → on retient x STRICTEMENT à gauche du tracé (exclut le « 0 » des
// distances, posé à x=off_x). Y_plot = y_texte − 3 ; interpolation linéaire (y_plot, z).
function altFromGrads(svg, off_x) {
  const g = [...svg.matchAll(/<text x="([\d.]+)" y="([\d.]+)"[^>]*>(\d+)<\/text>/g)]
    .map((m) => ({ x: +m[1], y: +m[2] - 3, z: +m[3] })).filter((t) => t.x < off_x - 3)
  if (g.length < 2) return null
  const a = g[0], b = g[g.length - 1]
  const dz = (b.z - a.z) / (b.y - a.y)
  return (yplot) => a.z + (yplot - a.y) * dz
}

async function parSize(idu, w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
  const page = await ctx.newPage()
  await page.goto(URL, { waitUntil: 'domcontentloaded' }); await page.waitForFunction(() => window.__labuse != null, { timeout: 30000 })
  await ouvrir(page, idu); await page.waitForTimeout(700)
  const scene = await (await fetch(`${API}/outils/gabarit/scene/${idu}`)).json()
  const m = { cadrage_parcelle_largeur_pct: 0, coupes: {} }
  m.cadrage_parcelle_largeur_pct = Math.round((await page.evaluate(() => window.__gab3d.probe.pf)) * 1000) / 10
  m.contour_couverture_pct = Math.round((scene.terrain?.couverture_parcelle ?? 0) * 100)
  // A1 — audit de la zone d'implantation (pixels verts dedans / dehors)
  m.zone = await page.evaluate(() => window.__gab3dZoneAudit ? window.__gab3dZoneAudit() : { zone: false })
  // lettres de l'axe actif (B/B′, A/A′) DANS la vue à l'ouverture (coupe B par défaut)
  m.lettres_axe = await lettresAxe(page)
  // pt 2 — tout le contour + B/B′ dans le cadre, à l'OUVERTURE puis au RECENTRER
  m.cadre_ouverture = await page.evaluate(() => window.__gab3d?.probe?.cadre === true)
  await page.click('[data-gab3d-recentrer]').catch(() => {}); await page.waitForTimeout(400)
  m.cadre_recentrer = await page.evaluate(() => window.__gab3d?.probe?.cadre === true)
  // pt 1 — « Agrandir la coupe » ne recouvre ni le titre ni le datum (bandeau HTML), et le datum n'est PLUS dans le SVG
  m.agrandir = await page.evaluate(() => {
    const re = (s) => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null }
    const b = re('[data-gab3d-agrandir]'), t = re('[data-gab3d-coupe-titre]'), d = re('[data-gab3d-coupe-datum]')
    const ov = (a, c) => a && c && a.width > 0 && c.width > 0 && a.x < c.x + c.width && c.x < a.x + a.width && a.y < c.y + c.height && c.y < a.y + a.height
    return { recouvre_titre: ov(b, t), recouvre_datum: ov(b, d) }
  })
  // 4. coupes A et B, aperçu (bas) + détail (agrandir) : A2 (non traversé), bandes (mêmes bornes), chevauchements
  for (const ax of ['A', 'B']) {
    await page.click(`text=Coupe ${ax}`).catch(() => {}); await page.waitForTimeout(500)
    const lettres = await lettresAxe(page)   // lettres de l'axe de CETTE coupe (A/A′ ou B/B′), dans la vue
    const apImg = await page.$('[data-gab3d-overlay] img[alt^="Coupe"]')
    const apSvg = apImg ? await (await fetch(await apImg.evaluate((e) => e.src))).text() : ''
    const apercu = await mesureCoupe(page, '[data-gab3d-overlay] img[alt^="Coupe"]', '[data-gab3d-coupe-band]')
    if (apercu) { apercu.libelles = a2Control(apSvg); apercu.labels = labelsChevauchent(apSvg); apercu.bande_grad = bandeGradControl(apSvg); apercu.sur_courbe = etiquettesSurCourbe(apSvg); apercu.datum_dans_svg = /Altitudes en m/.test(apSvg) }
    await page.screenshot({ path: `${OUT}/mesure_${idu.slice(-6)}_${w}x${h}_coupe${ax}.png` })
    await page.click('[data-gab3d-agrandir]').catch(() => {}); await page.waitForTimeout(500)
    const detImg = await page.$('[data-gab3d-overlay] img[alt="Agrandie"]')
    const detSvg = detImg ? await (await fetch(await detImg.evaluate((e) => e.src))).text() : ''
    const detail = await mesureCoupe(page, '[data-gab3d-overlay] img[alt="Agrandie"]')
    if (detail) { detail.labels = labelsChevauchent(detSvg); detail.bande_grad = bandeGradControl(detSvg) }
    if (ax === 'B') await page.screenshot({ path: `${OUT}/mesure_${idu.slice(-6)}_${w}x${h}_detailB.png` })
    await page.click('text=Revenir au terrain').catch(() => {}); await page.waitForTimeout(300)
    const ba = bandeBornes(apSvg), bd = bandeBornes(detSvg)
    m.coupes[ax] = { apercu, detail, lettres, bandes_apercu: ba, bandes_bornes_identiques: ba.length > 0 && JSON.stringify(ba) === JSON.stringify(bd) }
  }
  // plan-clé + légende lisibles à cette taille (plus petit texte à l'écran)
  m.plan_texte_min_px = await minTextePx(page, '[data-gab3d-plan]')
  m.legende_px = await page.evaluate(() => { const e = document.querySelector('[data-gab3d-legende]'); return e ? Math.round(parseFloat(getComputedStyle(e).fontSize) * 10) / 10 : null })
  // A3 — on PART du losange ◆ affiché sur la coupe (B si elle en porte un, sinon A) : survol à son x → le
  // repère tombe sur le terrain. Écart = |altitude du marqueur drapé (maillage 3D) − altitude du losange
  // (profil serveur)|, deux pipelines distincts au MÊME endroit → critère < 0,5 m.
  m.survol = { marqueur_pose: false, note: 'aucun losange sur les coupes' }
  for (const ax of ['B', 'A']) {
    await page.click(`text=Coupe ${ax}`).catch(() => {}); await page.waitForTimeout(450)
    const img = await page.$('[data-gab3d-overlay] img[alt^="Coupe"]'); const bb = await img.boundingBox()
    const svg = await (await fetch(await img.evaluate((e) => e.src))).text()
    const x0 = +(svg.match(/data-plot-x0="([\d.]+)"/)?.[1] || 58), x1 = +(svg.match(/data-plot-x1="([\d.]+)"/)?.[1] || 900)
    const los = svg.match(/<path d="M([\d.]+),([\d.-]+) l4,4 l-4,4 l-4,-4 z"/)
    if (!los) continue
    const lx = +los[1], ly = +los[2] + 4   // centre du losange (x plan, Y plot)
    const alt = altFromGrads(svg, x0); const zLos = alt ? alt(ly) : null
    // point d'axe VISÉ par le losange (plan) : fraction = (x_losange − x0)/(x1 − x0)
    const a = scene.axes_plan[ax], frLos = (lx - x0) / (x1 - x0)
    const ex = a.p0[0] + (a.p1[0] - a.p0[0]) * frLos, ey = a.p0[1] + (a.p1[1] - a.p0[1]) * frLos
    // position RÉELLE du losange à l'écran (object-contain → letterbox ; dims = viewBox, pas naturalWidth WebKit)
    const vb = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/)
    const nw = +vb[1], nh = +vb[2]
    const scl = Math.min(bb.width / nw, bb.height / nh), drawnW = nw * scl, offX = (bb.width - drawnW) / 2
    const drawnH = nh * scl, offY = (bb.height - drawnH) / 2
    const px = bb.x + offX + (lx / nw) * drawnW
    await page.mouse.move(px - 1, bb.y + offY + drawnH * 0.5); await page.mouse.move(px, bb.y + offY + drawnH * 0.5); await page.waitForTimeout(250)
    const mk = await page.evaluate(() => window.__gab3d.probe)
    m.survol = {
      coupe: ax, marqueur_pose: mk.mon,
      // ÉCART HORIZONTAL : où le repère tombe sur le terrain vs l'endroit visé par le losange (« le même endroit »)
      ecart_m: mk.mon ? Math.round(Math.hypot(mk.mx - ex, mk.my - ey) * 100) / 100 : null,
      alt_marqueur_3d_m: mk.mon ? Math.round(mk.mz * 100) / 100 : null,
      alt_losange_coupe_m: zLos != null ? Math.round(zLos * 100) / 100 : null,
      ecart_altitude_m: (mk.mon && zLos != null) ? Math.round(Math.abs(mk.mz - zLos) * 100) / 100 : null,
    }
    break
  }
  m.parite_sid = await page.evaluate(() => [...document.querySelectorAll('[data-gab3d-overlay] img')].some((i) => /[?&]sid=/.test(i.src)))
  m.rien_ne_depasse = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1 && document.documentElement.scrollHeight <= innerHeight + 1)
  await page.screenshot({ path: `${OUT}/mesure_${idu.slice(-6)}_${w}x${h}_relief.png` })

  // B — PHOTO aérienne (si le bouton existe) : chargée au clic, drapée, overlays préservés.
  const photoBtn = await page.$('[data-gab3d-photo]')
  if (photoBtn) {
    const t0 = Date.now()
    await photoBtn.click()
    const ok = await page.waitForFunction(() => window.__gab3d?.photo === 'ok' || window.__gab3d?.photo === 'echec', { timeout: 6000 }).then(() => true).catch(() => false)
    const etat = await page.evaluate(() => window.__gab3d?.photo || 'inconnu')
    m.photo = {
      etat, delai_ms: Date.now() - t0,
      credit_ign: await page.evaluate(() => /©\s*IGN/i.test(document.querySelector('[data-gab3d-credit]')?.textContent || '')),
      millesime: await page.evaluate(() => document.querySelector('[data-gab3d-credit]')?.textContent?.match(/\b(19|20)\d{2}\b/)?.[0] || null),
      proxy_serveur: await page.evaluate(() => performance.getEntriesByType('resource').some((r) => /\/outils\/gabarit\/.*ortho/i.test(r.name)) && !performance.getEntriesByType('resource').some((r) => /geopf\.fr|ign\.fr/i.test(r.name))),
    }
    if (ok && etat === 'ok') await page.screenshot({ path: `${OUT}/mesure_${idu.slice(-6)}_${w}x${h}_photo.png` })
  }
  await ctx.close()
  return m
}

const TAILLES = [[1280, 720], [1440, 694], [1440, 900], [1920, 1080], [2560, 1300]]
for (const [court, idu] of IDUS) {
  mesures[court] = {}
  for (const [w, h] of TAILLES) mesures[court][`${w}x${h}`] = await parSize(idu, w, h)
}
fs.writeFileSync(`${OUT}/mesures_webkit.json`, JSON.stringify(mesures, null, 2))
console.log(JSON.stringify(mesures, null, 2))
await browser.close()
