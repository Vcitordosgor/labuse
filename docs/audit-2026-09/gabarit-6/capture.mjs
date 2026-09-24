// GABARIT-6 — captures de recette (lecture seule). Node playwright direct (MCP indispo).
// Lancer : node docs/audit-2026-09/gabarit-6/capture.mjs
import pw from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright-core/index.js'
const { chromium } = pw

const BASE = 'http://localhost:5595/socle/'
const OUT = '/Users/openclaw/Desktop/labuse-gabarit6/docs/audit-2026-09/gabarit-6/captures'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' })
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('console', (m) => { if (m.type() === 'error') console.log('  [console.error]', m.text().slice(0, 120)) })

async function ficheHeader(idu, name) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await sleep(2500)
  await page.evaluate((i) => window.__labuse.select(i), idu)
  await page.waitForSelector('.fiche-v6', { timeout: 20000 })
  await sleep(4500) // laisser le fetch gabarit (en-tête) résoudre
  const aside = await page.$('.fiche-v6')
  await aside.screenshot({ path: `${OUT}/${name}.png` })
  console.log('OK', name)
}

async function outil(idu, name, { expand3d = false, mapShot = false, clickNonInt = false } = {}) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await sleep(1500)
  await page.evaluate((i) => { window.__labuse.select(i); window.__labuse.setModule('gabarit') }, idu)
  await page.waitForSelector('[data-gabarit-panel]', { timeout: 20000 })
  await sleep(4500) // fetch gabarit + rendu carte
  if (clickNonInt) {
    const d = await page.$('[data-gabarit-non-integrees]')
    if (d) { await d.scrollIntoViewIfNeeded(); }
  }
  const panel = await page.$('[data-gabarit-panel]')
  await panel.screenshot({ path: `${OUT}/${name}-panneau.png` })
  console.log('OK', name, '(panneau)')
  if (mapShot) {
    await page.screenshot({ path: `${OUT}/${name}-carte-2d.png` })
    console.log('OK', name, '(carte 2D)')
    const b3d = await page.$('button[aria-label="Relief 3D"]')
    if (b3d) {
      await b3d.click(); await sleep(4000)
      await page.screenshot({ path: `${OUT}/${name}-carte-3d.png` })
      console.log('OK', name, '(carte 3D)')
    } else console.log('!! bouton 3D introuvable')
  }
}

try {
  await ficheHeader('97415000BW0102', 'p1-fiche-entete-BW0102')
  await ficheHeader('97411000BZ1065', 'p1-fiche-entete-BZ1065')
  await outil('97415000BW0102', 'p2-outil-BW0102')
  await outil('97411000AK0069', 'p3-outil-Ud-AK0069', { clickNonInt: true })
  await outil('97411000BZ1065', 'p4-outil-BZ1065', { mapShot: true })
} catch (e) {
  console.error('CAPTURE FAIL:', e.message)
} finally {
  await browser.close()
}
