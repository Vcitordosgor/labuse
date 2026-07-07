// AUTO-QA VAGUE 2 — Copilote IA. 10 phrases NL → JSON attendu (stub déterministe, validé par
// schéma côté API) + parcours UI réel (Copilote → chips appliqués ; fiche → synthèse + pourquoi).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/modules'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

// ── 10 phrases → attentes (stub déterministe)
const CASES = [
  ['les chaudes avec vue mer', (f) => f.statuts.includes('chaude') && f.vueMer],
  ['parcelles à surveiller de plus de 2000 m²', (f) => f.statuts.includes('a_surveiller') && f.surfaceMin === 2000],
  ['chaudes avec événement bodacc', (f) => f.statuts.includes('chaude') && f.evenement],
  ['terrains pollués à creuser', (f) => f.statuts.includes('a_creuser') && f.flags.includes('sol_pollue')],
  ['score > 80 avec vue mer', (f) => f.scoreMin === 80 && f.vueMer],
  ['SDP d’au moins 800 m²', (f) => f.sdpMin === 800],
  ['moins de 5000 m² près d’une usine', (f) => f.surfaceMax === 5000 && f.flags.includes('icpe')],
  ['parcelles avec risque inondation', (f) => f.flags.includes('risques')],
  ['monument historique à proximité', (f) => f.flags.includes('abf')],
  ['raconte-moi une blague', null], // hors périmètre → refus explicite
]

const api = async (text) => {
  const r = await fetch(new URL('/ia/search', BASE).href, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) })
  return r.json()
}

for (const [text, check] of CASES) {
  const d = await api(text)
  if (check === null) assert(!!d.out_of_scope && !d.filters, `NL refus : « ${text} »`)
  else assert(!!d.filters && check(d.filters), `NL : « ${text} »`, JSON.stringify(d.filters ?? d))
}

// ── parcours UI réel
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes')
await page.waitForTimeout(2000)

await page.locator('nav button[title="IA"]').click()
await page.waitForTimeout(600)
assert((await page.locator('text=Copilote').count()) > 0, 'vue Copilote')
assert((await page.locator('text=Mode dégradé : stub local').count()) > 0, 'état stub évident (carte mode dégradé + marche à suivre)')
await page.locator('input[placeholder*="vue mer"]').fill('les chaudes avec vue mer')
await page.screenshot({ path: `${OUT}/ia_copilote.png` })
await page.keyboard.press('Enter')
await page.waitForTimeout(1500)
// retour auto sur la carte, chips appliqués
assert((await page.locator('header span:has-text("Chaude")').count()) > 0, 'copilote → chip Chaude appliqué')
assert((await page.locator('header span:has-text("Vue mer")').count()) > 0, 'copilote → chip Vue mer appliqué')
assert(page.url().includes('vm=1'), 'copilote → URL synchronisée')
await page.screenshot({ path: `${OUT}/ia_filtres_appliques.png` })

// fiche → IA (synthèse + pourquoi)
await page.keyboard.press('/')
await page.keyboard.type('AC0253')
await page.keyboard.press('Enter')
await page.waitForTimeout(1200)
await page.locator('button[title="Analyse IA"]').click()
await page.waitForTimeout(300)
await page.getByRole('button', { name: 'Synthèse' }).last().click()
await page.waitForTimeout(1200)
assert((await page.locator('text=vérifier les sources').count()) > 0, 'fiche IA : synthèse + mention')
await page.getByRole('button', { name: 'Pourquoi ce score ?' }).click()
await page.waitForTimeout(1200)
assert((await page.locator('text=100 % déterministe').count()) > 0, 'fiche IA : pourquoi + doctrine')
await page.screenshot({ path: `${OUT}/ia_fiche.png` })

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('VAGUE 2 — AUTO-QA VERTE')
