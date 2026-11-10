// ECRANS-NOV-2 (recette 2) — parcours WebKit de l'écran « Analyse LABUSE par scénario » À DEUX ÉTAPES.
// Vérifie : étape Choisir (bandes + « Autres parcelles » repliable, 0 masqués, pas de phrase), la
// carte peint EXACTEMENT la liste choisie (scenarioPaint), cartes de résultat (chiffre en gros +
// capacité−existant, pas de « Voir le détail »), toute la carte ouvre la FICHE parcelle, « Modifier la
// recherche » rouvre Choisir, puce « Vente : … ». Focus au clic (aucun contour). webkit-2104 / pw 1.49.1.
import { webkit } from '/tmp/pw-wk/node_modules/playwright-core/index.mjs'

const BASE = process.env.BASE || 'http://127.0.0.1:9990/socle/'
const OUT = 'captures/ecrans-nov-2'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const b = await webkit.launch()
const page = await b.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` })
const panel = '[data-ecran="analyse-scenario"]'

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|ok/i.test(x.textContent || '')); if (b) b.click() })
await page.evaluate(() => {
  const L = window.__labuse
  L.setFilters({ ...L.getFilters(), communes: ['Saint-Denis'], zonage: ['U'], analyseLabuse: false })
  L.setVerdict(false)
})
for (let i = 0; i < 3; i++) { if (await page.locator('[data-analyser-btn]').count()) break; await page.locator('[data-filtres-toggle]').first().click(); await wait(300) }

// ── 1. Analyser → étape Choisir (bandes + Autres, pas de phrase « Classées par… ») ──
await page.locator('[data-analyser-btn]').first().click()
await page.waitForSelector(`${panel} [data-voir-parcelles]`, { timeout: 15000 })
await page.waitForFunction(() => {
  const m = (document.querySelector('[data-voir-parcelles]')?.innerText || '').match(/Voir les ([\d\s]+) parcelles/)
  return m && parseInt(m[1].replace(/\s/g, ''), 10) > 0
}, { timeout: 15000 })
await wait(500)
await shot('webkit-01-choisir')
const choisir = await page.evaluate(() => {
  const t = document.querySelector('[data-etape-choisir]')?.innerText || ''
  return { phraseRetiree: !/Classées par/.test(t), aAutres: /Autres parcelles/.test(t),
    aBandes: /Excellente|Bonne/.test(t) }
})

// ── 2. déplier « Autres parcelles » ──
await page.locator(`${panel} [data-autres]`).click()
await wait(400)
await shot('webkit-02-autres')

// ── 3. Voir les N → la liste + la carte peint la liste choisie ──
await page.locator(`${panel} [data-voir-parcelles]`).click()
await page.waitForSelector(`${panel} [data-carte-resultat]`, { timeout: 15000 })
await wait(700)
await shot('webkit-03-liste')
// la carte peint EXACTEMENT la liste choisie (scenarioPaint = idus des cohortes cochées)
const paint = await page.evaluate(() => window.__labuse.getScenarioPaint())
const etat = await page.evaluate(() => {
  const txt = document.querySelector('[data-scn-scroll]')?.innerText || ''
  return { vente: /Vente :/.test(txt), pasVoirDetail: !/Voir le détail/.test(txt) }
})

// ── 5. clic sur une carte → ouvre la FICHE parcelle ──
const idu = await page.locator(`${panel} [data-carte-resultat]`).first().getAttribute('data-carte-resultat')
await page.locator(`${panel} [data-carte-resultat]`).first().click()
await page.waitForSelector('.fiche-v6', { timeout: 8000 }).catch(() => {})
await wait(700)
const fiche = await page.evaluate(() => ({ selectedIdu: window.__labuse.getSelectedIdu(),
  ficheDom: !!document.querySelector('.fiche-v6') }))
await shot('webkit-04-fiche')
await page.evaluate(() => { const x = document.querySelector('.fiche-v6 button[aria-label*="ermer"]'); if (x) x.click() })
await wait(400)

// ── 6. recette 3 : UN SEUL bouton « ← Retour ». Depuis la LISTE → étape « Choisir » (choix conservés).
const pasDeModifier = (await page.locator(`${panel} [data-modifier]`).count()) === 0
await page.locator(`${panel} [data-retour]`).click()
await page.waitForSelector(`${panel} [data-etape-choisir]`, { timeout: 8000 })
await wait(400)
const choixConserves = await page.evaluate(() => {
  const btns = [...document.querySelectorAll('[data-etape-choisir] [role="checkbox"]')]
  const coche = (lab) => { const b = btns.find((x) => x.textContent.includes(lab)); return b && b.getAttribute('data-check') === 'on' }
  return { excellente: coche('Excellente'), bonne: coche('Bonne') }
})
await shot('webkit-05-retour-choisir')
// focus au clic (cocher ne pose aucun contour)
await page.locator(`${panel} [role="checkbox"]`).first().click()
await wait(200)
const focusAuClic = await page.evaluate(() => {
  const el = document.activeElement, s = el ? getComputedStyle(el) : null
  return { input: document.documentElement.getAttribute('data-input'), tag: el && el.tagName,
    aContour: !!s && s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 }
})
// ── depuis « Choisir », « ← Retour » ramène aux filtres (panneau d'analyse disparu) ──
await page.locator(`${panel} [data-retour]`).click()
await wait(500)
const retourFiltres = await page.evaluate(() => ({ panneauAnalyse: !!document.querySelector('[data-ecran="analyse-scenario"]'),
  analyseLabuse: window.__labuse.getFilters().analyseLabuse }))

console.log(JSON.stringify({
  choisir,
  carte_peint_liste: { n_idus: Array.isArray(paint?.idus) ? paint.idus.length : null, tronque: paint?.tronque },
  carteOuvreFiche: { clicIdu: idu, selectedIdu: fiche.selectedIdu, ficheDom: fiche.ficheDom },
  vente: etat.vente, pasVoirDetail: etat.pasVoirDetail,
  nav: { pasDeModifier, retourListe_vers_choisir_choixConserves: choixConserves, retourChoisir_vers_filtres: retourFiltres },
  focusAuClic,
}, null, 2))
await b.close()
