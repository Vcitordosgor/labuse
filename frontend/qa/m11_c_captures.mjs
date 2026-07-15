// M11 · SURFACE C — captures de l'onglet Faisabilité + explication IA.
import { chromium } from 'playwright'
const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/m11-ia/captures'
const IDU = '97415000EL0387'

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1300, height: 1100 } })
p.on('console', (m) => { if (m.type() === 'error') console.log('  [err]', m.text().slice(0, 120)) })

await p.goto(BASE, { waitUntil: 'networkidle' })
await p.waitForFunction(() => window.__labuse && window.__labuse.select, { timeout: 10000 })
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
// ouvrir l'onglet Faisabilité
await p.waitForSelector('button:has-text("Faisabilité")', { timeout: 10000 })
await p.locator('button:has-text("Faisabilité")').first().click()
await p.waitForSelector('[data-faisa-steps]', { timeout: 10000 })
await p.waitForTimeout(800)
const nSteps = await p.locator('[data-faisa-steps] > li').count()
console.log('onglet Faisabilité : steps affichés =', nSteps)
const fiche = p.locator('aside:has([data-faisa-explain])')
await fiche.screenshot({ path: `${OUT}/c-onglet-faisabilite.png` })

// déclencher l'explication IA
await p.locator('[data-faisa-explain-btn]').click()
await p.waitForSelector('[data-faisa-explain] .whitespace-pre-wrap', { timeout: 25000 })
await p.waitForTimeout(600)
const txt = (await p.locator('[data-faisa-explain]').innerText()).replace(/\s+/g, ' ')
console.log('explication (extrait):', txt.slice(0, 240))
console.log('marqueurs bruts ⟨ :', txt.includes('⟨'), '| ## :', txt.includes('##'), '| DVF fragile mentionné :', /fragil/i.test(txt))
// scroll vers le bas pour montrer l'explication complète
await p.locator('[data-faisa-explain]').scrollIntoViewIfNeeded()
await p.waitForTimeout(300)
await fiche.screenshot({ path: `${OUT}/c-explication-ia.png` })

await b.close()
console.log('captures C OK')
