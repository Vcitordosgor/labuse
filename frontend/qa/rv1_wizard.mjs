// RADAR-VEILLE-1 (R3) — les 4 étapes du wizard « Déposer une annonce » en admin (flag ON).
import { chromium } from 'playwright'
import fs from 'node:fs'
const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/RADAR-VEILLE-1/captures'
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1100 }, deviceScaleFactor: 2 })
const p = await ctx.newPage()
const report = { steps: {} }
const shot = async (n) => { await p.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log('shot', n) }
try {
  await p.goto(BASE + '#admin=1', { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('aside button', { timeout: 15000 }); await p.waitForTimeout(800)
  await p.locator('aside button', { hasText: 'Radar' }).first().click()
  await p.waitForSelector('[data-depot-agence]', { timeout: 10000 })
  const wiz = p.locator('[data-depot-agence]')
  await wiz.scrollIntoViewIfNeeded(); await shot('05-depot-etape1'); report.steps['1'] = true
  const html = fs.readFileSync('../qa/radar-terrains/T-possession.html', 'utf-8')
  await p.fill('[data-depot-html]', html)
  await p.click('[data-depot-analyser]')
  await p.waitForSelector('[data-depot-etape="2"]', { timeout: 20000 })
  await p.waitForTimeout(400); await wiz.scrollIntoViewIfNeeded(); await shot('06-depot-etape2'); report.steps['2'] = true
  await p.click('[data-depot-continuer-adresse]')
  await p.waitForSelector('[data-depot-etape="3"]', { timeout: 8000 })
  await p.fill('[data-depot-adresse]', '27 chemin Vidot, La Bretagne, 97490 Saint-Denis')
  await p.fill('[data-depot-agence-nom]', 'Agence Immo Transac')
  const idu = await ctx.request.get('http://127.0.0.1:8000/radar/biens?limit=80').then(r => r.json()).then(r => (r.biens || []).find(b => b.rattachement?.idu)?.rattachement?.idu).catch(() => null)
  report.idu = idu
  if (idu) { await p.fill('[data-depot-parcelle]', idu); await p.waitForTimeout(500); await p.press('[data-depot-parcelle]', 'Enter'); await p.waitForTimeout(500) }
  await p.waitForTimeout(400); await wiz.scrollIntoViewIfNeeded(); await shot('07-depot-etape3'); report.steps['3'] = true
  const enabled = await p.locator('[data-depot-publier]').isEnabled().catch(() => false)
  report.publier_enabled = enabled
  if (enabled) {
    await p.click('[data-depot-publier]')
    await p.waitForSelector('[data-depot-etape="4"]', { timeout: 8000 })
    await p.waitForTimeout(400); await wiz.scrollIntoViewIfNeeded(); await shot('08-depot-etape4'); report.steps['4'] = true
    report.publie = (await p.locator('[data-depot-etape="4"]').innerText()).slice(0, 160)
  }
} catch (e) { report.err = String(e).slice(0, 200) }
fs.writeFileSync(`${OUT}/_wizard_report.json`, JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
