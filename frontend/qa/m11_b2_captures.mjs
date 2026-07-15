// M11 · SURFACE B2 — captures : (a) filtre personne morale appliqué SANS signalement,
// (b) réponse agrégée chiffrée sourcée. Backend dev servant dist/ sur 8010.
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m11-ia/captures'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 950 } })

async function search(q) {
  await p.goto(BASE, { waitUntil: 'networkidle' })
  await p.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 10000 })
  await p.evaluate(() => window.__labuse.setView('ia'))
  const input = p.locator('[data-porte-recherche] input')
  await input.waitFor({ state: 'visible', timeout: 8000 })
  await input.fill(q)
  await p.locator('[data-porte-recherche] button:has-text("Chercher")').click()
}

// (a) PERSONNE MORALE — filtre appliqué → restitution sur la carte, AUCUNE bannière « non appliqués »
await search('les brûlantes de Saint-Pierre avec un propriétaire personne morale')
await p.waitForSelector('[data-ia-restitution]', { timeout: 15000 })
await p.waitForTimeout(1200)
const banner = await p.locator('[data-ia-non-appliques]').count()
console.log(`(a) PM : restitution affichée, bannière « non appliqués » présente = ${banner > 0} (attendu false)`)
await p.screenshot({ path: `${OUT}/b2-a-personne-morale-sans-signalement.png` })

// (b) AGRÉGAT — reste sur la vue IA, carte chiffrée sourcée
await search('combien de brûlantes à Saint-Paul ?')
await p.waitForSelector('[data-ia-aggregate]', { timeout: 15000 })
await p.waitForTimeout(500)
const txt = (await p.locator('[data-ia-aggregate]').innerText()).replace(/\s+/g, ' ')
console.log('(b) agrégat :', txt)
await p.locator('[data-ia-aggregate]').screenshot({ path: `${OUT}/b2-b-agregat-source.png` })

// (b bis) superlatif avec mini-classement
await search('quelle commune a le plus de brûlantes ?')
await p.waitForSelector('[data-ia-classement]', { timeout: 15000 })
await p.waitForTimeout(500)
await p.locator('[data-ia-aggregate]').screenshot({ path: `${OUT}/b2-b-classement-source.png` })
console.log('(b bis) classement capturé')

await b.close()
console.log('captures B2 OK')
