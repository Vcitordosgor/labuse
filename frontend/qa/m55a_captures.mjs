// M55-A — captures de validation (items 4 & 5). LECTURE via le dev server vite (:5173, HMR
// → reflète le working tree). Usage : cd frontend && node qa/m55a_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://localhost:5173/socle/'
const OUT = process.env.OUT || '../reports/m55-a-couches/captures'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)

// ── item 5 : flèche de la section « Couches » — repliée (gauche) vs dépliée (bas) ──
const toggle = page.locator('[data-couches-toggle]').first()
await toggle.waitFor({ timeout: 15000 })
// état par défaut = DÉPLIÉ (flèche bas)
await page.locator('aside').first().screenshot({ path: `${OUT}/item5_panel_deplie.png` })
await toggle.locator('span[aria-hidden="true"]').screenshot({ path: `${OUT}/item5_fleche_deplie.png` })
// replier → flèche GAUCHE
await toggle.click()
await page.waitForTimeout(500)
await page.locator('aside').first().screenshot({ path: `${OUT}/item5_panel_replie.png` })
await toggle.locator('span[aria-hidden="true"]').screenshot({ path: `${OUT}/item5_fleche_replie.png` })
// rouvrir pour la suite
await toggle.click()
await page.waitForTimeout(400)

console.log('item5 OK. console errors:', errors.length)
console.log(errors.slice(0, 5).join('\n'))
await browser.close()
