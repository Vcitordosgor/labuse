// FICHE-COUCHES-1 — capture d'une fiche fortement contrainte : ce qui remonte + le compteur.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const IDU = '97410000AN0347'   // Saint-Benoît, littorale : PPR+tri_zone+cinquante_pas+trait_de_cote+SUP+DPU
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/fiche-couches/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
p.on('console', () => {}); p.on('pageerror', () => {})
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
await sleep(2500)
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
await sleep(5000)   // laisse la fiche + cascade charger
// déplie la section « Risques et protections » (RefDrawer) pour montrer aléas/sols/vigilances
const risq = p.locator('[data-ref="risques"], #risques, summary:has-text("Risques")').first()
try { await p.getByText('Risques et protections', { exact: false }).first().click(); await sleep(600) } catch { /* déjà ouverte */ }
// déplie « N couches sans objet » si présent
try { await p.getByText('sans objet — déplier', { exact: false }).first().click(); await sleep(400) } catch { /* rien */ }
// lit le compteur affiché
const compteur = await p.evaluate(() => {
  const el = [...document.querySelectorAll('*')].find((n) => /couches? évaluées?/.test(n.textContent || '') && n.children.length < 3)
  return el ? el.textContent.trim() : '(compteur non lu)'
})
console.log('compteur affiché :', compteur)
// capture de la fiche (aside droite) — pleine hauteur
await p.screenshot({ path: OUT + 'fiche_contrainte.png' })
// crop resserré sur le panneau fiche (à droite)
await p.screenshot({ path: OUT + 'fiche_contrainte_panneau.png', clip: { x: 1010, y: 0, width: 430, height: 1000 } })
await br.close()
console.log('OK fiche-couches')
