// AUDIT M5.1 lots 4.1/4.4 — couches de la carte (LECTURE SEULE).
// Pour chaque couche du panneau « COUCHES » : activation via l'UI, écoute réseau
// (layers.geojson / parcels.geojson / tuiles MVT / communes974.geojson), vérification
// de rendu (diff pixel du canvas carte avant/après toggle), capture d'écran.
//
// Usage : cd frontend && node qa/audit_couches_m51.mjs
import { mkdirSync, writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../reports/m51-unification/captures'
mkdirSync(OUT, { recursive: true })

const CLIP = { x: 310, y: 0, width: 1120, height: 890 } // zone carte (panneau 300px exclu)
const results = []

const browser = await chromium.launch()

async function newPage(url) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page._net = []
  page._errors = []
  page.on('console', (m) => { if (m.type() === 'error') page._errors.push(m.text()) })
  page.on('response', async (r) => {
    const u = r.url()
    if (!/\/map\/(tiles|layers\.geojson|parcels\.geojson)|communes974\.geojson/.test(u)) return
    const entry = { url: u.replace(/^https?:\/\/[^/]+/, ''), status: r.status(), n: null, vueMerOui: null }
    try {
      const ct = r.headers()['content-type'] || ''
      if (ct.includes('json')) {
        const j = await r.json()
        entry.n = j?.features?.length ?? null
        if (u.includes('parcels.geojson') && Array.isArray(j?.features))
          entry.vueMerOui = j.features.filter((f) => f?.properties?.vue_mer === 'oui').length
      }
    } catch { /* pbf / body déjà consommé */ }
    page._net.push(entry)
  })
  await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 })
  await page.waitForTimeout(3000)
  return page
}

const layerBtn = (page, label) => page.locator(`button:has(span:text-is("${label}"))`).first()
const isOn = async (page, label) => (await layerBtn(page, label).locator('span.bg-mint').count()) > 0
const mapShot = (page) => page.screenshot({ clip: CLIP })

/** Résumé réseau : agrège tuiles pbf par famille, garde les geojson tels quels. */
function summarizeNet(net) {
  const out = []
  const tiles = {}
  for (const e of net) {
    if (/\/map\/tiles\//.test(e.url)) {
      const fam = e.url.replace(/\/\d+\/\d+\/\d+\.pbf.*/, '/{z}/{x}/{y}.pbf')
      tiles[fam] ??= { url: fam, count: 0, statuses: new Set() }
      tiles[fam].count++
      tiles[fam].statuses.add(e.status)
    } else out.push(e)
  }
  for (const t of Object.values(tiles))
    out.push({ url: `${t.url} (×${t.count})`, status: [...t.statuses].join('/'), n: null })
  return out
}

/** Teste UNE couche : toggle, réseau, diff de rendu, capture. */
async function auditLayer(page, { key, label, file, defaultOn = false, zoomFirst = false }) {
  const r = { couche: key, label, mode: page._mode, active: false, rendu: false, net: [], note: '' }
  try {
    const on0 = await isOn(page, label)
    if (zoomFirst) { // équipements : minzoom 13 — zoomer AVANT le diff de rendu
      await page.mouse.move(CLIP.x + CLIP.width / 2, CLIP.y + CLIP.height / 2)
      for (let i = 0; i < 5; i++) { await page.mouse.wheel(0, -600); await page.waitForTimeout(350) }
      await page.waitForTimeout(1500)
    }
    if (defaultOn && on0) { // couche active par défaut : OFF → diff → ON
      const before = await mapShot(page)
      await layerBtn(page, label).click()
      await page.waitForTimeout(1600)
      const after = await mapShot(page)
      r.rendu = !before.equals(after)
      page._net.length = 0
      await layerBtn(page, label).click() // ré-active
      await page.waitForTimeout(1600)
    } else {
      const before = await mapShot(page)
      page._net.length = 0
      await layerBtn(page, label).click()
      await page.waitForTimeout(2500)
      const after = await mapShot(page)
      r.rendu = !before.equals(after)
    }
    r.active = await isOn(page, label)
    r.net = summarizeNet(page._net)
    if (file) await page.screenshot({ path: `${OUT}/${file}` })
    if (!defaultOn) { await layerBtn(page, label).click(); await page.waitForTimeout(600) } // éteint
    if (zoomFirst) { // dézoome (retour au cadre commune)
      await page.mouse.move(CLIP.x + CLIP.width / 2, CLIP.y + CLIP.height / 2)
      for (let i = 0; i < 5; i++) { await page.mouse.wheel(0, 600); await page.waitForTimeout(250) }
    }
  } catch (e) { r.note = 'ERREUR ' + e.message.slice(0, 120) }
  results.push(r)
  console.log(`[${page._mode}] ${label} → active=${r.active} rendu_change=${r.rendu}`)
  for (const e of r.net) console.log(`    ${e.status} ${e.url}${e.n != null ? ` — ${e.n} features` : ''}${e.vueMerOui != null ? ` (vue_mer=oui : ${e.vueMerOui})` : ''}`)
  return r
}

