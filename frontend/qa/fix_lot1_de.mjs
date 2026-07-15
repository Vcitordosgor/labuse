// FIX LOT 1 — captures D (patrimoine message vide) et E (simulateur PLU cliquable).
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 950 } })

// D — scan patrimoine : boîte absente → message clair
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setModule, { timeout: 10000 })
await p.evaluate(() => window.__labuse.setModule('patrimoine'))
await p.waitForSelector('input[placeholder*="SIREN"]', { timeout: 10000 })
await p.locator('input[placeholder*="SIREN"]').fill('VISHOR MATERIAUX')
await p.waitForSelector('[data-m02-vide]', { timeout: 10000 })
console.log('D message:', (await p.locator('[data-m02-vide]').innerText()).replace(/\s+/g, ' ').slice(0, 120))
await p.locator('aside').first().screenshot({ path: `${OUT}/fixD-patrimoine-vide.png` })

// D bis — boîte AVEC foncier → suggestions normales (non-régression)
await p.locator('input[placeholder*="SIREN"]').fill('CBO')
await p.waitForTimeout(1200)
const sug = await p.locator('aside button:has-text("parc.")').count()
console.log('D-bis AJP suggestions:', sug, '(>0 attendu)')

// E — simulateur PLU : liste cliquable → fiche s'ouvre (commune requise pour des candidats)
await p.evaluate(() => window.__labuse.setCommune('Saint-Denis'))
await p.waitForTimeout(500)
await p.evaluate(() => window.__labuse.setModule('simulplu'))
await p.waitForSelector('button:has-text("→ U")', { timeout: 10000 })
await p.waitForTimeout(500)
await p.locator('button:has-text("→ U")').first().click()
await p.waitForTimeout(3000)
console.log('aside après clic zone (extrait):', (await p.locator('aside').first().innerText()).replace(/\s+/g, ' ').slice(0, 160))
await p.waitForSelector('[data-m15-item]', { timeout: 20000 })
await p.waitForTimeout(600)
await p.locator('aside').first().screenshot({ path: `${OUT}/fixE-simulplu-liste.png` })
const idu0 = await p.locator('[data-m15-item]').first().innerText()
await p.locator('[data-m15-item]').first().click()
await p.waitForTimeout(1500)
// une fiche parcelle s'ouvre-t-elle ? (aside fiche avec IDU 14 car)
const opened = await p.locator('aside:has-text("m²")').count()
console.log('E clic sur', idu0.replace(/\s+/g, ' ').slice(0, 30), '→ fiche ouverte:', opened > 0)
await p.screenshot({ path: `${OUT}/fixE-simulplu-clic-fiche.png` })
await b.close()
console.log('captures D/E OK')
