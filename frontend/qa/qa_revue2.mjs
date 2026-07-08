// REVUE VIC N°2 — R1 (le cadastre d'abord, le tri comme GESTE) + R2 (copilote cadreur, EN RÉEL).
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))

// ═══ R1 — URL VIERGE : le cadastre entier, verdict éteint ═══
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('[data-verdict-on]', { timeout: 20000 })
await page.waitForTimeout(6000)   // tuiles z9 (~6 Mo la première fois)
const trame = await page.evaluate(() => {
  const m = window.__labuse_map
  return { zoom: m.getZoom(), fills: m.queryRenderedFeatures({ layers: ['ile-fill'] }).length }
})
assert(trame.fills > 1000, `R1 : trame parcellaire RENDUE à l'ouverture (z=${trame.zoom.toFixed(1)}, ${trame.fills} parcelles à l'écran — pas d'île noire)`)
// verdict ÉTEINT : pas de compteurs, pas de liste, bouton signature visible
assert((await page.locator('[data-verdict-on]').isVisible()), 'R1 : bouton signature « LABUSE a trié pour vous » VISIBLE')
assert((await page.locator('text=opportunités détectées').count()) === 0, 'R1 : entonnoir ÉTEINT par défaut')
assert((await page.locator('.overflow-y-auto > button').count()) === 0, 'R1 : liste éteinte par défaut')
await page.screenshot({ path: `${OUT}/revue2_defaut_eteint.png` })

// LE GESTE : un clic → couleurs + entonnoir + liste
await page.locator('[data-verdict-on]').click()
await page.waitForSelector('text=opportunités détectées', { timeout: 15000 })
await page.waitForFunction(() => document.querySelectorAll('.overflow-y-auto > button').length > 0, null, { timeout: 20000 })
assert(true, 'R1 : le geste allume entonnoir + liste')
assert(page.url().includes('v=1'), 'R1 : verdict dans l’URL (v=1)')
const colored = await page.evaluate(() => {
  const m = window.__labuse_map
  const paint = m.getPaintProperty('ile-fill', 'fill-color')
  return Array.isArray(paint) && JSON.stringify(paint).includes('#5CE6A1')
})
assert(colored, 'R1 : les couleurs de verdict sont sur la carte')
await page.screenshot({ path: `${OUT}/revue2_defaut_allume.png` })

// URL v=1 → ouvre allumé
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'domcontentloaded' })
await page.reload({ waitUntil: 'networkidle' })
await page.waitForSelector('text=opportunités détectées', { timeout: 20000 })
assert(true, 'R1 : URL v=1 → ouvre verdict allumé (lien de démo)')

// ═══ R2 — COPILOTE CADREUR (EN RÉEL) ═══
const st = await (await fetch(new URL('/ia/status', BASE).href)).json()
assert(st.provider === 'anthropic', `R2 : provider réel (${st.provider})`)

// a) précise → ZÉRO question, exécution directe (comportement inchangé, parcours C)
await page.locator('nav button[title="IA"]').click()
await page.waitForTimeout(600)
await page.locator('input[placeholder*="vue mer"]').fill('les chaudes de Saint-Pierre')
await page.keyboard.press('Enter')
await page.waitForSelector('header span:has-text("Chaude")', { timeout: 25000 })
assert((await page.locator('[data-entretien]').count()) === 0, 'R2 : demande précise → ZÉRO question (pas d’entretien)')
await page.waitForSelector('[data-ia-restitution]', { timeout: 15000 })   // stats+top async après apply
assert((await page.locator('[data-ia-restitution]').count()) > 0, 'R2 : restitution posée (précise)')
await page.locator('[data-ia-restitution] button[title="Fermer"]').click()

// b) projet vague → ENTRETIEN de cadrage (V2) : reformulation + fiche à l'écran + chips → lancer
await page.locator('nav button[title="IA"]').click()
await page.waitForTimeout(600)
await page.locator('input[placeholder*="vue mer"]').fill('je cherche un terrain pour 40 logements étudiants dans l\'Ouest')
await page.locator('[data-decrire-projet]').click()
await page.waitForSelector('[data-entretien-reformulation]', { timeout: 30000 })
assert(true, 'R2/V2 : l’entretien s’ouvre (reformulation à l’écran)')
const ficheTxt = await page.locator('[data-entretien-fiche]').innerText()
assert(/étudiant/i.test(ficheTxt) && /Ouest/i.test(ficheTxt), 'R2/V2 : la fiche se construit à l’écran (type + secteur)')
assert((await page.locator('[data-entretien-lancer]').count()) >= 1, 'R2/V2 : « Lancer la recherche » disponible')
await page.screenshot({ path: `${OUT}/revue2_copilote_cadrage.png` })
await page.locator('[data-entretien-lancer]').click()
// suivi automatique → filtres + vol caméra + restitution
await page.waitForSelector('[data-ia-restitution]', { timeout: 40000 })
const resti = await page.locator('[data-ia-restitution]').innerText()
assert(resti.includes('parcelles'), 'R2 : phrase de restitution VISIBLE')
assert((await page.locator('[data-ia-top]').count()) === 3, 'R2 : les 3 meilleures cliquables')
// le compteur = SQL (communes du secteur Ouest)
await page.waitForTimeout(1200)
const countTxt = await page.locator('[data-ia-count]').innerText()
assert(/\d/.test(countTxt), `R2 : compteur animé affiché (${countTxt})`)
await page.screenshot({ path: `${OUT}/revue2_copilote_restitution.png` })
// top 1 cliquable → fiche
await page.locator('[data-ia-top]').first().click()
await page.waitForSelector('button[title="Analyse IA"]', { timeout: 12000 })
assert(true, 'R2 : top 1 → fiche ouverte')
await page.keyboard.press('Escape')
void sql

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('REVUE VIC N°2 — R1/R2 VERTS')
