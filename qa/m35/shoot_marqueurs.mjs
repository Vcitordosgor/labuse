// M35 Lot D (reprise revue) — capture 5bis : carte île, marqueurs communes (les compteurs
// pilotent taille/éclat + infobulle native). Dump VERBATIM des titles (DOM réel) en .txt.
// Usage : node ../qa/m35/shoot_marqueurs.mjs  (depuis frontend/ ; vite + API 8000 up)
import { writeFileSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.VITE_URL || 'http://localhost:5173/socle/'
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1440, height: 900 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForSelector('[data-commune-marker]', { timeout: 30000 })
// l'ANALYSE (couche verdict) est OFF au chargement — les compteurs n'apparaissent qu'avec
// elle (marqueurs « hot » + infobulles chiffrées). On l'active comme un utilisateur.
await p.click('[data-verdict-on]')
await p.waitForTimeout(4500)
const titles = await p.$$eval('[data-commune-marker]',
  (els) => els.map((e) => e.getAttribute('title')))
writeFileSync('../qa/m35/screens/5bis_marqueurs_infobulles.txt',
  ['# Infobulles RÉELLES (attribut title) des 24 marqueurs communes — DOM au chargement',
   `# ${new Date().toISOString()}`, '', ...titles.sort()].join('\n'))
// survol Saint-Denis (l'état hover éclaire le marqueur ; l'infobulle native n'est pas
// rendue par le navigateur headless — la preuve chiffrée est le .txt ci-dessus)
await p.hover('[data-commune-marker="Saint-Denis"]')
await p.waitForTimeout(400)
await p.screenshot({ path: '../qa/m35/screens/5bis_carte_marqueurs_communes.png' })
console.log('png + titles →', titles.length, 'marqueurs')
console.log(titles.filter((t) => t && t.includes('Saint-Denis'))[0])
await b.close()
