// M52-L1 — captures écran réel de la carte VERDICT (lisibilité du score).
// Usage : LABEL=apres node capture.mjs   (API dev déjà lancée sur :8000)
// Écrit qa/m52/captures/L1_<label>_<idu>__(verdict|panel).png
import { chromium } from 'playwright'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const LABEL = process.env.LABEL || 'apres'
const BASE = process.env.BASE || 'http://127.0.0.1:8000'
const OUT = dirname(fileURLToPath(import.meta.url))
const ALL = [
  ['97418000AT2379', 'brulante_AT2379'],   // Sainte-Marie ×22,1 rang 7
  ['97416000EY1406', 'declasseB_EY1406'],   // Saint-Pierre ×13,2 bâti révélé
  ['97416000IL0307', 'ecartee_IL0307'],     // Saint-Pierre ×1,3
]
// IDUS=id1,id2 → ne capture que ceux-là (recapture ciblée après correction).
const only = (process.env.IDUS || '').split(',').map((s) => s.trim()).filter(Boolean)
const PARCELS = only.length ? ALL.filter(([idu]) => only.includes(idu)) : ALL

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const EXE = process.env.PW_EXE
  || '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell'
const browser = await chromium.launch({ executablePath: EXE })
const ctx = await browser.newContext({ viewport: { width: 1480, height: 1000 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()

for (const [idu, name] of PARCELS) {
  await page.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' })
  const box = page.locator('[data-omnibox]')
  await box.waitFor({ state: 'visible', timeout: 20000 })
  await box.fill(idu)
  await page.locator('button[aria-label="Lancer la recherche"]').click()
  // la fiche s'ouvre → attendre l'IDU rendu puis la carte verdict
  await page.locator(`[data-fiche-idu]`).first().waitFor({ state: 'visible', timeout: 20000 })
  await sleep(1200) // stabilisation (fetch score_v2 + rendu réglette)
  const panel = page.locator('aside.absolute.right-0.top-0').first()
  await panel.screenshot({ path: join(OUT, `L1_${LABEL}_${name}__panel.png`) })
  const card = page.locator('[data-verdict-card]').first()
  if (await card.count()) {
    await card.screenshot({ path: join(OUT, `L1_${LABEL}_${name}__verdict.png`) })
    console.log(`✓ ${LABEL} ${name} — panel + verdict`)
  } else {
    console.log(`✓ ${LABEL} ${name} — panel (pas de data-verdict-card)`)
  }
}

await browser.close()
