// M43 — captures écran du volet Propriétaire : fait public d'entreprise (PM only).
//   1. PM avec signal (BOURBON CORP : cessée+pcl+radiée, tous datés+Sourcé)
//   2. PM sain (SCI ALOE : aucune mention d'état — témoin)
//   3. PP muette (aucun proprietaire_moral — rien)
// Usage : cd frontend && node ../qa/m43/shoot_m43.mjs   (API 8799 up, front buildé)
import { chromium } from 'playwright'

const PORT = 8799
const FICHES = [
  ['97415000EV0843', '1_pm_avec_signal'],   // BOURBON CORPORATION — 3 états publics datés
  ['97411000AW0692', '2_pm_sain_temoin'],    // SCI ALOE — PM sans signal : aucune mention
  ['97401000AC0023', '3_pp_muette'],         // non-PM : pas de volet société
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1100, height: 1500 } })
await p.goto(`http://127.0.0.1:${PORT}/socle`, { waitUntil: 'load', timeout: 90000 })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 30000 })
for (const [idu, nom] of FICHES) {
  await p.evaluate((id) => window.__labuse.select(id), idu)
  await p.waitForTimeout(2500)
  // ouvrir le volet Propriétaire (le fait société y est rendu, sous la dénomination)
  const prop = p.getByText('Propriétaire', { exact: false }).first()
  try { await prop.click({ timeout: 4000 }); await p.waitForTimeout(1200) } catch { /* déjà ouvert / absent */ }
  await p.screenshot({ path: `../qa/m43/screens/${nom}.png`, fullPage: true })
  console.log('png →', nom, idu)
}
await b.close()
