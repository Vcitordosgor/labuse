// GABARIT-3D-3 (finitions avant merge) — CONTRÔLES :
//  1) aucun libellé de la coupe ne chevauche un autre (boîtes opaques <rect/><text>) ;
//  2) le plan-clé occupe au moins les 2/3 de la hauteur disponible de son panneau ;
//  3) les lettres d'axe (A A′ B B′) du plan-clé ne se chevauchent pas.
// BZ1065 (élément couvert), CT0442 (nue), DX0049 (bâtie en pente), à 1440×694 et 1920×1080.
import { webkit } from '/tmp/pw-wk/node_modules/playwright/index.mjs'
import fs from 'node:fs'

const OUT = '/Users/openclaw/Desktop/labuse-3d/docs/audit-2026-11/gabarit-3d-3'
const URL = 'http://localhost:10090/socle/'
const CAS = [['BZ1065', '97411000BZ1065'], ['CT0442', '97413000CT0442'], ['DX0049', '97415000DX0049']]
const TAILLES = [[1440, 694], [1920, 1080]]
const browser = await webkit.launch()

async function ouvrir(page, idu) {
  await page.waitForFunction(() => window.__labuse?.setModule && window.__labuse?.select, { timeout: 20000 })
  await page.evaluate(() => document.querySelector('[data-cookie-consent]')?.remove())
  await page.evaluate(() => window.__labuse.setModule('gabarit')); await page.waitForTimeout(300)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('[data-gabarit-viewer-3d]', { timeout: 30000 })
  await page.click('[data-gabarit-viewer-3d]')
  await page.waitForSelector('[data-gab3d-legende]', { timeout: 60000 })
  await page.waitForTimeout(800)
}
const inter = (a, b) => !(a[2] < b[0] || a[0] > b[2] || a[3] < b[1] || a[1] > b[3])

function boitesCoupe(svg) {    // libellés à fond opaque : <rect x y width height .../><text>…</text>
  const out = []
  const re = /<rect x="([\-\d.]+)" y="([\-\d.]+)" width="([\d.]+)" height="([\d.]+)"[^>]*\/><text[^>]*>([^<]*)<\/text>/g
  let m
  while ((m = re.exec(svg))) { const x = +m[1], y = +m[2], w = +m[3], h = +m[4]; out.push([x, y, x + w, y + h, m[5]]) }
  return out
}
function lettresPlan(svg) {
  const out = []
  const re = /<text x="([\-\d.]+)" y="([\-\d.]+)"[^>]*font-size="(\d+)"[^>]*>([^<]*)<\/text>/g
  let m
  while ((m = re.exec(svg))) {
    const x = +m[1], y = +m[2], fs = +m[3], t = m[4]
    if (['A', 'A′', 'B', 'B′'].includes(t)) { const w = Math.max(t.length * fs * 0.56, 4); out.push([x - w / 2 - 2, y - fs, x + w / 2 + 2, y + 3, t]) }
  }
  return out
}
// la flèche du nord + « N » : région autour de (width-22, 30) dans le plan-clé
function nordPlan(svg) {
  const vb = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/); const w = vb ? +vb[1] : 210
  const nx = w - 22, ny = 30
  return [nx - 9, ny - 20, nx + 9, ny + 18]
}
// cotes d'altitude de la coupe (centre x, valeur) + échelle px/m lue sur les graduations de distance → le
// seuil « voisines » vaut EXACTEMENT 3 m sur l'axe (comme la règle serveur), pas un pourcentage approximatif.
function cotesCoupe(svg) {
  const out = []
  for (const b of boitesCoupe(svg)) { const mm = b[4].match(/^(\d+),(\d)\s?m$/); if (mm) out.push({ x: (b[0] + b[2]) / 2, v: +(`${mm[1]}.${mm[2]}`) }) }
  const ticks = [...svg.matchAll(/<text x="([\d.]+)" y="[\d.]+" text-anchor="middle" font-size="9.5"[^>]*>(\d+)<\/text>/g)]
    .map((m) => ({ x: +m[1], d: +m[2] }))
  let pxPerM = 10
  if (ticks.length >= 2) { const a = ticks[0], b = ticks[ticks.length - 1]; if (b.d !== a.d) pxPerM = Math.abs((b.x - a.x) / (b.d - a.d)) }
  return { out, seuilX: 3 * pxPerM }
}

