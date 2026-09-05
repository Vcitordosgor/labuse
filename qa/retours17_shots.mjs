// RETOURS-17 — captures panneau Permis (5 états) + carte (4 états, 3 couleurs) + légende.
// PHASE=avant|apres. Lancer depuis frontend/ : CHROME=<exe> PHASE=apres node ../qa/retours17_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-17/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  shot', n, SUFFIX) }
const shotPanel = async (n) => {
  const el = await page.$('aside') || await page.$('[data-permis-total]')
  if (el) { await el.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  panel', n, SUFFIX) }
}
let _n = 0
const go = async () => { await page.goto(`${BASE}?r17=${++_n}#m=permis`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500) }
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2800)
  await page.mouse.click(700, 860)
  await page.waitForTimeout(300)
}
const seg = async (k) => {
  const b = await page.$(`[data-permis-seg="${k}"]`)
  if (b) { await b.click(); await page.waitForTimeout(3500) }
}
const openLegend = async () => {
  const t = await page.$('[data-legend-toggle]')
  if (t) { await t.click().catch(() => {}); await page.waitForTimeout(500) }
}

// ── panneau + carte sur SOMBRE (fond par défaut) ──
await go()
await seg('tous')           // Tous : les quatre états peints, trois couleurs
await openLegend()
await shotPanel('W2-panneau-tous')     // le panneau : bloc total + 5 lignes + bandeau
await shot('W3-carte-tous-sombre')     // la carte : vert/corail/gris + légende 3 entrées

// chaque état isolé (le panneau accentue l'actif, la carte n'en montre qu'une couleur)
await seg('cours'); await shotPanel('W2-panneau-recent')
await seg('mort'); await shotPanel('W2-panneau-dormant')
await seg('acheve'); await shotPanel('W2-panneau-acheve')
await seg('autre'); await shotPanel('W2-panneau-autre')

// ── carte sur ORTHO (4 fonds : lisibilité des 3 couleurs sur photo) ──
await go()
await seg('tous')
await basemap('Ortho IGN')
await openLegend()
await shot('W3-carte-tous-ortho')

fs.writeFileSync(`${OUT}/_errors-${SUFFIX}.txt`, errors.join('\n') || 'aucune')
console.log('ERREURS:', errors.length)
await browser.close()
