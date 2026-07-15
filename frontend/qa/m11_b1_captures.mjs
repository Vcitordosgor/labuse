// M11 · SURFACE B1 — captures front de la bannière « critères non appliqués ».
// Prérequis : backend dev servant dist/ sur 8021 (LABUSE_DEV_MODE=1). Front reçoit la vraie réponse /ia/search.
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8021/socle/'
const OUT = '../reports/m11-ia/captures'

const CAS = [
  { file: 'b1-1-mistraduction-passoire.png',
    q: 'les passoires thermiques classées G à Saint-Denis',
    attend: 'bannière DPE, PAS de flag risques' },
  { file: 'b1-2-drop-personne-morale.png',
    q: 'les brûlantes de Saint-Pierre avec un propriétaire personne morale',
    attend: 'bannière personne morale + tier/commune appliqués' },
  { file: 'b1-3-non-regression.png',
    q: 'les chaudes de Saint-Paul de plus de 800 m2',
    attend: 'aucune bannière, seulement ✓ appliqué' },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } })
page.on('console', (m) => { if (m.type() === 'error') console.log('  [console.error]', m.text()) })

for (const c of CAS) {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 10000 })
  await page.evaluate(() => window.__labuse.setView('ia'))
  const input = page.locator('[data-porte-recherche] input')
  await input.waitFor({ state: 'visible', timeout: 8000 })
  await input.fill(c.q)
  await page.locator('[data-porte-recherche] button:has-text("Chercher")').click()
  // apply() bascule sur la carte + pose la restitution — c'est LÀ que la bannière s'affiche
  await page.waitForSelector('[data-ia-restitution]', { timeout: 15000 })
  await page.waitForTimeout(1200)   // vol caméra + compteur animé
  await page.screenshot({ path: `${OUT}/${c.file}`, fullPage: false })
  const banner = await page.locator('[data-ia-non-appliques]').count()
  const txt = banner ? (await page.locator('[data-ia-non-appliques]').innerText()).replace(/\s+/g, ' ') : '—'
  console.log(`✓ ${c.file}  (bannière: ${banner > 0}) ${txt}  — ${c.attend}`)
}

await browser.close()
console.log('captures OK')
