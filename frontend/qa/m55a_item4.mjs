// M55-A item 4 — bulle « équipement » cliquable (nom + catégorie + distance à la parcelle
// sélectionnée). Dev server vite (:5173). Usage : cd frontend && node qa/m55a_item4.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://localhost:5173/socle/'
const OUT = process.env.OUT || '../reports/m55-a-couches/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)

// 1) activer la couche « Équipements »
await page.locator('button:has(span:text-is("Équipements"))').first().click()
await page.waitForTimeout(300)

// 2) zoomer sur un secteur dense (centre de Saint-Denis) et attendre le rendu des icônes
await page.evaluate(() => window.__labuse_map.jumpTo({ center: [55.4504, -20.8823], zoom: 16 }))
await page.waitForTimeout(3500)

const box = await page.locator('canvas.maplibregl-canvas').boundingBox()

// 3) sélectionner d'abord une PARCELLE (pour la ligne « distance à la parcelle sélectionnée »)
await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
await page.waitForTimeout(1500)

// 4) localiser une icône équipement rendue et cliquer à son pixel
const info = await page.evaluate(() => {
  const m = window.__labuse_map
  const feats = m.queryRenderedFeatures({ layers: ['ov-equip'] })
  if (!feats.length) return { n: 0 }
  const f = feats[0]
  const p = m.project(f.geometry.coordinates)
  return { n: feats.length, x: p.x, y: p.y, name: f.properties?.name, subtype: f.properties?.subtype,
           sel: window.__labuse_map && document.querySelector('[data-verdict-off]') ? 'fiche?' : null }
})
console.log('equip rendus:', info.n, '| exemple:', info.subtype, info.name)

if (info.n > 0) {
  await page.mouse.click(box.x + info.x, box.y + info.y)
  await page.waitForTimeout(900)
  // capture pleine (carte + bulle) et gros plan sur la bulle
  await page.screenshot({ path: `${OUT}/item4_equip_popup_full.png` })
  const popup = page.locator('.labuse-popup').first()
  if (await popup.count()) {
    const pbox = await popup.boundingBox()
    if (pbox) await page.screenshot({ path: `${OUT}/item4_equip_popup_zoom.png`,
      clip: { x: Math.max(0, pbox.x - 30), y: Math.max(0, pbox.y - 30), width: pbox.width + 320, height: pbox.height + 120 } })
    console.log('POPUP HTML:', (await popup.innerText()).replace(/\n/g, ' | '))
  } else console.log('!! aucune bulle .labuse-popup détectée')
}
console.log('console errors:', errors.length, errors.slice(0, 4).join(' || '))
await browser.close()
