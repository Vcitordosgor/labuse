// FIX FINITIONS — preuves A (libellés zonage), B (entonnoir inline), C (vue mer), D (équipements).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 800 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setCommune, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setCommune('Saint-Paul'))
await p.waitForTimeout(1500)

// A : libellés zonage clarifiés (panneau COUCHES)
await p.screenshot({ path: `${OUT}/fin-A-zonage-labels.png`, clip: { x: 0, y: 60, width: 320, height: 300 } })
console.log('A zones officielles présent:', await p.locator('text=Zonage PLU (zones officielles)').count())
console.log('A par parcelle présent:', await p.locator('text=Zonage PLU (par parcelle)').count())

// B : afficher l'analyse puis ouvrir l'entonnoir « pourquoi ? » → inline, lisible, liste scrollable
const hero = p.locator('[data-verdict-on]'); if (await hero.count()) await hero.click()
await p.waitForTimeout(1200)
await p.locator('[data-entonnoir-btn]').click()
await p.waitForSelector('[data-entonnoir-panel]', { timeout: 5000 })
await p.waitForTimeout(800)
const panel = await p.locator('[data-entonnoir-panel]').boundingBox()
// la liste des résultats est-elle présente ET sous le panneau (donc atteignable en scrollant) ?
const listBox = await p.locator('[data-results-scroll]').boundingBox()
console.log('B entonnoir panel bottom:', Math.round(panel.y + panel.height), '· liste résultats présente:', !!listBox)
await p.screenshot({ path: `${OUT}/fin-B-entonnoir-inline.png`, clip: { x: 0, y: 0, width: 320, height: 800 } })
// vérifier qu'on peut scroller la liste des parcelles avec l'explication ouverte
await p.locator('[data-results-scroll]').evaluate((el) => el.scrollBy(0, 300)).catch(() => {})
await p.waitForTimeout(400)
await p.locator('[data-entonnoir-btn]').click() // refermer

// C : vue mer — activer la couche, zoomer sur la côte
await p.locator('button:has-text("Vue mer")').first().click()
await p.waitForTimeout(600)
for (let i = 0; i < 3; i++) { await p.locator('button[title="Zoomer"]').click(); await p.waitForTimeout(500) }
await p.waitForTimeout(1500)
await p.screenshot({ path: `${OUT}/fin-C-vuemer.png` })

// D : équipements — activer + zoomer pour voir les symboles + la légende
await p.locator('button:has-text("Vue mer")').first().click() // désactiver vue mer pour lisibilité
await p.locator('button:has-text("Équipements")').first().click()
await p.waitForTimeout(600)
for (let i = 0; i < 3; i++) { await p.locator('button[title="Zoomer"]').click(); await p.waitForTimeout(500) }
await p.waitForTimeout(2000)
console.log('D légende équipements visible:', await p.locator('text=ÉQUIPEMENTS').count())
await p.screenshot({ path: `${OUT}/fin-D-equipements.png` })

await b.close()
console.log('captures finitions OK')
