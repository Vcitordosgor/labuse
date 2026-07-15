// M11 · SURFACE A — captures de la barre de fiche (playwright). LECTURE SEULE (sauf quota DB).
// node frontend/qa/capture_surface_a.mjs
import { chromium } from 'playwright'
import { execSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'

const BASE = process.env.BASE || 'http://127.0.0.1:8023/socle/'
const IDU = process.env.IDU || '97423000AB1908'
const OUT = 'reports/m11-ia/captures'
const DBURL = 'postgresql://openclaw@localhost/labuse'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })

async function openFiche() {
  await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(2000)
  await page.fill('input[title^="Recherche du dashboard"]', IDU)
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-askbar]', { timeout: 20000 })
  await page.waitForTimeout(1000)
}

async function ask(text, { chip } = {}) {
  if (chip) {
    await page.locator(`[data-askbar] button:has-text(${JSON.stringify(chip)})`).first().click()
  } else {
    await page.fill('[data-askbar] input', text)
    await page.locator('[data-askbar] button:has-text("Demander")').click()
  }
  // attend la fin du chargement (« L'IA lit la fiche… » disparaît)
  await page.waitForFunction(() => {
    const el = document.querySelector('[data-askbar]')
    return el && !/lit la fiche/.test(el.textContent || '') && /Sourcé|Estimé|Absent|disponible|limite/.test(el.textContent || '')
  }, { timeout: 45000 }).catch(() => {})
  await page.waitForTimeout(800)
}

async function shot(name) {
  const bar = page.locator('[data-askbar]')
  await bar.screenshot({ path: `${OUT}/${name}.png` })
  console.log('capture:', name)
}

await openFiche()
await shot('01-barre-vide')                                  // la barre au repos (chips + champ premium)

await ask('Quelle est la zone PLU de cette parcelle ?')      // zonage → cité SOURCÉ (plus de déduction)
await shot('02-reponse-sourcee')                             // réponse SOURCÉE + étiquettes de provenance

await ask("Y a-t-il de l'amiante dans le bâti ?")
await shot('03-reponse-absent')                              // hors-données → « non disponible » (Absent)

// quota : on sature le compteur du sujet courant (dev) puis on repose une question
try {
  execSync(`psql "${DBURL}" -c "UPDATE ia_ask_quota SET n=20 WHERE idu='${IDU}';"`, { stdio: 'ignore' })
  await ask('Une question de plus au-delà du quota ?')
  await shot('04-quota-atteint')
} catch (e) { console.log('quota capture skip:', e.message) }

await browser.close()
console.log('DONE')
