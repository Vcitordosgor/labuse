// M30 — captures avant/après des écrans touchés (usage : node scripts/shot_m30.mjs <suffixe>)
// Écrans : popover filtres (items 2-3), liste filtrée declasse (3), fiche sans adresse (4),
// fiche AR2714 (6 DVF + 7a entrée sélection + 7b viabilisation), fiche AI1886 (5 délaissé).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const suffixe = process.argv[2] || 'apres'
const DIR = new URL('../../qa/m30/captures/', import.meta.url).pathname
mkdirSync(DIR, { recursive: true })
const out = (n) => `${DIR}${n}_${suffixe}.png`

const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 2 })

// 1 · popover « + Filtre » (théâtre retiré / groupe Déclassées)
await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
await p.waitForFunction(() => !!window.__labuse, null, { timeout: 15000 }).catch(() => {})
await p.waitForTimeout(1500)
await p.getByText('+ Filtre').first().click().catch(() => {})
await p.waitForTimeout(800)
await p.screenshot({ path: out('popover_filtres'), clip: { x: 0, y: 0, width: 820, height: 640 } })
console.log('shot popover')

// 2 · liste filtrée sur un tier de déclassement (lien partageable #f=1&tv=…)
await p.goto('http://localhost:5173/socle/#f=1&tv=declasse_bati_sature', { waitUntil: 'networkidle' })
await p.waitForTimeout(3500)
await p.screenshot({ path: out('liste_declasse_bati_sature'), fullPage: false })
console.log('shot liste declasse')

// 3-5 · fiches témoins
for (const [idu, nom] of [
  ['97416000ET2164', 'fiche_adresse_absente'],   // brûlante rang 25, aucune adresse BAN
  ['97409000AR2714', 'fiche_ar2714'],            // DVF tuile Marché + entrée sélection + viabilisation
  ['97407000AI1886', 'fiche_delaisse_ai1886'],   // 9 m² — délaissé, bilan non servi
]) {
  await p.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle' })
  await p.waitForFunction(() => !!window.__labuse, null, { timeout: 15000 }).catch(() => {})
  await p.evaluate((i) => { window.__labuse?.setView('cartes'); window.__labuse?.select(i) }, idu)
  await p.waitForSelector('[data-fiche-idu]', { timeout: 15000 })
  await p.waitForTimeout(2500)
  await p.locator('aside:has([data-fiche-idu])').first().screenshot({ path: out(nom) })
  console.log('shot', nom)
}
await b.close()
