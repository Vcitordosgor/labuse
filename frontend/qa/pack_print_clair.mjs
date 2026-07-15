// APPORTEUR PACK — variante print/PDF CLAIRE (écran reste sombre).
// Preuve : 1) capture écran = thème sombre ; 2) PDF (rendu en media print) = thème clair.
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/p/'
const OUT = '../../reports/pre-lancement/captures'
const TOKEN = '5MrzfaL4yq7TW9uT' // Bras-Panon, AVEC adresse BAN

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 760, height: 1200 } })
await p.goto(BASE + TOKEN, { waitUntil: 'networkidle' })

// 1) ÉCRAN = sombre (media screen) — non régression
await p.emulateMedia({ media: 'screen' })
await p.screenshot({ path: `${OUT}/pack-print-ecran-sombre.png`, fullPage: true })

// 2) EXPORT PDF = clair. page.pdf() honore le media émulé → on force 'print' AVANT (sinon il
//    reprend le 'screen' émulé ci-dessus et sort un PDF sombre).
await p.emulateMedia({ media: 'print' })
await p.pdf({ path: `${OUT}/pack-print-clair.pdf`, printBackground: true, format: 'A4' })

// 3) aperçu visuel du thème print (media print + screenshot)
await p.screenshot({ path: `${OUT}/pack-print-clair-apercu.png`, fullPage: true })

await b.close()
console.log('captures pack print OK')
