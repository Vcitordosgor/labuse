import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8042/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-acde36dc69fe81f54/qa/m14/D'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForTimeout(1500)

const input = page.locator('[data-omnibox]')
await input.waitFor({ state: 'visible' })

// --- D1 : placeholder ---
const placeholder = await input.getAttribute('placeholder')
console.log('D1 placeholder =', JSON.stringify(placeholder))
const EXPECTED = 'Rechercher : IDU, adresse exacte, commune…'
console.log('D1 match =', placeholder === EXPECTED)

// screenshot du champ de recherche (zone header)
const header = page.locator('header')
await header.screenshot({ path: `${OUT}/d1_placeholder.png` })

// --- D2 : clic à l'extrême droite du champ focus l'input ---
// On mesure la boundingBox du wrapper visible de la barre (le div omnibox englobant),
// puis on clique proche du bord droit de la ZONE INPUT (avant la loupe).
const box = await input.boundingBox()
console.log('D2 input boundingBox =', JSON.stringify(box))

// s'assurer qu'on ne part pas déjà focus
await page.evaluate(() => document.activeElement?.blur())
await page.waitForTimeout(100)
const before = await page.evaluate(() => document.activeElement?.getAttribute?.('data-omnibox') != null)
console.log('D2 focus AVANT clic =', before)

// clic à l'extrême droite de l'input : x + width - 8
const clickX = box.x + box.width - 8
const clickY = box.y + box.height / 2
await page.mouse.click(clickX, clickY)
await page.waitForTimeout(200)

const after = await page.evaluate(() => document.activeElement?.getAttribute?.('data-omnibox') != null)
console.log('D2 focus APRÈS clic droite (x=' + clickX.toFixed(0) + ') =', after)

// preuve visuelle : marqueur du point de clic + focus visible
await page.evaluate(({ x, y }) => {
  const dot = document.createElement('div')
  dot.style.cssText = `position:fixed;left:${x - 6}px;top:${y - 6}px;width:12px;height:12px;border-radius:50%;background:#ff3b6b;z-index:99999;box-shadow:0 0 0 3px rgba(255,59,107,.35);pointer-events:none`
  document.body.appendChild(dot)
}, { x: clickX, y: clickY })
await page.waitForTimeout(150)
await header.screenshot({ path: `${OUT}/d2_clic_droite.png` })

console.log('RESULT D1_PASS=' + (placeholder === EXPECTED) + ' D2_PASS=' + (after === true))
await browser.close()
