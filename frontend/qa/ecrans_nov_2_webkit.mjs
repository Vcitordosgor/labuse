// ECRANS-NOV-2 — parcours WebKit (Safari) de l'écran « Analyse LABUSE par scénario » À DEUX ÉTAPES,
// DANS le panneau de gauche (à côté de la carte). Parcours : filtres Saint-Denis + un zonage →
// « Analyser » → étape « Choisir » (cocher/décocher, changer d'objectif ET de scénario → les effectifs
// changent, bug 4) → « Voir les N parcelles » → étape « La liste » → clic sur une carte → détail →
// « Modifier ▾ » → Retour. On vérifie la règle de focus (aucun contour au clic). webkit-2104 / pw 1.49.1.
import { webkit } from '/tmp/pw-wk/node_modules/playwright-core/index.mjs'

const BASE = process.env.BASE || 'http://127.0.0.1:9990/socle/'
const OUT = 'captures/ecrans-nov-2'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await webkit.launch()
const page = await b.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` })
const panel = '[data-ecran="analyse-scenario"]'
const effTexte = () => page.evaluate(() => document.querySelector('[data-etape-choisir]')?.innerText || '')

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|ok/i.test(x.textContent || '')); if (b) b.click() })

// ── 1. Filtres : Saint-Denis + un zonage (U) ──
await page.evaluate(() => {
  const L = window.__labuse
  L.setFilters({ ...L.getFilters(), communes: ['Saint-Denis'], zonage: ['U'], analyseLabuse: false })
  L.setVerdict(false)
})
for (let i = 0; i < 3; i++) {
  if (await page.locator('[data-analyser-btn]').count()) break
  await page.locator('[data-filtres-toggle]').first().click(); await wait(300)
}
await wait(300)

// valeur d'une ligne cochable (ex. « Aucun ajout » → 12349) dans l'étape Choisir
const valeur = (label) => page.evaluate((lab) => {
  const t = document.querySelector('[data-etape-choisir]')?.innerText || ''
  const m = t.match(new RegExp(lab + '\\s*([\\d\\s]+)'))
  return m ? parseInt(m[1].replace(/\s/g, ''), 10) : null
}, label)

// ── 2. Analyser → étape « Choisir » (Potentiel · Bâti conservé, Excellente + Bonne cochées) ──
await page.locator('[data-analyser-btn]').first().click()
await page.waitForSelector(`${panel} [data-voir-parcelles]`, { timeout: 15000 })
// attendre que les EFFECTIFS soient chargés (N > 0), pas le « Voir les 0 parcelles » de chargement
await page.waitForFunction(() => {
  const m = (document.querySelector('[data-voir-parcelles]')?.innerText || '').match(/Voir les ([\d\s]+) parcelles/)
  return m && parseInt(m[1].replace(/\s/g, ''), 10) > 0
}, { timeout: 15000 })
await wait(600)
await shot('webkit-01-choisir-keep')
const keepAucun = await valeur('Aucun ajout')      // conservation : > 0
const keepCalcul = await valeur('Calcul à compléter')   // conservation : 0

// ── 3. BUG (4) : passer en Reconstruction → les effectifs DOIVENT changer ──
await page.locator(`${panel} button:has-text("Reconstruction")`).click()
// reconstruction : « Calcul à compléter » devient > 0 (l'inverse du bâti conservé)
await page.waitForFunction(() => {
  const t = document.querySelector('[data-etape-choisir]')?.innerText || ''
  const m = t.match(/Calcul à compléter\s*([\d\s]+)/)
  return m && parseInt(m[1].replace(/\s/g, ''), 10) > 0
}, { timeout: 15000 })
await wait(600)
await shot('webkit-02-choisir-rebuild')
const rebuildAucun = await valeur('Aucun ajout')       // reconstruction : 0
const rebuildCalcul = await valeur('Calcul à compléter')  // reconstruction : > 0

// ── 4. Prospection (libellés courts) ──
await page.locator(`${panel} button:has-text("Prospection")`).click()
await page.waitForFunction(() => /Fort|Moyen|Faible/.test(document.querySelector('[data-etape-choisir]')?.innerText || ''), { timeout: 10000 })
await wait(500)
await shot('webkit-03-choisir-prospection')

// ── vérif FOCUS au clic : cocher une ligne ne pose AUCUN contour ──
await page.locator(`${panel} [role="checkbox"]`).first().click()
await wait(200)
const focusAuClic = await page.evaluate(() => {
  const el = document.activeElement, s = el ? getComputedStyle(el) : null
  return { input: document.documentElement.getAttribute('data-input'), tag: el && el.tagName,
    aContour: !!s && s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0 }
})

// ── 5. Retour en Potentiel · Reconstruction, cocher aussi « À étudier », puis « Voir les N parcelles » ──
await page.locator(`${panel} button:has-text("Potentiel")`).click()
await page.locator(`${panel} button:has-text("Reconstruction")`).click()
await page.waitForSelector(`${panel} [role="checkbox"]`)
await page.locator(`${panel} [role="checkbox"]:has-text("À étudier")`).click()
await wait(300)
await page.locator(`${panel} [data-voir-parcelles]`).click()
await page.waitForSelector(`${panel} [data-carte-resultat]`, { timeout: 15000 })
await wait(600)
await shot('webkit-04-liste')

// ── 6. Clic sur une carte de résultat → détail ──
await page.locator(`${panel} [data-carte-resultat]`).first().click()
await page.waitForFunction(() => /Ce qui explique|Gain net/.test(document.body.innerText), { timeout: 10000 })
await wait(500)
await shot('webkit-05-detail')
await page.keyboard.press('Escape'); await wait(300)

// ── 7. « Modifier ▾ » rouvre l'étape « Choisir » ──
await page.locator(`${panel} [data-modifier]`).click()
await page.waitForSelector(`${panel} [data-etape-choisir]`)
await wait(300)
await shot('webkit-06-modifier')

// ── 8. Retour → revient aux filtres ──
await page.locator(`${panel} [data-retour]`).click()
await wait(400)
const apresRetour = await page.evaluate(() => ({
  panneauAnalyse: !!document.querySelector('[data-ecran="analyse-scenario"]'),
  analyseLabuse: window.__labuse.getFilters().analyseLabuse,
}))

console.log(JSON.stringify({
  focusAuClic, apresRetour,
  bug4: {
    keep: { aucun_ajout: keepAucun, calcul: keepCalcul },
    rebuild: { aucun_ajout: rebuildAucun, calcul: rebuildCalcul },
    // le scénario DOIT changer les effectifs : conservation (Aucun ajout>0, Calcul=0) vs
    // reconstruction (Aucun ajout=0, Calcul>0).
    corrigé: keepAucun > 0 && keepCalcul === 0 && rebuildAucun === 0 && rebuildCalcul > 0,
  },
}, null, 2))
await b.close()
