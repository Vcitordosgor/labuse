// FIX IA-FICHE UX — barre repliable (3 états) + bouton IA retiré + chips enrichis + réponse aménités.
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/pre-lancement/captures'
const IDU = '97415000EL0387'
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 430, height: 950 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 10000 })
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
await p.waitForSelector('[data-askbar]', { timeout: 10000 })
await p.waitForTimeout(1000)

// État 1 — REPLIÉ (défaut) : la fiche est pleinement visible, juste le bouton
const collapsed = await p.locator('[data-askbar-open]').count()
const iaBtn = await p.locator('button[title="Analyse IA"]').count()
console.log('état replié : bouton "Demander" =', collapsed > 0, '| vieux bouton IA présent =', iaBtn, '(attendu 0)')
await p.locator('aside:has([data-askbar])').first().screenshot({ path: `${OUT}/fixIA-replie.png` })

// État 2 — DÉPLIÉ : clic → champ + chips enrichis
await p.locator('[data-askbar-open]').click()
await p.waitForSelector('[data-askbar-close]', { timeout: 5000 })
await p.waitForTimeout(400)
const chips = await p.locator('[data-askbar] button').allInnerTexts()
console.log('chips dépliés :', chips.filter((c) => c.length > 3).slice(0, 8))
await p.locator('aside:has([data-askbar])').first().screenshot({ path: `${OUT}/fixIA-deplie.png` })

// État 3 — APRÈS RÉPONSE : cliquer "équipements à proximité"
await p.locator('[data-askbar] button:has-text("équipements à proximité")').click()
await p.waitForSelector('[data-askbar] .whitespace-pre-wrap', { timeout: 20000 })
await p.waitForTimeout(600)
const rep = (await p.locator('[data-askbar]').innerText()).replace(/\s+/g, ' ')
console.log('réponse (extrait) :', rep.slice(rep.indexOf('Oui') >= 0 ? rep.indexOf('Oui') : 0, 160))
console.log('étiquette aménités présente :', /proximit/i.test(rep))
await p.locator('aside:has([data-askbar])').first().screenshot({ path: `${OUT}/fixIA-apres-reponse.png` })

// repli après usage
await p.locator('[data-askbar-close]').click()
await p.waitForTimeout(400)
console.log('après ✕ fermer : bouton "Demander" de retour =', await p.locator('[data-askbar-open]').count() > 0)
await b.close()
console.log('captures IA-fiche OK')
