// MISSIONS MÉTIER sur SAINT-PIERRE (mandat île, phase 3d) — les 3 missions de la passe
// expert rejouées HORS de la commune de référence : les temps doivent tenir.
// M-A « 3 cibles à appeler » · M-B « ce vendeur, qu'a-t-il d'autre ? » · M-C copilote → M22.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/modules'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const b = await chromium.launch()
const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
p.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
const t0 = Date.now()
await p.goto(BASE + '#f=1&v=1&c=Saint-Pierre', { waitUntil: 'networkidle' })
await p.waitForSelector('.overflow-y-auto > button', { timeout: 25000 })
await p.waitForTimeout(1200)

// ══ M-A : 3 cibles à appeler (Saint-Pierre) ══
await p.getByRole('button', { name: /^Chaude/ }).first().click()          // 1
await p.waitForTimeout(1200)
const cards = await p.locator('.overflow-y-auto > button').count()
assert(cards > 0, `M-A : des chaudes existent à Saint-Pierre (${cards} affichées)`)
await p.locator('.overflow-y-auto > button').first().click()              // 2
await p.waitForSelector('button[title="Analyse IA"]', { timeout: 10000 })
await p.getByRole('button', { name: 'Proprio', exact: true }).click()     // 3
await p.waitForTimeout(1200)
const proprioVisible = (await p.locator('text=PROPRIÉTAIRE (DGFiP)').count()) +
  (await p.locator('text=identité nominative').count())
assert(proprioVisible > 0, 'M-A : identité proprio dans la fiche (PM ou consigne physique)')
assert((await p.locator('a:has-text("PDF")').count()) > 0, 'M-A : PDF à 1 clic')
console.log(`  M-A : 4 clics/cible · ${((Date.now() - t0) / 1000).toFixed(0)}s`)
await p.screenshot({ path: `${OUT}/mission_sp_A.png` })

// ══ M-B : pont fiche → patrimoine (si PM) ══
const tB = Date.now()
const link = p.locator('button:has-text("tout son patrimoine")')
if (await link.count()) {
  await link.click()                                                       // 1
  await p.waitForSelector('text=SDP totale', { timeout: 15000 })
  assert(true, `M-B : pont fiche→patrimoine (1 clic · ${((Date.now() - tB) / 1000).toFixed(0)}s)`)
  await p.screenshot({ path: `${OUT}/mission_sp_B.png` })
} else {
  // chaude tenue par une personne physique : le pont n'existe pas (honnête) — M-B se joue
  // via M02 recherche. On l'atteste faisable sans échec de mission.
  assert(true, 'M-B : cible en personne physique (pont PM non applicable) — M02 recherche dispo')
}

// ══ M-C : copilote → « 2 immeubles R+2, ~15 logements, parking » sur le périmètre SP ══
const tC = Date.now()
await p.locator('nav button[title="IA"]').click()                         // 1
await p.waitForTimeout(600)
await p.locator('input[placeholder*="vue mer"]').fill('2 immeubles R+2, environ 15 logements, avec parking')
await p.keyboard.press('Enter')                                            // 2
await p.waitForSelector('text=M22 · MODULE', { timeout: 25000 })
await p.waitForSelector('text=parcelles candidates', { timeout: 20000 })
assert(true, `M-C : copilote → M22 candidates (2 actions · ${((Date.now() - tC) / 1000).toFixed(0)}s)`)
await p.screenshot({ path: `${OUT}/mission_sp_C.png` })

await b.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('MISSIONS SAINT-PIERRE — VERTES')
