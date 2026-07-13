// M6 Phase 2a — A-01 : vignettes ortho des 20 parcelles échantillon « emprise routière probable »
// (vérification à l'œil AVANT application globale de l'exclusion — garde-fou Vic).
// Usage : cd frontend && BASE=http://127.0.0.1:8010/socle/ node qa/m6_2a_a01_vignettes.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m6-audit/captures-2a-a01'
mkdirSync(OUT, { recursive: true })

const IDUS = [
  '97409000AS2098', '97414000CV1011', '97416000IE1899',
  '97407000BA0396', '97408000AN0517', '97409000AI0895', '97409000BD1301', '97409000BH0288',
  '97419000AD0133', '97420000AV0607', '97416000DZ0456', '97413000CX1189', '97402000AB0984',
  '97411000BE0651', '97409000AE0436', '97412000BR0775', '97412000CZ0975', '97410000AB0343',
  '97411000EX0027', '97410000AK0712',
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1100, height: 800 } })
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2500)

// fond ortho (dropdown fond de plan → « Ortho IGN »)
try {
  await page.locator('button[title="Fond de plan"]').click()
  await page.waitForTimeout(400)
  await page.locator('button:text-is("Ortho IGN")').click()
  await page.waitForTimeout(2500)
} catch (e) { console.log('WARN fond ortho:', e.message.slice(0, 80)) }

for (const idu of IDUS) {
  try {
    await page.fill('input[title^="Recherche du dashboard"]', idu)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(4500)
    await page.screenshot({ path: `${OUT}/a01-${idu}.png` })
    console.log('OK', idu)
  } catch (e) { console.log('FAIL', idu, e.message.slice(0, 100)) }
}
await browser.close()
