// M35 — captures de revue : one-pagers (motif client, pourcentages, témoin nue) → PNG.
// Usage : node ../qa/m35/shoot_m35.mjs  (depuis frontend/ ; API 8010 up)
import { chromium } from 'playwright'

const FICHES = [
  ['97419000AL1154', '1_AL1154_motif_client_nettoye'],
  ['97422000CY0197', '2_CY0197_pourcentages_libelles'],
  ['97415000CX0639', '3_CX0639_pourcentages_libelles'],
  ['97408000AP1610', '4_AP1610_nue_banale_temoin'],
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1000, height: 1400 } })
for (const [idu, nom] of FICHES) {
  await p.goto(`http://127.0.0.1:8010/parcels/${idu}/export?format=onepager`, { waitUntil: 'networkidle' })
  await p.screenshot({ path: `../qa/m35/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom)
}
await b.close()
