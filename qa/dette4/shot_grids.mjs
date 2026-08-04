// Capture chaque .grid de /tmp/ech100.html en PNG (une image = 4 parcelles à classer).
// Usage : depuis frontend/ — node ../qa/dette4/shot_grids.mjs /tmp/ech100.html /tmp/ech100
import { chromium } from 'playwright'
import { mkdir } from 'node:fs/promises'
const [file, outDir] = process.argv.slice(2)
await mkdir(outDir, { recursive: true })
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1200, height: 900 }, deviceScaleFactor: 1.5 })
await p.goto('file://' + file, { waitUntil: 'load' })
const n = await p.locator('.grid').count()
for (let i = 0; i < n; i++) {
  await p.locator('.grid').nth(i).screenshot({ path: `${outDir}/grid_${String(i + 1).padStart(2, '0')}.png` })
}
await b.close()
console.log(`${n} grilles → ${outDir}/grid_NN.png`)
