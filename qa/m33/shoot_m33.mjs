// M33 — captures : tiroir mode B (saturée Sourcé / révélée Estimé / négatif honnête),
// nue témoin (AUCUN tiroir), export one-pager étiqueté.
// Usage : node ../qa/m33/shoot_m33.mjs <vite_url>   (API 8000 up derrière le proxy)
import { chromium } from 'playwright'

const BASE = process.argv[2]
const FICHES = [
  ['97415000AW2362', '1_saturee_niveaux_sources', true],
  ['97413000CX2643', '2_revelee_niveaux_estimes', true],
  ['97409000BI0229', '3_negatif_defaut_honnete', true],
  ['97408000AP1610', '4_nue_temoin_aucun_panneau', false],
]
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
for (const [idu, nom, attendPanneau] of FICHES) {
  await p.fill('input[placeholder^="Rechercher"]', idu)
  await p.waitForTimeout(1500)
  await p.keyboard.press('Enter')
  await p.waitForSelector('[data-fiche-idu]', { timeout: 30000 })
  await p.waitForTimeout(2500)
  const drawer = await p.$('[data-drawer="mode-b"]')
  if (attendPanneau) {
    if (!drawer) throw new Error(`tiroir mode B ATTENDU absent sur ${idu}`)
    await drawer.scrollIntoViewIfNeeded()
    const btn = await drawer.$('button')
    await btn.click()
    await p.waitForTimeout(600)
    await drawer.scrollIntoViewIfNeeded()
  } else if (drawer) {
    throw new Error(`tiroir mode B INATTENDU présent sur ${idu} (témoin nue)`)
  }
  await p.screenshot({ path: `../qa/m33/screens/${nom}.png` })
  console.log('png →', nom, attendPanneau ? '(tiroir ouvert)' : '(aucun tiroir ✓)')
}
await b.close()
