// PROJET PARCOURS — parcours de sélection Tinder (Phase 1).
// Preuves : tri (carte en fond + carte de décision), retenir/écarter, sections retenues/écartées,
// récupération d'une écartée (réversible), reprise (quitter/rouvrir → état conservé).
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/pre-lancement/captures'
const NOM = 'Résidence étudiante Saint-Paul'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 860 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 10000 })

// aller aux projets, lancer le tri sur le projet Saint-Paul
await p.evaluate(() => window.__labuse.setView('projets'))
await p.waitForSelector('[data-projets-liste]', { timeout: 10000 })
const card = p.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
await card.locator('[data-projet-trier]').click()

// 1) le tri : carte en fond + carte de décision
await p.waitForSelector('[data-decision-card]', { timeout: 15000 })
await p.waitForTimeout(2500) // tuiles + points clés
const prog0 = (await p.locator('[data-parcours-progress]').innerText()).replace(/\s+/g, ' ')
console.log('progression initiale:', prog0)
await p.screenshot({ path: `${OUT}/parcours-1-tri.png` })

// 2) une action RETENIR puis une action ÉCARTER (sur la parcelle suivante)
await p.locator('[data-decision-retenir]').click()
await p.waitForTimeout(1200)
await p.screenshot({ path: `${OUT}/parcours-2-apres-retenir.png` })
await p.locator('[data-decision-ecarter]').click()
await p.waitForTimeout(1000)
// quelques décisions de plus pour peupler les sections
await p.locator('[data-decision-retenir]').click(); await p.waitForTimeout(700)
await p.locator('[data-decision-ecarter]').click(); await p.waitForTimeout(700)
const prog1 = (await p.locator('[data-parcours-progress]').innerText()).replace(/\s+/g, ' ')
console.log('progression après 4 décisions:', prog1)

// 3) sections retenues + écartées
await p.locator('[data-parcours-sections]').click()
await p.waitForSelector('[data-section-ecartees]', { timeout: 5000 })
await p.waitForTimeout(500)
await p.screenshot({ path: `${OUT}/parcours-3-sections.png` })

// 4) RÉCUPÉRATION d'une écartée (réversible) — la boussole
const recuperer = p.locator('[data-recuperer]').first()
const avantEcartees = await p.locator('[data-section-ecartees] > div').count()
await recuperer.click()
await p.waitForTimeout(1200)
const apresEcartees = await p.locator('[data-section-ecartees] > div').count()
console.log(`écartées: ${avantEcartees} → ${apresEcartees} (récupération)`)
await p.screenshot({ path: `${OUT}/parcours-4-recuperation.png` })
// fermer le tiroir (son ✕ dédié — l'overlay intercepte sinon)
await p.locator('[data-sections-close]').click()
await p.waitForTimeout(400)

// 5) REPRISE : quitter puis rouvrir → l'état est conservé
await p.locator('[data-parcours-quitter]').click()
await p.waitForSelector('[data-projets-liste]', { timeout: 8000 })
await card.locator('[data-projet-trier]').click()
await p.waitForSelector('[data-parcours-progress]', { timeout: 15000 })
await p.waitForTimeout(2500)
const progReprise = (await p.locator('[data-parcours-progress]').innerText()).replace(/\s+/g, ' ')
console.log('progression à la REPRISE:', progReprise)
await p.screenshot({ path: `${OUT}/parcours-5-reprise.png` })

await b.close()
console.log('captures parcours OK')
