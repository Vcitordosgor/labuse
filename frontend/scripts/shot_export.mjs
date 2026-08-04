// Capture ponctuelle d'un fichier HTML (ex. export fiche rendu hors-ligne) — Chrome système.
// Usage : node scripts/shot_export.mjs <chemin.html> <sortie.png> [selecteur]
import { chromium } from 'playwright'
const [file, out, sel = '.avis-ia'] = process.argv.slice(2)
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 900, height: 780 }, deviceScaleFactor: 2 })
await p.goto('file://' + file, { waitUntil: 'load' })
await p.locator(sel).first().screenshot({ path: out })
await b.close()
console.log('shot →', out)
