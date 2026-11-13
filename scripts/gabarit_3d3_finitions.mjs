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
    // 3) lettres d'axe du plan-clé — aucun chevauchement
    const planSrc = await page.evaluate(() => document.querySelector('[data-gab3d-plan]')?.src || '')
    const psvg = planSrc ? await (await fetch(planSrc)).text() : ''
    const lp = lettresPlan(psvg)
    let chevLettres = 0
    for (let i = 0; i < lp.length; i++) for (let j = i + 1; j < lp.length; j++) if (inter(lp[i], lp[j])) chevLettres++
    res[`${court}_${w}x${h}`] = { chevCoupe, planRatio: ratio, planRatioOk: ratio >= 0.66, chevLettres, nLabels: bl.length, nLettres: lp.length }
    await ctx.close()
  }
}
fs.writeFileSync(`${OUT}/finitions.json`, JSON.stringify(res, null, 2))
console.log('\n== finitions (coupe sans chevauchement · plan-clé ≥ 2/3 · lettres sans chevauchement) ==')
let okAll = true
for (const k of Object.keys(res)) {
  const r = res[k]; const ok = r.chevCoupe === 0 && r.planRatioOk && r.chevLettres === 0; okAll = okAll && ok
  console.log(`  ${k}: ${ok ? 'OK' : 'KO'} — coupe chevauch=${r.chevCoupe} · plan ${Math.round(r.planRatio * 100)}% (≥66) · lettres chevauch=${r.chevLettres}`)
}
console.log(okAll ? '\nTOUS OK' : '\nAU MOINS UN KO')
await browser.close()
