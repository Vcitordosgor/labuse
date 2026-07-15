// Lot 0 repro — points 8 (entonnoir pourquoi), 10 (vue mer), 13 (équipements).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 860 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setCommune, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setCommune('Saint-Paul'))
await p.waitForTimeout(1500)
// afficher l'analyse (verdict) → la liste apparaît
const heroBtn = p.locator('[data-verdict-on]')
if (await heroBtn.count()) await heroBtn.click()
await p.waitForTimeout(1500)

// POINT 8 : ouvrir l'entonnoir « pourquoi ? » et observer clipping/scroll
const enton = p.locator('[data-entonnoir-btn]')
console.log('entonnoir présent:', await enton.count())
if (await enton.count()) {
  await enton.click()
  await p.waitForTimeout(1200)
  const pop = p.locator('[data-entonnoir-popover]')
  const box = await pop.boundingBox().catch(() => null)
  const vp = p.viewportSize()
  console.log('popover box:', JSON.stringify(box), 'viewport h:', vp.height)
  if (box) console.log('popover dépasse le bas du panneau ?', box.y + box.height > vp.height, '(bottom=', Math.round(box.y + box.height), ')')
  await p.screenshot({ path: `${OUT}/repro-8-entonnoir.png` })
  await p.keyboard.press('Escape')
}

// POINT 10 : vue mer en mode COMMUNE (couche activée)
await p.evaluate(() => { const s = window.__labuse; s.toggleLayer && s.toggleLayer('vue_mer') })
// pas d'API toggleLayer exposée ? on clique la couche dans le panneau
const vmToggle = p.locator('button:has-text("Vue mer")').first()
if (await vmToggle.count()) await vmToggle.click()
await p.waitForTimeout(1800)
await p.screenshot({ path: `${OUT}/repro-10-vuemer-commune.png` })

// POINT 13 : équipements (activer + zoomer)
const eqToggle = p.locator('button:has-text("Équipements")').first()
if (await eqToggle.count()) await eqToggle.click()
await p.waitForTimeout(2200)
await p.screenshot({ path: `${OUT}/repro-13-equipements.png` })

await b.close()
console.log('repro OK')