// ═══ 1. Mode COMMUNE (Saint-Paul) ═══
console.log('\n── Mode commune : Saint-Paul ──')
{
  const page = await newPage(BASE + '#f=1&v=1&c=Saint-Paul')
  page._mode = 'commune'
  // requêtes du chargement (parcelles + communes974 arrivent au boot, hors toggle)
  const loadNet = summarizeNet(page._net)
  console.log('  chargement :')
  for (const e of loadNet) console.log(`    ${e.status} ${e.url}${e.n != null ? ` — ${e.n} features` : ''}${e.vueMerOui != null ? ` (vue_mer=oui : ${e.vueMerOui})` : ''}`)
  results.push({ couche: '_chargement', mode: 'commune', net: loadNet })

  await auditLayer(page, { key: 'zonage', label: 'Zonage PLU', file: 'couche-zonage.png' })
  await auditLayer(page, { key: 'ppr', label: 'PPR multirisque', file: 'couche-ppr.png' })
  await auditLayer(page, { key: 'vue_mer', label: 'Vue mer', file: 'couche-vue-mer.png' })
  await auditLayer(page, { key: 'parc', label: 'Parc national', file: 'couche-parc.png' })
  await auditLayer(page, { key: 'anru', label: 'ANRU (NPNRU)', file: 'couche-anru.png' })
  await auditLayer(page, { key: 'equipements', label: 'Équipements', file: 'couche-equipements.png', zoomFirst: true })
  // couches actives par défaut (données déjà à bord — le toggle ne pilote que la visibilité)
  await auditLayer(page, { key: 'parcelles', label: 'Parcelles', file: 'couche-parcelles.png', defaultOn: true })
  await auditLayer(page, { key: 'limites', label: 'Limites parcelles', file: 'couche-limites.png', defaultOn: true })
  await auditLayer(page, { key: 'communes', label: 'Limites communes', file: 'couche-communes.png', defaultOn: true })

  console.log('  erreurs console :', page._errors.length ? page._errors.slice(0, 5) : 'aucune')
  await page.close()
}

// ═══ 2. Mode ÎLE : zonage/PPR passent en tuiles MVT ; ANRU sert les 8 périmètres ═══
console.log('\n── Mode île (toute l\'île) ──')
{
  const page = await newPage(BASE + '#v=1')
  page._mode = 'ile'
  const loadNet = summarizeNet(page._net)
  results.push({ couche: '_chargement', mode: 'ile', net: loadNet })
  console.log('  chargement :')
  for (const e of loadNet) console.log(`    ${e.status} ${e.url}`)

  await auditLayer(page, { key: 'zonage', label: 'Zonage PLU', file: 'couche-zonage-ile.png' })
  await auditLayer(page, { key: 'ppr', label: 'PPR multirisque', file: 'couche-ppr-ile.png' })
  await auditLayer(page, { key: 'anru', label: 'ANRU (NPNRU)', file: 'couche-anru-ile.png' })

  console.log('  erreurs console :', page._errors.length ? page._errors.slice(0, 5) : 'aucune')
  await page.close()
}

await browser.close()
writeFileSync(`${OUT}/../audit-couches-net.json`, JSON.stringify(results, null, 2))
console.log(`\n→ détail réseau : ${OUT}/../audit-couches-net.json`)
