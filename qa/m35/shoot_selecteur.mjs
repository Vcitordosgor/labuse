// M35 Lot D — capture du sélecteur /communes (l'ordre = compteurs tiers servis).
// Usage : node ../qa/m35/shoot_selecteur.mjs  (depuis frontend/ ; vite 5175 + API 8000 up)
import { chromium } from 'playwright'

const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
await p.goto('http://localhost:5175/socle/', { waitUntil: 'networkidle' })
await p.waitForTimeout(2500)
// ouvre le sélecteur de commune (bouton « Toute l'île » du Header)
await p.getByText("Toute l’île", { exact: false }).first().click()
await p.waitForTimeout(1200)
await p.screenshot({ path: '../qa/m35/screens/5_selecteur_communes_ordre_tiers.png' })
console.log('png → 5_selecteur_communes_ordre_tiers')
await b.close()
