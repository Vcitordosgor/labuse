// RECETTE-8 — helper de capture (playwright/chromium). Front dev :5199 (/socle/), API :8031.
// Usage : node _recette8_capture.mjs <nom> <recette|action> [idu]
import { chromium } from 'playwright'

const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/RECETTE-8-preuves/captures/', import.meta.url).pathname

const [, , nom, action, idu = '97411000EL0157'] = process.argv

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 160)) })

async function ready() {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => (window).__labuse != null, { timeout: 20000 })
}

async function openFiche(id) {
  await page.evaluate((i) => (window).__labuse.select(i), id)
  await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 })
  await page.waitForTimeout(1500)
}

async function shot(name) {
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: false })
  console.log('CAPTURE', `${OUT}${name}.png`)
}

await ready()

if (action === 'fiche-head') {
  await openFiche(idu)
  await shot(nom)
} else if (action === 'fiche-head-hover-i') {
  await openFiche(idu)
  // survole le premier « i » des tuiles de tête pour montrer l'infobulle
  const i = page.locator('[data-bandeau-chiffres] .stat-l [role="button"]').first()
  await i.hover()
  await page.waitForTimeout(700)
  await shot(nom)
} else if (action === 'fiche-scroll') {
  await openFiche(idu)
  await page.evaluate(() => {
    const sc = document.querySelector('aside.fiche-v6 .flex.min-h-0.flex-1.overflow-y-auto') ||
               document.querySelector('aside.fiche-v6 [class*="overflow-y-auto"]')
    if (sc) sc.scrollTop = 320
  })
  await page.waitForTimeout(600)
  await shot(nom)
} else if (action === 'map') {
  await page.waitForTimeout(2500)
  await shot(nom)
} else if (action === 'temps') {
  await page.evaluate(() => (window).__labuse.setModule('temps'))
  await page.waitForTimeout(1200)
  // designer la parcelle : taper l'IDU dans le ParcelInput du panneau (dataAttr temps-idu)
  const inp = page.locator('[data-temps-idu] input, input[data-temps-idu], [data-parcel-input="temps-idu"] input').first()
  try { await inp.fill(idu); await page.keyboard.press('Enter') } catch (e) { console.error('fill', String(e).slice(0,80)) }
  await page.waitForTimeout(5000)
  await shot(nom)
} else {
  await page.waitForTimeout(1200)
  await shot(nom)
}

await browser.close()
