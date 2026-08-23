// §2 — capture du menu Outils APRÈS : liste plate (plus de catégories), gabarit unique,
// barre verticale gauche pour chaque outil, ordre d'usage probable.
// Usage : BASE=http://localhost:5174/socle/ node qa/lot-ui/s2-menu.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://localhost:5174/socle/').replace(/\/?$/, '/')
const OUT = new URL('./captures', import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(30000)

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.locator('button[title="Outils"]').click()
  await page.locator('[data-outil]').first().waitFor()
  await page.waitForTimeout(600)

  // ordre effectif rendu + absence de catégories/étoile
  const order = await page.locator('[data-outil]').evaluateAll((els) => els.map((e) => e.getAttribute('data-outil')))
  const groups = await page.locator('[data-outil-group]').count()
  const stars = await page.locator('[data-outil-phare]').count()
  console.log('ordre rendu :', order.join(' → '))
  console.log('catégories (data-outil-group) :', groups, '· étoiles phare (data-outil-phare) :', stars)

  await page.locator('aside:has([data-outil])').screenshot({ path: `${OUT}/s2-menu-plat.png` })
  console.log('📸 s2-menu-plat.png →', OUT)
} catch (e) {
  console.error('ÉCHEC :', String(e).slice(0, 400))
  await page.screenshot({ path: `${OUT}/s2-echec.png` }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
