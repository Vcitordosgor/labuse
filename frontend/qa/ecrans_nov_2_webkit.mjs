// ECRANS-NOV-2 — parcours WebKit (Safari) de l'écran « Analyse LABUSE par scénario » DANS le panneau
// de gauche (à côté de la carte). Parcours : filtres Saint-Denis + un zonage → « Analyser avec LABUSE »
// → changement d'objectif et de scénario → clic sur une carte de résultat → détail → Retour. On vérifie
// aussi la règle de focus (aucun contour au CLIC).  webkit 2104 via /tmp/pw-wk (playwright 1.49.1).
import { webkit } from '/tmp/pw-wk/node_modules/playwright-core/index.mjs'

const BASE = process.env.BASE || 'http://127.0.0.1:9990/socle/'
const OUT = 'captures/ecrans-nov-2'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await webkit.launch()
const page = await b.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2,
  reducedMotion: 'reduce' })   // rituel d'analyse à 400 ms
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` })
const panel = '[data-ecran="analyse-scenario"]'

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|ok/i.test(x.textContent || '')); if (b) b.click() })

// ── 1. Filtres : Saint-Denis + un zonage (U) ──
await page.evaluate(() => {
  const L = window.__labuse
  L.setFilters({ ...L.getFilters(), communes: ['Saint-Denis'], zonage: ['U'], analyseLabuse: false })
  L.setVerdict(false)
})
// ouvrir la section Filtres pour atteindre le CTA « Analyser avec LABUSE »
for (let i = 0; i < 3; i++) {
  if (await page.locator('[data-analyser-btn]').count()) break
  await page.locator('[data-filtres-toggle]').first().click(); await wait(300)
}
await wait(300)
await shot('webkit-00-filtres')

// ── 2. Analyser avec LABUSE → le panneau d'analyse par scénario ──
await page.locator('[data-analyser-btn]').first().click()
await page.waitForSelector(`${panel} [data-carte-resultat]`, { timeout: 15000 })
await wait(500)
await shot('webkit-01-potentiel-keep')

// ── 3. Reconstruction ──
await page.locator(`${panel} button:has-text("Reconstruction")`).click()
await page.waitForFunction(() => /existant/.test(document.querySelector('[data-ecran="analyse-scenario"]')?.innerText || ''), { timeout: 10000 })
await wait(400)
await shot('webkit-02-potentiel-rebuild')

// ── 4. Prospection vente (Signal principal) ──
await page.locator(`${panel} button:has-text("Prospection vente")`).click()
await page.waitForFunction(() => /Signal/.test(document.querySelector('[data-ecran="analyse-scenario"]')?.innerText || ''), { timeout: 10000 })
await wait(400)
await shot('webkit-03-prospection')

// ── vérif FOCUS au clic : une puce ne pose AUCUN contour (data-input=mouse) ──
await page.locator(`${panel} button:has-text("Faible")`).first().click()
await wait(200)
const focusAuClic = await page.evaluate(() => {
  const el = document.activeElement
  const s = el ? getComputedStyle(el) : null
  return { input: document.documentElement.getAttribute('data-input'), tag: el && el.tagName,
    aContour: !!s && s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 }
})

// ── 5. Retour à Potentiel, clic sur une carte de résultat → détail ──
await page.locator(`${panel} button:has-text("Potentiel foncier")`).click()
await page.locator(`${panel} button:has-text("Reconstruction")`).click()
await page.waitForSelector(`${panel} [data-carte-resultat]`)
await page.locator(`${panel} [data-carte-resultat]`).first().click()
await page.waitForFunction(() => /Ce qui explique|Gain net/.test(document.body.innerText), { timeout: 10000 })
await wait(500)
await shot('webkit-04-detail')
await page.keyboard.press('Escape'); await wait(300)

// ── 6. Comprendre l'analyse ──
await page.locator(`${panel} [data-comprendre]`).click()
await page.waitForFunction(() => /Comprendre l'analyse/.test(document.body.innerText), { timeout: 5000 })
await wait(300)
await shot('webkit-05-comprendre')
await page.keyboard.press('Escape'); await wait(300)

// ── 7. Retour → revient aux filtres ──
await page.locator(`${panel} [data-retour]`).click()
await wait(400)
const apresRetour = await page.evaluate(() => ({
  panneauAnalyse: !!document.querySelector('[data-ecran="analyse-scenario"]'),
  analyseLabuse: window.__labuse.getFilters().analyseLabuse,
}))
await shot('webkit-06-retour-filtres')

console.log(JSON.stringify({ focusAuClic, apresRetour }, null, 2))
await b.close()
