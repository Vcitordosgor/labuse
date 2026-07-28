// M26-B · Point B — capture de l'état 1 branché sur un RUN RÉEL (SSE bout en bout).
// Parcours : vue Copilote → brief → Instruire → attendre run_completed → capture.
// Usage : node qa/m26b_etat1_capture.mjs  (API :8000 et vite :5173 démarrés)
import { chromium } from 'playwright'

const BASE = 'http://localhost:5173/socle/'
const OUT = 'qa/captures'
const BRIEF = 'Terrain pour un collectif de 6 logements à Saint-Paul, budget foncier 480 k€, hors zone rouge PPR'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 1000 } })
p.on('console', (m) => { if (m.type() === 'error') console.log('console error:', m.text()) })
await p.goto(BASE, { waitUntil: 'networkidle' })

// entrer dans la vue Copilote par le rail (comme un utilisateur)
await p.click('nav button:has-text("Copilote")')
await p.waitForSelector('[data-copilote]')
await p.fill('[data-brief]', BRIEF)
await p.screenshot({ path: `${OUT}/m26b-00-console.png` })

console.log('instruction lancée —', new Date().toISOString())
await p.click('[data-instruire]')
await p.waitForSelector('[data-en-cours]', { timeout: 15000 })
await p.screenshot({ path: `${OUT}/m26b-01-en-cours.png` })

// le run réel prend ~1 min (mesure M26-A : 56 s exhaustif)
await p.waitForSelector('[data-resultats]', { timeout: 180000 })
console.log('run terminé —', new Date().toISOString())
await p.waitForTimeout(400)

await p.screenshot({ path: `${OUT}/m26b-02-etat1-haut.png` })
await p.screenshot({ path: `${OUT}/m26b-03-etat1-page.png`, fullPage: true })

// journal ouvert (bloc livrable)
await p.click('[data-journal-ouvrir]')
await p.waitForSelector('[data-journal]')
await p.locator('[data-journal]').scrollIntoViewIfNeeded()
await p.screenshot({ path: `${OUT}/m26b-04-journal.png` })

// vérifications rapides consignées dans la sortie
const nRestituees = await p.locator('[data-restituee]').count()
const autres = await p.locator('[data-autres-retenues]').textContent().catch(() => null)
const badges = await p.locator('[data-badge]').allTextContents()
console.log('restituées rendues:', nRestituees)
console.log('autres retenues:', (autres ?? 'ABSENT').trim())
console.log('badges:', badges.join(' | '))
await b.close()
