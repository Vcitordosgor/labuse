// RETOURS-19 — capture du SURVOL d'une barre d'accordéon Permis (chevron sans carré sombre sur le vert).
// PHASE=avant|apres. Lancer depuis frontend/ : CHROME=<exe> PHASE=apres node ../qa/retours19_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-19/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, hasTouch: false, isMobile: false })
const page = await ctx.newPage()
await page.goto(`${BASE}?r19#m=permis`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2500)

// on survole la barre « Affiner » (repliée → le chevron est visible) et on capture la barre.
const sel = '[data-permis-bloc-toggle="affiner"]'
const bar = await page.$(sel)
await bar.hover()
await page.waitForTimeout(500)
await bar.screenshot({ path: `${OUT}/chevron-survol-${SUFFIX}.png` })
console.log('shot chevron-survol', SUFFIX)

// contrôle : le fond de la barre est-il bien vert au survol (media hover:hover matché) ?
const bg = await page.evaluate((s) => {
  const el = document.querySelector(s)
  el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }))
  return getComputedStyle(el).backgroundColor
}, sel)
console.log('bar bg au survol =', bg)
await browser.close()
