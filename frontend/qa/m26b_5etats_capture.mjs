// M26-B · Point C — captures des 5 états sur RUNS RÉELS (SSE bout en bout).
// États 1/2 : même run (capture en vol puis à la fin). État 3 : brief vague → précision
// → reprise. État 4 : brief impossible → zéro honnête. État 5 : API relancée avec
// LABUSE_COPILOTE_QUOTA_JOUR=0 (voir m26b_etat5_capture.mjs, instance séparée).
// Usage : node qa/m26b_5etats_capture.mjs  (API :8000 dev mode + vite :5173)
import { chromium } from 'playwright'

const BASE = 'http://localhost:5173/socle/'
const OUT = 'qa/captures'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 3400 } })
p.on('console', (m) => { if (m.type() === 'error') console.log('console error:', m.text()) })

async function vueCopilote() {
  await p.goto(BASE, { waitUntil: 'domcontentloaded' })
  await p.waitForSelector('nav button')
  await p.evaluate(() => localStorage.clear())
  await p.click('nav button:has-text("Copilote")')
  await p.waitForSelector('[data-copilote]')
}

// ── états 2 puis 1 — un seul run réel ─────────────────────────────────────────
await vueCopilote()
await p.fill('[data-brief]', 'Terrain pour un collectif de 6 logements à Saint-Paul, budget foncier 480 k€, hors zone rouge PPR')
await p.click('[data-instruire]')
console.log('run états 2/1 lancé —', new Date().toISOString())
// état 2 : au moins un étage d'entonnoir atteint + une étape active au fil
await p.waitForSelector('[data-etage][data-etage-atteint]', { timeout: 60000 })
await p.waitForTimeout(600)
await p.screenshot({ path: `${OUT}/m26c-etat2-en-cours.png` })
console.log('état 2 capturé (fil vivant, entonnoir partiel)')
// état 1 : fin du run
await p.waitForSelector('[data-resultats]', { timeout: 180000 })
await p.waitForTimeout(400)
await p.screenshot({ path: `${OUT}/m26c-etat1-integral.png` })
const nonViables = await p.locator('[data-charge-flag="non-viable"]').count()
const flags = await p.locator('[data-charge-flag="au-dessus"]').count()
console.log(`état 1 capturé — restituées: ${await p.locator('[data-restituee]').count()},`,
  `au-dessus: ${flags}, non viables: ${nonViables}`)

// ── état 3 — précision demandée puis reprise ──────────────────────────────────
await vueCopilote()
await p.fill('[data-brief]', 'Je cherche un terrain pas trop cher pour faire du collectif')
await p.click('[data-instruire]')
console.log('run état 3 lancé')
await p.waitForSelector('[data-clarification]', { timeout: 90000 })
await p.waitForTimeout(400)
await p.screenshot({ path: `${OUT}/m26c-etat3-precision.png` })
console.log('état 3 capturé — question :',
  (await p.locator('[data-clarification] h3').textContent())?.trim())
// reprise : réponse par champ libre (commune + budget réalistes pour laisser le run finir)
await p.fill('[data-clarif-libre]', 'Saint-Paul, budget 480 k€, 6 logements')
await p.click('[data-clarif-reprendre]')
await p.waitForSelector('[data-fil-etape="interpretation"][data-etat="active"], [data-fil-etape][data-etat="active"]', { timeout: 30000 })
await p.screenshot({ path: `${OUT}/m26c-etat3-reprise.png` })
console.log('reprise capturée (le fil continue, même run)')

// ── état 4 — zéro retenue ─────────────────────────────────────────────────────
await vueCopilote()
await p.fill('[data-brief]', 'Terrain pour 300 logements à Cilaos, budget foncier 100 k€, hors PPR')
await p.click('[data-instruire]')
console.log('run état 4 lancé')
await p.waitForSelector('[data-zero], [data-resultats], [data-echec], [data-clarification]', { timeout: 180000 })
await p.waitForTimeout(400)
await p.screenshot({ path: `${OUT}/m26c-etat4-zero.png` })
const zero = await p.locator('[data-zero]').count()
const relances = await p.locator('[data-relance]').allTextContents()
console.log(`état 4 capturé — panneau zéro: ${zero > 0}, relances: ${relances.join(' | ')}`)

await b.close()
