// M55-I — captures des 5 points + sondes non-régression (dev server :5173).
// Usage : cd frontend && node qa/m55i_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = process.env.OUT || '../reports/m55-i/captures'
const BASE = process.env.BASE || 'http://localhost:5173/socle/'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
const shot = (loc, name) => loc.screenshot({ path: `${OUT}/${name}.png` }).catch((e) => console.log(`✗ ${name}: ${e.message.split('\n')[0]}`))

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2200)
const aside = page.locator('aside').first()

// I1 : accueil entier (logo visible)
await shot(aside, 'i1_apres_accueil')

// I2 : deux états (déjà capturés en i2_*), on re-shoote B pour la cohérence
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(500)

// rituel 3,0 s
const t0 = Date.now()
await page.locator('[data-analyser-btn]').click()
await page.locator('[data-voir-parcelles]').waitFor({ timeout: 10000 })
const rituel = Date.now() - t0
await page.locator('[data-voir-parcelles]').click()
await page.locator('[data-results-scroll] > button').first().waitFor({ timeout: 30000 })
await page.waitForTimeout(2000)

// I3 : deux tris seulement · I5 : badges sans rang · I10-héritage : ventilation bouclée
const tris = await page.locator('[data-tri-bar] [data-sort]').allInnerTexts()
const chips = await page.locator('[data-tier-chip]').allInnerTexts()
const badgesAvecRang = chips.filter(c => /·\s*\d/.test(c)).length
const groupes = [...new Set(chips.map(c => c.split(' ·')[0]))].join(' → ')
const vent = await page.locator('[data-results-panel] p.mt-3').first().innerText()
await shot(aside, 'i3_i5_liste')

// I4 : les deux libellés
const haut = await page.locator('[data-algo-open]').innerText().catch(() => 'absent')
const bas = await page.locator('[data-comprendre-btn]').innerText().catch(() => 'absent')

// récit unique : la ventilation de la ligne résultats == la phrase de Révélation ?
// on relit la Révélation en ré-ouvrant Filtres et relançant (déjà vu : mêmes nombres, source getFiltre)
console.log('── SONDES M55-I ──')
console.log('rituel (clic→Voir):', rituel, 'ms (cible 3000 + réseau)')
console.log('I3 tris:', JSON.stringify(tris))
console.log('I4 haut:', JSON.stringify(haut), '· bas:', JSON.stringify(bas))
console.log('I5 badges avec rang (attendu 0):', badgesAvecRang)
console.log('groupement (uniq):', groupes)
console.log('ventilation:', vent.replace(/\n/g, ' '))

// carte == liste (M55-G) : Salazie + procédure
const p2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await p2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 }); await p2.waitForTimeout(2000)
await p2.locator('[data-filtres-toggle]').click(); await p2.waitForTimeout(600)
await p2.locator('button:has-text("97433")').first().click(); await p2.waitForTimeout(500)
await p2.locator('[data-signaux-vie] button:has-text("Procédure collective")').click(); await p2.waitForTimeout(1000)
await p2.locator('[data-analyser-btn]').click(); await p2.waitForTimeout(3800)
await p2.locator('[data-voir-parcelles]').click(); await p2.waitForTimeout(2500)
await p2.evaluate(() => window.__labuse_map.flyTo({ center: [55.54, -21.03], zoom: 13, duration: 0 }))
await p2.waitForTimeout(3500)
const peintes = await p2.evaluate(() => new Set(window.__labuse_map.queryRenderedFeatures({ layers: ['ile-fill'] }).map(f => f.properties?.idu)).size)
const pied = await p2.locator('[data-results-panel]').innerText()
console.log('carte==liste — liste:', (pied.match(/(\d[\d\s ]*) affichée/) || [,'?'])[1], '· peintes:', peintes)
await p2.close()

// mobile
await page.setViewportSize({ width: 375, height: 720 })
await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
await page.locator('[data-couches-mobile]').click(); await page.waitForTimeout(800)
await page.screenshot({ path: `${OUT}/nr_mobile.png` })

console.log('captures OK →', OUT, '· console errors:', errors.length)
console.log(errors.slice(0, 4).join('\n'))
await browser.close()
