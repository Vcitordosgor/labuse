// RECETTE-9 — helper de capture (playwright/chromium). Front dev :5199 (/socle/), API :8031.
// Usage : node _recette9_capture.mjs <recette> [idu]
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg

const BASE = 'http://localhost:5199/socle/'
const OUT = new URL('../docs/audit-2026-09/RECETTE-9-preuves/captures/', import.meta.url).pathname
const [, , recette, idu = '97411000EL0157'] = process.argv

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0, 200)) })

async function ready() {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
}
async function openFiche(id) {
  await page.evaluate((i) => window.__labuse.select(i), id)
  await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 })
  await page.waitForTimeout(1200)
}
async function shot(name) {
  await page.screenshot({ path: `${OUT}${name}.png` })
  console.log('CAPTURE', `${OUT}${name}.png`)
}

await ready()

if (recette === 't1') {
  await openFiche(idu)
  // ouvre le questionnaire Financier
  await page.click('[data-banquier-btn]')
  await page.waitForSelector('[data-financier-questionnaire]', { timeout: 10000 })
  await page.waitForTimeout(400)
  // écran 0 : choisir « Construction neuve »
  await page.click('[data-usage="construction"]')
  await page.waitForSelector('[data-financier-etapes]', { timeout: 10000 })
  await page.waitForTimeout(500)
  // écran 1 « Votre projet » : bannière programme + logements « indispensable » + étapes cliquables
  await shot('T1-questionnaire-etape1-indispensable')
  // saisir un nombre de logements pour prouver la conservation à la nav
  const numInputs = page.locator('[data-financier-questionnaire] input[type="number"]')
  await numInputs.first().fill('8')
  await page.waitForTimeout(200)
  // aller à l'étape 2 via le fil d'étapes cliquable, puis revenir à l'étape 1
  await page.click('[data-financier-etapes] [data-etape="1"]')
  await page.waitForTimeout(400)
  await shot('T1-questionnaire-etape2')
  await page.click('[data-financier-etapes] [data-etape="0"]')
  await page.waitForTimeout(400)
  await shot('T1-questionnaire-retour-etape1-saisie-conservee')
}

if (recette === 't7') {
  await openFiche(idu)
  // cadre les actions + la grille des 6 boutons (bas du tiroir)
  const actions = page.locator('.actions').first()
  await actions.scrollIntoViewIfNeeded()
  await page.waitForTimeout(500)
  // capture rognée autour de la zone boutons
  const box = await actions.boundingBox()
  if (box) {
    await page.screenshot({ path: `${OUT}${process.env.SHOT || 'T7-boutons'}.png`,
      clip: { x: box.x - 8, y: box.y - 8, width: box.width + 16, height: 210 } })
    console.log('CAPTURE', `${OUT}${process.env.SHOT || 'T7-boutons'}.png`)
  }
}

if (recette === 't6') {
  await openFiche(idu)
  // ouvre « Remonter le temps » depuis la fiche
  await page.click('[data-temps-tile]')
  await page.waitForFunction(() => window.__labuse_tm != null, { timeout: 15000 })
  // laisse le temps au pin + à la géométrie cible de se charger
  await page.waitForTimeout(4000)
  // inspection PROGRAMMATIQUE : la source `cible` porte-t-elle une feature sur les deux volets ?
  const diag = await page.evaluate(() => {
    const tm = window.__labuse_tm
    const cnt = (m) => { try { return (m.getSource('cible')?._data?.features || []).length } catch { return 'n/a' } }
    const paint = (m) => { try { return m.getPaintProperty('cible', 'line-color') } catch { return 'n/a' } }
    return { pinIdu: window.__labuse_store?.tempsPinIdu ?? '(?)',
             pastFeatures: cnt(tm.past), nowFeatures: cnt(tm.now),
             color: paint(tm.past) }
  })
  console.log('T6-DIAG', JSON.stringify(diag))
  await page.waitForTimeout(1500)
  await shot('T6-remonter-le-temps-contour')
  // glisse la poignée pour montrer le contour des DEUX côtés
  const handle = page.locator('[title="Glisser pour comparer"]')
  const box = await handle.boundingBox()
  if (box) {
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2)
    await page.mouse.down(); await page.mouse.move(box.x - 300, box.y + box.height / 2, { steps: 10 }); await page.mouse.up()
    await page.waitForTimeout(800)
    await shot('T6-remonter-le-temps-contour-poignee-gauche')
  }
}

await browser.close()
