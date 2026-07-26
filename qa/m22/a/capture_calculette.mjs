// M22-A — capture UI : bascule « Charge supportable / Prix d'achat max » dans le tiroir
// Faisabilité de la fiche (parcelle réelle 97415000ET1659, CF centrale positive, prix fiable).
// Usage : node qa/m22/a/capture_calculette.mjs  (API+front sur :8022)
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8022'
const IDU = '97415000ET1659'
const OUT = 'qa/m22/a'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } })
await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 15000 })
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
await p.waitForSelector('[data-drawer="faisabilite"]', { timeout: 15000 })
// ouvrir le tiroir Faisabilité (clic sur son en-tête) et attendre la calculette
await p.locator('[data-drawer="faisabilite"] > button').click()
await p.waitForSelector('[data-calculette]', { timeout: 15000 })
await p.waitForSelector('[data-calc-resultat]', { timeout: 20000 })
// saisir un prix demandé AU-DESSUS du max (4 M€ > 3,22 M€) — l'écart doit apparaître
await p.locator('[data-calculette] input[type="number"]').nth(2).fill('4000000')
await p.waitForSelector('[data-calc-verdict]', { timeout: 15000 })
await p.waitForTimeout(400)
const drawer = p.locator('[data-drawer="faisabilite"]')
await drawer.screenshot({ path: `${OUT}/ui_mode_charge.png` })
console.log('mode charge OK (verdict achat affiché)')

// bascule → Prix d'achat max
await p.locator('[data-calc-mode="achat_max"]').click()
await p.waitForSelector('[data-calc-ecart]', { timeout: 15000 })
await p.waitForTimeout(400)
const resultat = (await p.locator('[data-calc-resultat]').innerText()).replace(/\s+/g, ' ')
const ecart = (await p.locator('[data-calc-ecart]').innerText()).replace(/\s+/g, ' ')
console.log('résultat:', resultat)
console.log('écart:', ecart)
if (!/Prix d'achat maximal admissible/.test(resultat)) throw new Error('libellé inverse absent')
if (!/surcoût/.test(ecart)) throw new Error('écart de négociation absent')
await drawer.screenshot({ path: `${OUT}/ui_mode_achat_max.png` })
// zoom : la calculette seule (bascule + résultat + écart de négociation lisibles)
await p.locator('[data-calculette]').screenshot({ path: `${OUT}/ui_achat_max_calculette.png` })
console.log('mode achat_max OK (écart demandé − max affiché)')
await b.close()
