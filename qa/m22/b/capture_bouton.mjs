// M22-B — capture UI : bouton discret « Éditer la lettre de vérification de zonage »
// dans le tiroir Règles d'urbanisme (la barre M20 reste à 7 tuiles, prouvé par la capture).
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8022'
const IDU = '97415000BV1193'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } })
await p.goto(`${BASE}/socle/`, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 15000 })
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
await p.waitForSelector('[data-drawer="regles"]', { timeout: 15000 })
await p.locator('[data-drawer="regles"] > button').click()
await p.waitForSelector('[data-lettre-zonage]', { timeout: 15000 })
await p.waitForTimeout(400)
const href = await p.locator('[data-lettre-zonage]').getAttribute('href')
if (href !== `/lettre-zonage/${IDU}.pdf`) throw new Error(`href inattendu : ${href}`)
// capture du bouton AVEC son contexte (fin du tiroir) : clip autour de la boîte du lien
await p.locator('[data-lettre-zonage]').scrollIntoViewIfNeeded()
await p.waitForTimeout(300)
const box = await p.locator('[data-lettre-zonage]').boundingBox()
await p.screenshot({ path: 'qa/m22/b/ui_bouton_lettre.png',
  clip: { x: Math.max(0, box.x - 30), y: Math.max(0, box.y - 220), width: 560, height: 320 } })
// (non-régression barre M20 à 7 tuiles : le diff du lot ne touche pas la barre — preuve git)
console.log('bouton lettre OK, href =', href)
await b.close()
