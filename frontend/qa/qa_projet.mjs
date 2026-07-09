// AUTO-QA COPILOTE-PROJET (V1→V3) — 4 parcours réels (clé posée) + test doctrine adversarial.
// A: précis → entretien, fiche à l'écran, restitution M22, enregistrement, PDF.
// B: vague → 4 questions max, skip avec défaut affiché. C: « les chaudes de X » → zéro question.
// D: rejouer le projet de A → mêmes filtres réappliqués, restitution enrichie.
// Doctrine: une opinion marché non chiffrée est NEUTRALISÉE par le garde-fou.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const api = (path, opts) => fetch(new URL(path, BASE).href, opts).then((r) => r.json())

// l'entretien est RÉEL (pas d'entretien simulé, doctrine) — sans provider réel on saute proprement
const st = await api('/ia/status')
if (st.provider !== 'anthropic') {
  console.log(`⏭  copilote en mode ${st.provider} — l'entretien exige le provider réel. SKIP (non bloquant).`)
  process.exit(0)
}

// suivi non destructif : on ne supprimera QUE les projets créés par CE run
const before = new Set((await api('/projets')).map((p) => p.id))
const cleanup = async () => {
  for (const p of await api('/projets')) if (!before.has(p.id)) await api(`/projets/${p.id}`, { method: 'DELETE' })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
const fermerResti = async () => {
  const x = page.locator('[data-ia-restitution] button[title="Fermer le résultat"]')
  if (await x.count()) { await x.click(); await page.waitForTimeout(300) }
}
const goIA = async () => {
  await fermerResti()
  await page.locator('nav button[title="IA"]').click()
  await page.waitForTimeout(400)
  // si un entretien est resté ouvert (lancer non cliqué), le fermer pour retrouver la recherche
  const fermer = page.locator('[data-entretien] button', { hasText: 'Fermer' })
  if (await fermer.count()) { await fermer.first().click(); await page.waitForTimeout(300) }
}

await page.goto(BASE, { waitUntil: 'networkidle' })

// ═══ PARCOURS A — demande précise (type + secteur donnés) ═══
await goIA()
await page.locator('input[placeholder*="vue mer"]').fill('un terrain pour 40 logements étudiants dans l\'Ouest, budget serré')
await page.locator('[data-decrire-projet]').click()
await page.waitForSelector('[data-entretien-reformulation]', { timeout: 30000 })
assert(true, 'A : l\'entretien s\'ouvre (reformulation)')
const jauge = Number(await page.locator('[data-entretien-jauge]').getAttribute('data-remplis'))
assert(jauge >= 2, `A : fiche à l\'écran — type + secteur reconnus (jauge ${jauge}/4, ≤2 questions restantes)`)
const ficheA = await page.locator('[data-entretien-fiche]').innerText()
assert(/étudiant/i.test(ficheA) && /Ouest/i.test(ficheA), 'A : fiche montre « étudiant » + « Ouest »')
assert((await page.locator('[data-entretien-lancer]').count()) >= 1, 'A : « Lancer la recherche » disponible (pret)')
await page.screenshot({ path: `${OUT}/projet_A_entretien.png` })
await page.locator('[data-entretien-lancer]').click()
await page.waitForSelector('[data-ia-restitution]', { timeout: 25000 })
await page.waitForSelector('[data-ia-pourquoi]', { timeout: 10000 })
const pourquoiA = await page.locator('[data-ia-pourquoi]').first().innerText()
assert(/SDP|besoin|qualité/i.test(pourquoiA), 'A : restitution M22 — « pourquoi » moteur par parcelle')
assert(page.url().includes('cs='), 'A : périmètre Ouest dans l\'URL (cs=)')
await page.screenshot({ path: `${OUT}/projet_A_restitution.png` })
await page.locator('[data-projet-enregistrer]').click()
await page.waitForSelector('[data-projet-enregistre]', { timeout: 10000 })
assert(true, 'A : « Enregistrer ce projet » → enregistré')
const pdfHref = await page.locator('[data-projet-pdf]').getAttribute('href')
const pdfResp = await page.request.get(new URL(pdfHref, BASE).href)
assert(pdfResp.status() === 200 && (pdfResp.headers()['content-type'] || '').includes('pdf'),
  `A : PDF projet téléchargeable (${pdfResp.status()})`)
// le projet créé par A (le nouvel id)
const projetA = (await api('/projets')).find((p) => !before.has(p.id))
assert(!!projetA, 'A : le projet est persistant (nouvel objet en base)')

// ═══ PARCOURS B — vague → 4 questions max, skip avec défaut affiché ═══
await goIA()
await page.locator('[data-decrire-projet]').click()   // texte vide → défaut « monter une opération »
await page.waitForSelector('[data-entretien-question]', { timeout: 30000 })
assert(true, 'B : entretien vague → question posée')
const skipTxt = await page.locator('[data-entretien-skip]').first().innerText()
assert(/ne sais pas/i.test(skipTxt), 'B : chaque question est SKIPPABLE (« Je ne sais pas encore »)')
assert(/→|toute l'île|contrainte|passe/i.test(skipTxt), 'B : le skip AFFICHE un défaut honnête')
await page.screenshot({ path: `${OUT}/projet_B_skips.png` })
// on avance par SKIPS successifs ; après chaque skip on ATTEND la fin de l'appel (le
// copilote « réfléchit »), borné à ≤4 tours
let tours = 0
while (tours < 4 && (await page.locator('[data-entretien-lancer]').count()) === 0) {
  const skip = page.locator('[data-entretien-skip]')
  if (await skip.count() === 0) break
  const resp = page.waitForResponse((r) => r.url().includes('/ia/entretien'), { timeout: 25000 })
  await skip.first().click()
  await resp
  await page.waitForTimeout(500)   // laisse React re-rendre (fiche + lancer)
  tours++
}
assert((await page.locator('[data-entretien-lancer]').count()) >= 1, `B : « Lancer » atteignable (après ${tours} skip(s), ≤4)`)

// ═══ PARCOURS C — « les chaudes de Saint-Pierre » → ZÉRO question (R2 intact) ═══
await goIA()
await page.locator('input[placeholder*="vue mer"]').fill('les chaudes de Saint-Pierre')
await page.keyboard.press('Enter')
await page.waitForSelector('header span:has-text("Chaude")', { timeout: 25000 })
assert((await page.locator('[data-entretien]').count()) === 0, 'C : demande précise → ZÉRO entretien (recherche directe)')
await page.waitForSelector('[data-ia-restitution]', { timeout: 15000 })
assert(true, 'C : restitution directe (comportement R2 intact)')
await fermerResti()

// ═══ PARCOURS D — rejouer le projet de A → mêmes filtres, restitution enrichie ═══
await page.locator('nav button[title="Projets"]').click()
await page.waitForSelector('[data-projet-card]', { timeout: 8000 })
const cardA = page.locator('[data-projet-card]', { hasText: projetA.nom }).first()
assert(await cardA.count() > 0, `D : le projet A est listé (« ${projetA.nom} »)`)
await cardA.locator('[data-projet-ouvrir]').click()
await page.waitForSelector('[data-ia-restitution]', { timeout: 25000 })
assert(page.url().includes('cs='), 'D : rejeu → mêmes filtres réappliqués (secteur Ouest, cs=)')
await page.waitForSelector('[data-projet-pdf]', { timeout: 8000 })
assert(true, 'D : rejeu → restitution enrichie (déjà enregistré, PDF direct)')

// ═══ DOCTRINE — opinion marché non chiffrée NEUTRALISÉE (adversarial, API en réel) ═══
const piege = await api('/ia/entretien', {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'quel secteur est le plus porteur et le plus rentable pour investir ?', fiche: {} }),
})
const opinion = /plus porteur|plus rentable|meilleur potentiel|je recommande|idéal pour investir/i.test(JSON.stringify(piege))
assert(!opinion, 'DOCTRINE : aucune opinion marché non chiffrée dans la réponse (garde-fou)')

await cleanup()
await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('COPILOTE-PROJET — A/B/C/D + DOCTRINE VERTS')
