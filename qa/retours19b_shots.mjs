// RETOURS-19 (Y1-Y5) — captures états actifs + survols. PHASE=avant|apres.
// Lancer depuis frontend/ : CHROME=<exe> PHASE=apres node ../qa/retours19b_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-19/captures'
fs.mkdirSync(OUT, { recursive: true })
const S = process.env.PHASE || 'apres'
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
const clip = async (name, sel) => {
  const el = await page.$(sel); if (!el) { console.log('  MISS', name, sel); return }
  await el.screenshot({ path: `${OUT}/${name}-${S}.png` }); console.log('  shot', name)
}
const shot = async (name) => { await page.screenshot({ path: `${OUT}/${name}-${S}.png` }); console.log('  full', name) }

await page.goto(`${BASE}?y=1`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500)

// Y2 — accueil : survol « Explorer la carte » (icône sans carré sombre sur le vert)
const acc = await page.$('.acc-entry')
if (acc) { await acc.hover(); await page.waitForTimeout(500); await clip('accueil-survol', '.acc-entry') }

// Y1 — sélecteur de périmètre ouvert (vert opaque) + Y3 survol d'une ligne à deux actions
const perim = await page.$('[data-commune-select]')
if (perim) {
  await perim.click(); await page.waitForTimeout(600)
  await clip('perimetre-actif', '[data-commune-select]')
  const row = await page.$('[data-fiche-commune]')
  if (row) {
    // survol de la ZONE PRINCIPALE (le bouton frère à gauche)
    const primary = await page.evaluateHandle((b) => b.previousElementSibling, row)
    await primary.asElement()?.hover(); await page.waitForTimeout(400)
    await clip('commune-survol-principal', '.floating')
    // survol de « voir la fiche → »
    await row.hover(); await page.waitForTimeout(400)
    await clip('commune-survol-fiche', '.floating')
  }
  await page.keyboard.press('Escape'); await page.waitForTimeout(300)
}

// Y1 — fond de carte : bouton ouvert (vert opaque) + entrée active (vert opaque)
const bm = await page.$('button[title="Fond de plan"]')
if (bm) { await bm.click(); await page.waitForTimeout(600); await shot('fond-carte-ouvert'); await page.keyboard.press('Escape'); await page.waitForTimeout(300) }

// Y1 — rail : entrée Outils active (vert opaque)
await page.goto(`${BASE}?y=2#m=permis`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
// ouvrir le menu Outils via le rail (l'entrée devient active)
const railOutils = await page.$('button.rail-item:has-text("Outils"), [data-rail="outils"]')
if (railOutils) { await railOutils.click(); await page.waitForTimeout(600) }
await clip('rail-outils-actif', 'nav')

// Y5 — panneau Permis : bandeau Sitadel sur une ligne
await page.goto(`${BASE}?y=3#m=permis`, { waitUntil: 'networkidle' }); await page.waitForTimeout(2500)
await clip('permis-sitadel', 'aside')

fs.writeFileSync(`${OUT}/_errors-b-${S}.txt`, errors.join('\n') || 'aucune')
console.log('ERREURS:', errors.length)
await browser.close()
