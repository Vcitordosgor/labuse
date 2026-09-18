import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-sources-audit/captures/sources-audit/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const IDU = '97410000AN0347'
const shot = async (p, name) => { await p.screenshot({ path: OUT + name }); console.log('shot', name) }

const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1200)
const ex = p.getByText('Explorer la carte', { exact: false })
if (await ex.count().catch(() => 0)) { await ex.first().click().catch(() => {}); await sleep(2500) }

// ── FICHE PARCELLE témoin ──
try {
  await p.evaluate((idu) => window.__labuse.select(idu), IDU)
  await sleep(6000) // fiche charge (couches évaluées)
  const fiche = p.locator('.fiche-v6, [data-fiche], aside').first()
  // capture pleine + scrolls
  await shot(p, 'fiche_parcelle_1_haut.png')
  // déplier tous les tiroirs de la fiche
  const tiroirs = p.locator('.fiche-v6 button, [data-fiche] button')
  const n = await tiroirs.count().catch(()=>0)
  for (let i=0;i<Math.min(n,40);i++){ await tiroirs.nth(i).click().catch(()=>{}); }
  await sleep(1500)
  // scroll le conteneur fiche par pas
  const cont = p.locator('.fiche-v6').first()
  if (await cont.count()) {
    await cont.evaluate(el => el.scrollTo(0, el.scrollHeight/3)); await sleep(900); await shot(p,'fiche_parcelle_2_milieu.png')
    await cont.evaluate(el => el.scrollTo(0, 2*el.scrollHeight/3)); await sleep(900); await shot(p,'fiche_parcelle_3_bas.png')
    await cont.evaluate(el => el.scrollTo(0, el.scrollHeight)); await sleep(900); await shot(p,'fiche_parcelle_4_fin.png')
  }
} catch(e){ console.log('FICHE err', e.message) }

// ── FICHE COMMUNE (contexte) ── Saint-Denis 97411 (ANRU, SRU, RP…)
try {
  await p.evaluate(() => window.__labuse.setContexteCommune('97411'))
  await sleep(4000)
  await shot(p, 'fiche_commune_1.png')
  const cc = p.locator('[data-contexte], aside').first()
  await p.mouse.wheel(0, 900); await sleep(700); await shot(p,'fiche_commune_2.png')
  await p.mouse.wheel(0, 900); await sleep(700); await shot(p,'fiche_commune_3.png')
} catch(e){ console.log('COMMUNE err', e.message) }

// ── OUTILS (parcelle sélectionnée d'abord pour les outils contextuels) ──
const outils = ['etude-zone','prospection-solaire','permis','communes','veille-promoteurs','patrimoine','risques','taxe-amenagement']
for (const o of outils) {
  try {
    await p.evaluate(() => window.__labuse.setView('cartes'))
    await p.evaluate((idu) => window.__labuse.select(idu), IDU); await sleep(1200)
    await p.evaluate((k) => window.__labuse.setModule(k), o)
    await sleep(3500)
    await shot(p, `outil_${o}.png`)
  } catch(e){ console.log('OUTIL', o, 'err', e.message) }
}

// ── RADAR ──
try { await p.evaluate(() => window.__labuse.setView('radar')); await sleep(3500); await shot(p,'radar.png') } catch(e){ console.log('RADAR err', e.message) }
// ── SOURCES page ──
try { await p.evaluate(() => window.__labuse.setView('sources')); await sleep(3500); await shot(p,'page_sources.png') } catch(e){ console.log('SOURCES err', e.message) }

await br.close()
console.log('ECRANS DONE')