const res = {}
for (const [court, idu] of CAS) {
  for (const [w, h] of TAILLES) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1.5 })
    const page = await ctx.newPage()
    await page.goto(URL, { waitUntil: 'domcontentloaded' })
    await ouvrir(page, idu)
    // 1) coupe — aucun chevauchement de libellés
    const coupeSrc = await page.evaluate(() => document.querySelector('[data-gab3d-coupe-band] img')?.src || '')
    const svg = coupeSrc ? await (await fetch(coupeSrc)).text() : ''
    const bl = boitesCoupe(svg)
    let chevCoupe = 0
    for (let i = 0; i < bl.length; i++) for (let j = i + 1; j < bl.length; j++) if (inter(bl[i], bl[j])) chevCoupe++
    // 2) plan-clé ≥ 2/3 de la hauteur du panneau
    const ratio = await page.evaluate(() => {
      const img = document.querySelector('[data-gab3d-plan]'); const panel = img?.closest('.flex.w-\\[320px\\]') || img?.parentElement?.parentElement
      if (!img || !panel) return 0
      return Math.round((img.getBoundingClientRect().height / panel.getBoundingClientRect().height) * 100) / 100
    })
    // 3) lettres d'axe du plan-clé — aucun chevauchement ENTRE ELLES ni avec la flèche du nord
    const planSrc = await page.evaluate(() => document.querySelector('[data-gab3d-plan]')?.src || '')
    const psvg = planSrc ? await (await fetch(planSrc)).text() : ''
    const lp = lettresPlan(psvg); const nord = nordPlan(psvg)
    let chevLettres = 0, lettreNord = 0
    for (let i = 0; i < lp.length; i++) { if (inter(lp[i], nord)) lettreNord++; for (let j = i + 1; j < lp.length; j++) if (inter(lp[i], lp[j])) chevLettres++ }
    // 4) pas deux cotes quasi identiques voisines (< ~3 m sur l'axe ET < 0,2 m d'altitude)
    const cc = cotesCoupe(svg); let cotesVoisines = 0
    for (let i = 0; i < cc.out.length; i++) for (let j = i + 1; j < cc.out.length; j++)
      if (Math.abs(cc.out[i].v - cc.out[j].v) < 0.2 && Math.abs(cc.out[i].x - cc.out[j].x) < cc.seuilX) cotesVoisines++
    res[`${court}_${w}x${h}`] = { chevCoupe, planRatio: ratio, planRatioOk: ratio >= 0.66, chevLettres, lettreNord, cotesVoisines }
    await ctx.close()
  }
}
fs.writeFileSync(`${OUT}/finitions.json`, JSON.stringify(res, null, 2))
console.log('\n== finitions (coupe sans chevauchement · plan-clé ≥ 2/3 · lettres sans chevauchement) ==')
let okAll = true
for (const k of Object.keys(res)) {
  const r = res[k]; const ok = r.chevCoupe === 0 && r.planRatioOk && r.chevLettres === 0 && r.lettreNord === 0 && r.cotesVoisines === 0; okAll = okAll && ok
  console.log(`  ${k}: ${ok ? 'OK' : 'KO'} — coupe chevauch=${r.chevCoupe} · plan ${Math.round(r.planRatio * 100)}% · lettres chevauch=${r.chevLettres} · lettre∩nord=${r.lettreNord} · cotes voisines=${r.cotesVoisines}`)
}
console.log(okAll ? '\nTOUS OK' : '\nAU MOINS UN KO')
await browser.close()
