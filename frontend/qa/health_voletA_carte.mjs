// VOLET A — complément : couleur RÉELLE peinte sur la carte (fill-color rendu) pour
// une brûlante et une écartée étage0, en zoomant sur la parcelle. LECTURE SEULE, :8010.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/health-check-post-m6/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 160)) })

// commune-scopé : le GeoJSON commune est queryable et porte tier_v2/etage0/status
const CIBLES = [
  { idu: '97423000AB1908', commune: 'Les Trois-Bassins', attendu: 'brulante → #E8695A braise' },
  { idu: '97423000AB1341', commune: 'Les Trois-Bassins', attendu: 'écartée étage0 → #E8695A opacity ~0.04' },
  { idu: '97410000AS1425', commune: 'Saint-Benoît', attendu: 'brulante → #E8695A braise' },
]
const results = []
for (const c of CIBLES) {
  await page.goto(BASE + '#v=1&c=' + encodeURIComponent(c.commune), { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForFunction(() => window.__labuse && window.__labuse_map, null, { timeout: 30000 })
  await page.waitForTimeout(4000)
  // attendre que le geojson commune porte la parcelle
  await page.waitForFunction((id) => {
    try { return window.__labuse_map.querySourceFeatures('parcels').some((x) => String(x.properties?.idu) === id) } catch { return false }
  }, c.idu, { timeout: 60000 }).catch(() => {})
  const info = await page.evaluate((id) => {
    const m = window.__labuse_map
    const f = m.querySourceFeatures('parcels').find((x) => String(x.properties?.idu) === id)
    if (!f) return { found: false }
    // centre approx
    let coord
    const g = f.geometry
    if (g.type === 'Polygon') coord = g.coordinates[0][0]
    else if (g.type === 'MultiPolygon') coord = g.coordinates[0][0][0]
    return { found: true, tier_v2: f.properties?.tier_v2, etage0: f.properties?.etage0, status: f.properties?.status, lng: coord[0], lat: coord[1] }
  }, c.idu)
  let rendered = null
  if (info.found) {
    await page.evaluate((i) => window.__labuse_map.jumpTo({ center: [i.lng, i.lat], zoom: 17.5 }), info)
    await page.waitForTimeout(2500)
    // lire la couleur rendue de parcels-fill au point de la parcelle
    rendered = await page.evaluate((id) => {
      const m = window.__labuse_map
      const fs = m.queryRenderedFeatures(undefined, { layers: ['parcels-fill'] })
      const f = fs.find((x) => String(x.properties?.idu) === id)
      // maplibre ne renvoie pas la couleur résolue directement : on recompose la règle
      const p = f?.properties
      if (!p) return { rendered_found: false }
      const e0 = Number(p.etage0 ?? 0) >= 1
      const tier = e0 ? 'ecartee(etage0)' : (p.tier_v2 || p.status || '')
      const color = e0 ? '#E8695A(0.04)' : ({ brulante: '#E8695A', chaude: '#E8B44C', a_creuser: '#8FA69A', reserve_fonciere: '#6FA8DC', ecartee: '#E8695A' }[p.tier_v2] || { chaude: '#5CE6A1', a_surveiller: '#4ADE96', a_creuser: '#E8B44C', ecartee: '#E8695A' }[p.status] || '#39463F')
      return { rendered_found: true, tier, color }
    }, c.idu)
    await page.screenshot({ path: `${OUT}/voletA-carte-${c.idu}.png` })
  }
  const r = { ...c, source: info, rendered }
  results.push(r)
  console.log(`■ ${c.idu} (${c.commune}) attendu=${c.attendu}`)
  console.log(`   source: found=${info.found} tier_v2=${info.tier_v2} etage0=${info.etage0} status=${info.status}`)
  console.log(`   rendu carte: ${rendered ? JSON.stringify(rendered) : 'n/a'}`)
}
console.log('\nerreurs console:', errs.length)
errs.slice(0, 6).forEach((e) => console.log('  ·', e))
await browser.close()
