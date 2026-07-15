// POINT 24 — comparateur swipe généralisé aux fonds de plan.
// Preuves : 1) défaut 1950↔actuelle (non-régression du geste) ; 2) swipe entre deux fonds
// quelconques (Plan IGN ↔ Ortho, à mi-course) ; 3) autre paire (Ortho ↔ Sombre) ;
// 4) synchro des caméras ; 5) sortie propre → carte à fond unique (toggle intact).
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 820 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })

// commune (charge la surcouche parcelles) puis le comparateur
await p.evaluate(() => window.__labuse.setCommune('Saint-Paul'))
await p.evaluate(() => window.__labuse.setModule('temps'))
await p.waitForSelector('[data-cmp-left]', { timeout: 10000 })
await p.waitForTimeout(2500) // laisser charger les tuiles WMTS

// helper : glisser la poignée du rideau à x% de la zone carte
async function dragTo(pct) {
  const zone = await p.locator('[data-cmp-left]').evaluateHandle(() => document.querySelector('.select-none'))
  const box = await zone.asElement().boundingBox()
  const handle = p.locator('button[title="Glisser pour comparer"]')
  const hb = await handle.boundingBox()
  await p.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2)
  await p.mouse.down()
  await p.mouse.move(box.x + box.width * pct, hb.y + hb.height / 2, { steps: 12 })
  await p.mouse.up()
  await p.waitForTimeout(700)
}

// 1) DÉFAUT : 1950 ↔ actuelle — le geste « 1950 » d'origine, inchangé
await dragTo(0.5)
await p.screenshot({ path: `${OUT}/swipe-1-defaut-1950.png` })

// 2) deux fonds quelconques : Plan IGN (gauche) ↔ Ortho actuelle (droite), rideau à ~38 %
await p.selectOption('[data-cmp-left]', 'bm-plan')
await p.selectOption('[data-cmp-right]', 'bm-ortho-now')
await p.waitForTimeout(2200)
await dragTo(0.38)
await p.screenshot({ path: `${OUT}/swipe-2-plan-vs-ortho.png` })

// 3) autre paire : Ortho actuelle ↔ Fond sombre, rideau à ~60 %
await p.selectOption('[data-cmp-left]', 'bm-ortho-now')
await p.selectOption('[data-cmp-right]', 'bm-carto')
await p.waitForTimeout(2200)
await dragTo(0.6)
await p.screenshot({ path: `${OUT}/swipe-3-ortho-vs-sombre.png` })

// 4) synchro caméras : bouger la carte de gauche, vérifier que la droite suit
const synced = await p.evaluate(() => {
  const tm = window.__labuse_tm
  tm.past.jumpTo({ center: [55.28, -21.03], zoom: 16 })
  const a = tm.past.getCenter(), c = tm.now.getCenter()
  return { dLng: Math.abs(a.lng - c.lng), dLat: Math.abs(a.lat - c.lat), z: Math.abs(tm.past.getZoom() - tm.now.getZoom()) }
})
console.log('synchro (écarts ~0 attendus):', JSON.stringify(synced))

// 5) SORTIE propre → carte à fond unique (toggle inchangé)
await p.click('button:has-text("Quitter")')
await p.waitForTimeout(1500)
await p.screenshot({ path: `${OUT}/swipe-4-sortie-fond-unique.png` })
const single = await p.evaluate(() => !!document.querySelector('canvas') && !document.querySelector('[data-cmp-left]'))
console.log('retour carte fond unique (comparateur démonté):', single)

await b.close()
console.log('captures swipe fonds de plan OK')
