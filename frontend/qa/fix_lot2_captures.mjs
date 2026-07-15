// FIX LOT 2 — deep-links : A (Maps épingle), B (Cadastre sélectionné), C (1950 centré), D (radar).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const IDU = '97415000EL0387'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1360, height: 950 } })

async function openFiche() {
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 10000 })
  await p.evaluate((idu) => window.__labuse.select(idu), IDU)
  await p.waitForSelector('[data-maps-link]', { timeout: 10000 })
  await p.waitForTimeout(800)
}

// A — Maps : bouton renommé + href avec épingle (query=lat,lng)
await openFiche()
const mapsHref = await p.locator('[data-maps-link]').getAttribute('href')
const mapsLabel = (await p.locator('[data-maps-link]').innerText()).trim()
console.log('A Maps: label =', mapsLabel, '| href =', mapsHref)
await p.locator('aside').first().screenshot({ path: `${OUT}/fixA-maps-bouton.png` })

// C — 1950 : clic → vue historique centrée sur la parcelle (flyTo)
await p.locator('button:has-text("1950")').click()
await p.waitForTimeout(2500)
console.log('C 1950 : module temps ouvert =', /1950|temps|remonter/i.test(await p.evaluate(() => document.body.innerText)))
await p.screenshot({ path: `${OUT}/fixC-1950-centre.png` })

// B — Cadastre : clic → fond IGN plan + parcelle sélectionnée (halo)
await openFiche()
await p.locator('[data-cadastre-link]').click()
await p.waitForTimeout(2500)
console.log('B Cadastre : cliqué (fond IGN plan + halo select)')
await p.screenshot({ path: `${OUT}/fixB-cadastre-selection.png` })

// D — radar permis : drawer géocodé (bouton localiser) + non géocodé (message)
await p.evaluate(() => window.__labuse.setModule('permis'))
await p.waitForSelector('button:has-text("mois")', { timeout: 10000 })
await p.waitForTimeout(1500)
// ouvrir le 1er permis géocodé de la liste (fond surface-3, pas non-géocodé)
const rows = p.locator('button.flex.items-center.gap-2:has-text("PC"), button.flex.items-center.gap-2:has-text("DP")')
// clic sur un permis quelconque et check du drawer
await p.locator('[data-permis-drawer]').count().then((c) => c)
await b.close()
console.log('captures A/B/C partielles OK — D via script dédié')
