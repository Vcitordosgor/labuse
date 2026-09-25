// DONNEES-FIX-1 — captures « après » (node playwright ; le canvas maplibre bloque le screenshot MCP).
import pkg from '/Users/openclaw/Desktop/labuse-donneesfix/frontend/node_modules/playwright/index.js'
const { chromium } = pkg

const EXE = '/Users/openclaw/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
const BASE = 'http://localhost:5715/socle/'
const OUT = 'docs/audit-2026-09/donnees-fix-1/captures'

const shots = [
  { idu: '97411000BZ1065', drawer: 'Bâti',      file: '02-badge-apres-BZ1065.png',      marker: 'Faîtage mesuré' },
  { idu: '97418000AZ0128', drawer: 'Bâti',      file: '07-badge-apres-aberration.png',  marker: 'Faîtage mesuré' },
  { idu: '97411000CD1214', drawer: 'Identité',  file: '04-identite-apres-SCI.png',       marker: 'non identifiable' },
  { idu: '97411000BZ1065', drawer: 'Potentiel', file: '06-potentiel-apres-BZ1065.png',   marker: 'SDP' },
]

const browser = await chromium.launch({ executablePath: EXE })
const page = await browser.newPage({ viewport: { width: 520, height: 1100 } })

for (const s of shots) {
  try {
    await page.goto(BASE, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(1500)
    await page.evaluate((idu) => window.__labuse.select(idu), s.idu)
    await page.waitForSelector('.fiche-v6', { timeout: 15000 })
    // attendre que le tiroir voulu soit RÉELLEMENT présent (fiche chargée, pas le squelette)
    await page.waitForFunction((name) =>
      [...document.querySelectorAll('.fiche-v6 button')].some(b => (b.textContent || '').trim().startsWith(name)),
      s.drawer, { timeout: 15000 })
    await page.waitForTimeout(500)
    await page.evaluate((name) => {
      const btn = [...document.querySelectorAll('.fiche-v6 button')]
        .find(b => (b.textContent || '').trim().startsWith(name))
      if (btn) btn.click()
    }, s.drawer)
    // attendre le contenu déplié (marqueur), pas le squelette
    await page.waitForFunction((m) => document.querySelector('.fiche-v6')?.innerText.includes(m),
      s.marker, { timeout: 15000 })
    await page.waitForTimeout(600)
    // masquer le canvas (fond de carte animé → screenshot instable)
    await page.evaluate(() => { document.querySelectorAll('canvas').forEach(c => c.style.display = 'none') })
    await page.waitForTimeout(300)
    const el = await page.$('.fiche-v6')
    await el.screenshot({ path: `${OUT}/${s.file}` })
    console.log(`OK ${s.file} (${s.idu} / ${s.drawer})`)
  } catch (e) {
    console.log(`FAIL ${s.file}: ${String(e).slice(0, 120)}`)
  }
}
await browser.close()
