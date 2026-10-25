// RECETTE-OUTILS-1 — bibliothèque de captures (Chrome système, build servi sous /socle/, proxy :6020).
import { chromium } from 'playwright'
import fs from 'node:fs'

export const BASE = process.env.RECETTE_BASE || 'http://localhost:6020/socle/'
export const OUT = 'reports/RECETTE-OUTILS-1/captures'
fs.mkdirSync(OUT, { recursive: true })

export async function launch() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
  const page = await ctx.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e)))
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })
  return { browser, ctx, page, errors }
}

export function mk(page) {
  return {
    async go(hash) { await page.goto(BASE + hash, { waitUntil: 'networkidle' }).catch(()=>{}); await page.waitForTimeout(800) },
    async shot(name) { await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false }); console.log('  shot', name) },
    async shotSel(sel, name) {
      const el = page.locator(sel).first()
      if (await el.count()) { await el.screenshot({ path: `${OUT}/${name}.png` }).catch(async()=>{ await page.screenshot({ path: `${OUT}/${name}.png` }) }); console.log('  shotSel', name) }
      else { await page.screenshot({ path: `${OUT}/${name}.png` }); console.log('  shotSel(fallback-full)', name) }
    },
    async wait(ms){ await page.waitForTimeout(ms) },
  }
}
