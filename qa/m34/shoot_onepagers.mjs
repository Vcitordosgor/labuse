// M34 — captures de revue : one-pagers (surface client modifiée) → PNG pleine page.
// Usage : node qa/m34/shoot_onepagers.mjs   (depuis frontend/ pour node_modules ; API 8010 up)
import { chromium } from 'playwright'

const FICHES = [
  ['97418000AT2542', '1_AT2542_brulante_ancre_golden'],
  ['97422000CY0197', '2_CY0197_brulante_badge_division'],
  ['97419000AL1154', '3_AL1154_acreuser_ex_montante_registre_piscine'],
  ['97415000CX0639', '4_CX0639_chaude_batie_marginale_divisible'],
  ['97407000AI1821', '5_AI1821_reserve_fonciere'],
  ['97412000BW0326', '6_BW0326_declassee_bati_revele'],
  ['97408000AP1610', '7_AP1610_nue_classique'],
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1000, height: 1400 } })
for (const [idu, nom] of FICHES) {
  await p.goto(`http://127.0.0.1:8010/parcels/${idu}/export?format=onepager`, { waitUntil: 'networkidle' })
  await p.screenshot({ path: `../qa/m34/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom)
}
await b.close()
