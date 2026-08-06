// M37 — captures : fiche avec vigilances intactes post-extinction, mode B en k€, nue témoin.
// Usage : node ../qa/m37/shoot_m37.mjs   (API 8010 up)
import { chromium } from 'playwright'

const FICHES = [
  ['97418000AT2542', '1_brulante_vigilance_acces_intacte'],   // vigilance (accès) préservée
  ['97415000AW2362', '2_mode_b_ke_saturee'],                  // mode B « ~181 k€ »
  ['97408000AP1610', '3_nue_temoin'],                         // nue classique
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1000, height: 1400 } })
for (const [idu, nom] of FICHES) {
  await p.goto(`http://127.0.0.1:8010/parcels/${idu}/export?format=onepager`, { waitUntil: 'load', timeout: 90000 })
  await p.waitForTimeout(2500)
  await p.screenshot({ path: `../qa/m37/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom)
}
await b.close()
