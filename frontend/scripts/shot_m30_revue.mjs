// M30-revue — captures A2/A3 + 3 libellés arbitrés (usage : node scripts/shot_m30_revue.mjs <suffixe>)
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const suffixe = process.argv[2] || 'apres'
const DIR = new URL('../../qa/m30/captures_revue/', import.meta.url).pathname
mkdirSync(DIR, { recursive: true })
const out = (n) => `${DIR}${n}_${suffixe}.png`

const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })

// 1 · popover — libellés « fermée à l'urbanisation » / « inconstructible (géométrie) »
await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
await p.getByText('+ Filtre').first().click()
await p.waitForTimeout(800)
await p.screenshot({ path: out('popover_libelles'), clip: { x: 560, y: 0, width: 880, height: 900 } })
console.log('shot popover')

// 2 · légende zonage — libellé famille AU (couche « Zonage PLU (par parcelle) » allumée)
await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
await p.waitForTimeout(1500)
await p.getByText('Zonage PLU (par parcelle)').first().click().catch(() => {})
await p.waitForTimeout(1500)
await p.screenshot({ path: out('legende_zonage_au'), fullPage: false })
console.log('shot legende')

// 3-4 · fiches témoins A2 (tuile délaissé entière) + A3 (titres de tiroirs entiers)
for (const [idu, nom, waitTxt] of [
  ['97407000AI1886', 'fiche_ai1886', 'délaissé'],
  ['97409000AR2714', 'fiche_ar2714', 'DVF —'],
]) {
  await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
  await p.waitForFunction(() => !!window.__labuse, null, { timeout: 15000 }).catch(() => {})
  await p.evaluate((i) => { window.__labuse?.setView('cartes'); window.__labuse?.select(i) }, idu)
  await p.waitForSelector('[data-fiche-idu]', { timeout: 15000 })
  await p.waitForFunction((t) => document.body.innerText.includes(t), waitTxt, { timeout: 20000 }).catch(() => {})
  await p.waitForTimeout(1500)
  await p.locator('aside:has([data-fiche-idu])').first().screenshot({ path: out(nom) })
  console.log('shot', nom)
}
await b.close()
