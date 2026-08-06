// M36 — captures de revue (one-pagers via API 8010).
// Usage : node ../qa/m36/shoot_m36.mjs  (depuis frontend/)
import { chromium } from 'playwright'

const FICHES = [
  ['97418000AT2542', '2_AT2542_brulante_rang_visible_sans_scores'],
  ['97412000BW0326', '3_BW0326_depassement_emprise_libelle'],
  ['97419000AL1154', '4_AL1154_fourchette_et_sans_scores'],
  ['97407000AI1821', '5_AI1821_reserve_rang_masque'],
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1000, height: 1400 } })
for (const [idu, nom] of FICHES) {
  await p.goto(`http://127.0.0.1:8010/parcels/${idu}/export?format=onepager`, { waitUntil: 'load', timeout: 90000 })
  await p.waitForTimeout(2500)
  await p.screenshot({ path: `../qa/m36/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom)
}
await b.close()
