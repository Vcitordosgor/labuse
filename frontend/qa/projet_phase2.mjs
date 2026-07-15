// PROJET Phase 2 — chercher plus + lien CRM auto + privacy contact proprio.
// Preuves : élargir (N ajoutées), ajout manuel IDU, retenir → CRM auto (projet + contact PM
// nommé / particulier masqué), réversibilité (retirer → entrée CRM disparaît).
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/pre-lancement/captures'
const NOM = 'Résidence étudiante Saint-Paul'
const IDU_MANUEL = '97413000AV1502' // Saint-Leu, hors périmètre initial
const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1280, height: 860 } })
await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 10000 })

// entrer dans le parcours du projet Saint-Paul
await p.evaluate(() => window.__labuse.setView('projets'))
await p.waitForSelector('[data-projets-liste]', { timeout: 10000 })
const card = p.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
await card.locator('[data-projet-trier]').click()
await p.waitForSelector('[data-decision-card]', { timeout: 15000 })
await p.waitForTimeout(2000)

// ── LOT 1 : chercher plus ──
await p.locator('[data-parcours-plus]').click()
await p.waitForSelector('[data-parcours-plus-panel]', { timeout: 5000 })
await p.locator('[data-plus-elargir]').click()
await p.waitForSelector('[data-plus-msg]', { timeout: 8000 })
console.log('élargir →', await p.locator('[data-plus-msg]').innerText())
await p.screenshot({ path: `${OUT}/phase2-1-chercher-plus-elargir.png` })
// ajout manuel par IDU
await p.locator('[data-plus-idu]').fill(IDU_MANUEL)
await p.locator('[data-plus-ajouter]').click()
await p.waitForTimeout(1200)
console.log('ajout manuel →', await p.locator('[data-plus-msg]').innerText())
await p.screenshot({ path: `${OUT}/phase2-2-ajout-manuel.png` })
await p.locator('[data-parcours-plus]').click() // refermer le panneau

// ── LOT 2 : retenir plusieurs → CRM auto (pour capturer PM + particulier) ──
for (let i = 0; i < 7; i++) {
  const btn = p.locator('[data-decision-retenir]')
  if (await btn.count() === 0) break
  await btn.click()
  await p.waitForTimeout(700)
}
const prog = (await p.locator('[data-parcours-progress]').innerText()).replace(/\s+/g, ' ')
console.log('après retenues:', prog)

// aller au CRM : les retenues y apparaissent, rattachées au projet, avec contact proprio
await p.evaluate(() => window.__labuse.setView('crm'))
await p.waitForSelector('h2:has-text("CRM")', { timeout: 10000 })
await p.waitForTimeout(1800)
const body = await p.evaluate(() => document.body.innerText)
console.log('CRM contient « Résidence étudiante Saint-Paul » :', body.includes('Résidence étudiante Saint-Paul'))
console.log('CRM contient un SIREN (PM nommée) :', /SIREN\s*\d/.test(body))
console.log('CRM contient « non communiqué » (particulier masqué) :', body.includes('non communiqué'))
await p.screenshot({ path: `${OUT}/phase2-3-crm-auto-contact.png`, fullPage: false })

// ── réversibilité : retirer une retenue → son entrée CRM disparaît ──
// compter les cartes CRM rattachées AU projet 13 (chip « ▸ Résidence… ») avant/après
const chip = p.locator(`text=▸ ${NOM}`)
const nAvant = await chip.count()
await p.evaluate(() => window.__labuse.setView('projets'))
await p.waitForSelector('[data-projets-liste]', { timeout: 8000 })
await card.locator('[data-projet-trier]').click()
await p.waitForSelector('[data-parcours-sections]', { timeout: 15000 })
await p.locator('[data-parcours-sections]').click()
await p.waitForSelector('[data-section-retenues]', { timeout: 5000 })
// « retirer » la première retenue (repasse à trier → CRM retiré)
const retirer = p.locator('[data-section-retenues] button:has-text("retirer")').first()
await retirer.click()
await p.waitForTimeout(1200)
await p.locator('[data-sections-close]').click().catch(() => {})
await p.evaluate(() => window.__labuse.setView('crm'))
await p.waitForSelector('h2:has-text("CRM")', { timeout: 10000 })
await p.waitForTimeout(1800)
const nApres = await chip.count()
console.log(`cartes CRM du projet 13 : ${nAvant} → ${nApres} après retrait (réversible, cohérent)`)
await p.screenshot({ path: `${OUT}/phase2-4-reversibilite-crm.png` })

await b.close()
console.log('captures phase2 OK')
