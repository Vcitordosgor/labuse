// FIX LOT 3 — B/C : 2 saisies (2 vs 8 bâtiments) → compteur + liste visiblement différents.
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 950 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setCommune('Saint-Denis'))
await p.evaluate(() => window.__labuse.setModule('programme'))
await p.waitForSelector('label:has-text("BÂTIMENTS") input', { timeout: 10000 })

async function runWith(bat, file) {
  const inp = p.locator('label:has-text("BÂTIMENTS") input')
  await inp.fill(String(bat))
  await p.locator('button:has-text("Trouver les parcelles")').click()
  await p.waitForSelector('[data-prog-count]', { timeout: 20000 })
  await p.waitForTimeout(800)
  const txt = (await p.locator('[data-prog-count]').innerText()).replace(/\s+/g, ' ')
  console.log(`bat=${bat} → ${txt}`)
  await p.locator('aside:has([data-prog-count])').first().screenshot({ path: `${OUT}/${file}` })
}
await runWith(2, 'fixBC-programme-2bat.png')
await runWith(8, 'fixBC-programme-8bat.png')
await b.close()
console.log('captures Lot3 OK')
