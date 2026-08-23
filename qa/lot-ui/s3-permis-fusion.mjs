// §3 — parcours de la FUSION « Permis » (Radar + Point mort en un outil).
// Prouve : (a) le menu ne montre qu'UNE carte « Permis » ; (b) le radar pose des points cliquables ;
// (c) le filtre « Au point mort » pose AUSSI des points cliquables (plus de surlignage de parcelle) ;
// (d) un clic sur un point « point mort » ouvre la fiche PERMIS (drawer), jamais la fiche parcelle ;
// (e) le deep-link `promesses` ouvre l'outil avec le filtre déjà actif.
// Usage : BASE=http://localhost:5174/socle/ node qa/lot-ui/s3-permis-fusion.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 }, deviceScaleFactor: 2 })
page.setDefaultTimeout(30000)
const shot = async (n, note) => { await page.waitForTimeout(500); await page.screenshot({ path: `${OUT}/${n}.png` }); console.log(`📸 ${n} — ${note}`) }

// compte les points permis (module-extra, kind='permis') posés sur la carte
const nbPoints = () => page.evaluate(() => {
  const m = window.__labuse_map; if (!m) return -1
  return m.querySourceFeatures('module-extra').filter((f) => f.properties?.kind === 'permis' && f.geometry?.type === 'Point').length
})
const unPoint = () => page.waitForFunction(() => {
  const m = window.__labuse_map; if (!m) return null
  const fs = m.querySourceFeatures('module-extra').filter((f) => f.properties?.kind === 'permis' && f.geometry?.type === 'Point')
  if (!fs.length) return null
  const f = fs[0]; return { lng: f.geometry.coordinates[0], lat: f.geometry.coordinates[1], pid: String(f.properties.permit_id) }
}, { timeout: 30000 }).then((h) => h.jsonValue())
const cliquer = async (pt) => {
  await page.evaluate(({ lng, lat }) => window.__labuse_map.jumpTo({ center: [lng, lat], zoom: 17 }), pt)
  // attendre que le point soit RENDU sous le centre (module-pts), sinon le clic pixel rate la cible
  await page.waitForFunction(({ lng, lat }) => {
    const m = window.__labuse_map; if (!m || !m.isMoving) return false
    if (m.isMoving()) return false
    const p = m.project([lng, lat])
    const fs = m.queryRenderedFeatures([[p.x - 6, p.y - 6], [p.x + 6, p.y + 6]], { layers: ['module-pts'] })
    return fs.length > 0
  }, pt, { timeout: 15000 })
  const px = await page.evaluate(({ lng, lat }) => { const m = window.__labuse_map; const p = m.project([lng, lat]); const r = m.getCanvas().getBoundingClientRect(); return { x: r.left + p.x, y: r.top + p.y } }, pt)
  await page.mouse.click(px.x, px.y)
}

let ok = true
try {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(600)

  // (a) menu : UNE seule carte « Permis »
  await page.click('button[title="Outils"]')
  await page.locator('[data-outil]').first().waitFor()
  const cartesPermis = await page.locator('[data-outil="permis"]').count()
  const cartesPromesses = await page.locator('[data-outil="promesses"]').count()
  const labels = await page.locator('[data-outil="permis"]').innerText()
  console.log(`(a) carte permis=${cartesPermis} · carte promesses(doit=0)=${cartesPromesses} · label="${labels.split('\n')[0]}"`)
  if (cartesPermis !== 1 || cartesPromesses !== 0) ok = false

  // (b) RADAR — points cliquables
  await page.click('[data-outil="permis"]')
  await page.waitForSelector('[data-permis-pointmort]', { state: 'visible' })
  const ptRadar = await unPoint()
  console.log(`(b) radar : ${await nbPoints()} points · exemple ${ptRadar.pid}`)
  await shot('s3-01-radar-points', 'radar : points permis cliquables')

  // (c) FILTRE « Au point mort » → points (pas de surlignage parcelle)
  await page.click('[data-permis-pointmort]')
  await page.waitForTimeout(400)
  // attendre que la liste point-mort charge puis les points
  await page.waitForFunction(() => {
    const m = window.__labuse_map; if (!m) return false
    return m.querySourceFeatures('module-extra').some((f) => f.properties?.kind === 'permis' && f.geometry?.type === 'Point')
  }, { timeout: 40000 })
  const actif = await page.locator('[data-permis-pointmort="1"]').count()
  const nbPm = await nbPoints()
  console.log(`(c) point mort actif=${actif} · ${nbPm} points sur la carte`)
  if (actif !== 1 || nbPm < 1) ok = false
  await shot('s3-02-pointmort-points', 'point mort : points cliquables (plus de surlignage parcelle)')

  // (d1) une LIGNE point-mort ouvre la fiche PERMIS (liste permis-centrée, plus de Row parcelle)
  await page.locator('[data-permis-row]').first().click()
  await page.waitForSelector('[data-permis-drawer]', { state: 'visible', timeout: 8000 })
  const drawerListe = await page.locator('[data-permis-drawer]').count()
  const ficheListe = await page.locator('[data-fiche-idu]').count()
  console.log(`(d1) clic LIGNE point mort → drawer permis=${drawerListe} · fiche parcelle=${ficheListe} (doit=0)`)
  if (drawerListe < 1 || ficheListe > 0) ok = false
  await page.locator('[data-permis-drawer]').click()   // clic backdrop ferme
  await page.waitForSelector('[data-permis-drawer]', { state: 'hidden', timeout: 5000 }).catch(() => {})

  // (d2) clic sur un POINT point-mort de la carte → drawer PERMIS, jamais fiche parcelle
  const ptPm = await unPoint()
  await cliquer(ptPm)
  await page.waitForSelector('[data-permis-drawer]', { state: 'visible', timeout: 8000 })
  const drawer = await page.locator('[data-permis-drawer]').count()
  const fiche = await page.locator('[data-fiche-idu]').count()
  console.log(`(d2) clic POINT point mort → drawer permis=${drawer} · fiche parcelle=${fiche} (doit=0)`)
  if (drawer < 1 || fiche > 0) ok = false
  await shot('s3-03-pointmort-clic-drawer', `clic point mort → fiche PERMIS (drawer=${drawer}, parcelle=${fiche})`)
  await page.locator('[data-permis-drawer]').click().catch(() => {})

  // (e) deep-link `promesses` → outil ouvert, filtre déjà actif
  await page.goto(BASE + '#m=promesses', { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('[data-permis-pointmort]', { state: 'visible', timeout: 15000 })
  const actifDeep = await page.locator('[data-permis-pointmort="1"]').count()
  const headerDeep = await page.locator('[data-module-breadcrumb]').innerText().catch(() => '')
  console.log(`(e) deep-link promesses : filtre actif=${actifDeep} · fil="${headerDeep.replace(/\n/g, ' ')}"`)
  if (actifDeep !== 1) ok = false
  await shot('s3-04-deeplink-promesses', 'deep-link promesses → outil Permis, filtre point mort actif')

  console.log(ok ? '\n✅ §3 fusion Permis : OK' : '\n❌ §3 : au moins une assertion a échoué')
  if (!ok) process.exitCode = 1
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 500))
  await page.screenshot({ path: `${OUT}/s3-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
