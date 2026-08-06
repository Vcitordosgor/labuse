// M39 — captures de revue (dette #13) : chaude+vigilance piscine · AL1154 (réconciliation
// registre, motif client identique) · témoin sous-seuil (AUCUNE vigilance). One-pager servi.
// Usage : node qa/m39/shoot_m39.mjs  (API up sur 8011)
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8011'
const FICHES = [
  ['97411000EL0203', '1_chaude_vigilance_piscine'],
  ['97419000AL1154', '2_AL1154_reconciliation_registre'],
  ['97411000BX0347', '3_temoin_sous_seuil_sans_vigilance'],
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1000, height: 1400 } })
for (const [idu, nom] of FICHES) {
  await p.goto(`${BASE}/parcels/${idu}/export?format=onepager`, { waitUntil: 'networkidle' })
  await p.screenshot({ path: `qa/m39/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom)
}
await b.close()
