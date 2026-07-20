// FIX post-validation — captures (avant/après). LABEL=before|after en env.
// after-only : A (cadrage aboutit) + D (tooltips ×N / complétude, texte DOM + badge).
// avant/après : B (barre parcours), C (carte restitution), E (repli IA).
import { chromium } from 'playwright'

const BASE = 'http://127.0.0.1:8010/socle/'
const OUT = '../../reports/post-validation/captures'
const LABEL = process.env.LABEL || 'after'
const NOM = 'Résidence étudiante Saint-Paul'
const wait = (p, ms) => p.waitForTimeout(ms)

const b = await chromium.launch()
const page = await b.newPage({ viewport: { width: 1280, height: 860 } })
const errs = []
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()) })

async function fresh() {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForFunction(() => window.__labuse && window.__labuse.setView, { timeout: 15000 })
}
const ONLY = process.env.ONLY || ''   // ex. ONLY=B pour ne rejouer qu'une section
async function step(name, fn) {
  if (ONLY && !name.startsWith(ONLY)) return
  try { await fn(); console.log(`OK  ${name}`) }
  catch (e) { console.log(`ERR ${name}: ${String(e).split('\n')[0]}`) }
}

// ── A — le cadrage aboutit (after-only) : le cas « R+3 » qui faisait tomber l'entretien ──
if (LABEL === 'after') {
  await step('A cadrage', async () => {
    await fresh()
    await page.evaluate(() => window.__labuse.setView('ia'))
    await page.waitForSelector('[data-porte-recherche] input', { timeout: 10000 })
    await page.fill('[data-porte-recherche] input', "40 logements en R+3 dans l'Ouest, éviter les zones inondables")
    await page.click('[data-decrire-projet]')
    await page.waitForSelector('[data-entretien-fiche]', { timeout: 20000 })
    // attendre que la fiche se remplisse (R+3 dans l'Ampleur) et que « Lancer » apparaisse
    await page.waitForSelector('[data-entretien-lancer]', { timeout: 25000 })
    await wait(page, 600)
    const fiche = (await page.locator('[data-entretien-fiche]').innerText()).replace(/\s+/g, ' ')
    console.log('   fiche:', fiche)
    await page.screenshot({ path: `${OUT}/A-cadrage-aboutit.png` })
  })
}

// ── B — barre du parcours de tri (avant/après) ──
await step('B barre parcours', async () => {
  await fresh()
  await page.evaluate(() => window.__labuse.setView('projets'))
  await page.waitForSelector('[data-projets-liste]', { timeout: 10000 })
  const card = page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
  await card.locator('[data-projet-trier]').click()
  await page.waitForSelector('[data-parcours-plus]', { timeout: 15000 })
  await wait(page, 2500)
  // la barre du parcours = l'ancêtre direct des boutons (sous l'en-tête app, pas l'en-tête)
  const bar = page.locator('[data-parcours-quitter]').locator('xpath=ancestor::div[1]')
  await bar.screenshot({ path: `${OUT}/B-parcours-bar-${LABEL}.png` })
})

// ── C — carte de restitution (avant/après) ──
await step('C restitution', async () => {
  await fresh()
  await page.evaluate(() => window.__labuse.setView('projets'))
  await page.waitForSelector('[data-projets-liste]', { timeout: 10000 })
  const card = page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
  await card.locator('[data-projet-ouvrir]').click()
  await page.waitForSelector('[data-ia-restitution]', { timeout: 20000 })
  await page.waitForSelector('[data-ia-top]', { timeout: 15000 })
  await wait(page, 1200)
  await page.locator('[data-ia-restitution]').screenshot({ path: `${OUT}/C-restitution-${LABEL}.png` })
})

// ── D — tooltips ×N et complétude (after-only) : texte DOM (les title natifs ne se
//      capturent pas en image) + capture de la carte de résultat qui porte les badges ──
if (LABEL === 'after') {
  await step('D tooltips', async () => {
    await fresh()
    await page.evaluate(() => window.__labuse.setView('projets'))
    await page.waitForSelector('[data-projets-liste]', { timeout: 10000 })
    const card = page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
    await card.locator('[data-projet-ouvrir]').click()
    await page.waitForSelector('[data-ia-restitution]', { timeout: 20000 })
    await page.click('[data-ia-voir-tout]')
    await page.waitForSelector('[data-results-scroll]', { timeout: 15000 })
    await wait(page, 1500)
    const multTip = await page.locator('[title^="Multiplicateur du score P"]').first().getAttribute('title').catch(() => null)
    const compTip = await page.locator('[title^="Complétude des données"]').first().getAttribute('title').catch(() => null)
    console.log('   ×N title      :', multTip)
    console.log('   complétude    :', compTip)
    // capture des 3 premières cartes de résultat (badges ×N + anneau de complétude à droite)
    const cards = page.locator('[data-results-scroll] [data-tier-chip]').first().locator('xpath=ancestor::button[1]')
    await cards.scrollIntoViewIfNeeded()
    const box = await cards.boundingBox()
    if (box) await page.screenshot({ path: `${OUT}/D-badges.png`,
      clip: { x: box.x, y: box.y, width: Math.min(460, box.width), height: Math.min(240, box.height * 3) } })
  })
}

// ── E — repli IA « Voir l'entièreté de la fiche » (avant/après) ──
await step('E repli IA', async () => {
  await fresh()
  // ouvrir une fiche via la restitution d'un projet (IDU réel garanti)
  await page.evaluate(() => window.__labuse.setView('projets'))
  await page.waitForSelector('[data-projets-liste]', { timeout: 10000 })
  const card = page.locator(`[data-projet-card]:has([data-projet-nom]:has-text("${NOM}"))`)
  await card.locator('[data-projet-ouvrir]').click()
  await page.waitForSelector('[data-ia-top]', { timeout: 20000 })
  await page.locator('[data-ia-top]').first().click()
  await page.waitForSelector('[data-askbar]', { timeout: 15000 })
  await page.click('[data-askbar-open]')
  await page.waitForSelector('[data-askbar] input', { timeout: 8000 })
  await page.fill('[data-askbar] input', 'Combien je peux construire ?')
  // lancer + attendre la réponse (appel IA réel)
  await page.locator('[data-askbar] button:has-text("Demander")').click()
  await page.waitForFunction(() => {
    const bar = document.querySelector('[data-askbar]')
    return bar && /Voir l'entièreté|réponse en cache|Absent|Sourcé|non disponible/i.test(bar.textContent || '')
      && !/L'IA lit la fiche/.test(bar.textContent || '')
  }, { timeout: 45000 })
  await wait(page, 800)
  const panelClip = { x: 895, y: 44, width: 385, height: 816 }   // le panneau fiche (droite)
  await page.screenshot({ path: `${OUT}/E-reponse-${LABEL}.png`, clip: panelClip })
  // (après) replier via le lien, puis capturer la fiche entière + l'état « gardé »
  if (LABEL === 'after') {
    await page.click('[data-askbar-voir-fiche]')
    await wait(page, 700)
    await page.screenshot({ path: `${OUT}/E-replie-${LABEL}.png`, clip: panelClip })
    const hint = (await page.locator('[data-askbar-open]').innerText()).replace(/\s+/g, ' ')
    console.log('   bouton replié :', hint)
  }
})

console.log(`\nconsole errors: ${errs.length}`)
if (errs.length) console.log(errs.slice(0, 5).join('\n'))
await b.close()
console.log(`captures ${LABEL} terminées`)
