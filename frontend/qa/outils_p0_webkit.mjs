// OUTILS-P0-1 — captures WebKit des deux corrections.
//  #1 Prospection solaire : les deux modes s'ouvrent et se remplissent SANS « Maximum update depth
//     exceeded » (le retour stabilisé + l'abonnement ciblé du panneau cassent la boucle).
//  #2 Pièges et risques : quatre états — contraintes (cartes) · « Aucune intersection détectée » ·
//     « Couverture inconnue » (apparaît quand il y en a) ; plus de « Vérifié, rien à signaler ».
// Pilotage par window.__labuse (setModule) + saisie d'IDU dans la barre (chemin onPick du produit).
// On RECHARGE la page entre chaque outil : état propre, pas de report d'un mode sur l'autre.
// webkit / pw-core de /tmp/pw-wk.
import { webkit } from '/tmp/pw-wk/node_modules/playwright-core/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = process.env.BASE || 'http://127.0.0.1:10110/socle/'
const OUT = 'captures/outils-p0'
mkdirSync(OUT, { recursive: true })
const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const b = await webkit.launch()
const page = await b.newPage({ viewport: { width: 1360, height: 900 }, deviceScaleFactor: 2, reducedMotion: 'reduce' })
const CHAMP = '[placeholder="Adresse, IDU ou référence (BW0917)"]'   // la barre parcelle de l'outil (≠ omnibox)
const log = {}

async function fraisSur(key) {
  await page.goto(BASE, { waitUntil: 'domcontentloaded' })
  await page.waitForFunction(() => !!window.__labuse, { timeout: 30000 })   // bundle prêt (MapLibre garde le réseau occupé → pas de networkidle)
  await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|^ok$/i.test((x.textContent || '').trim())); if (b) b.click() })
  await page.evaluate((k) => window.__labuse.setModule(k), key)
  await wait(500)
}
async function shotPanel(name) { const el = await page.$('aside'); await el.screenshot({ path: `${OUT}/${name}.png` }) }
async function saisirIdu(idu) {
  await page.waitForSelector(CHAMP, { timeout: 15000 })
  await page.fill(CHAMP, idu)
  await page.press(CHAMP, 'Enter')
}

// ── #1a — SOLAIRE / Piscines (ouvrir le mode, « Toute l'île », résultat rempli) ──
await fraisSur('prospection-solaire')
await page.waitForSelector('[data-solaire-mode="piscines"]', { timeout: 15000 })
await page.click('[data-solaire-mode="piscines"]')
await page.waitForSelector('[data-piscines-perim="ile"]', { timeout: 15000 })
await page.click('[data-piscines-perim="ile"]')
await page.waitForSelector('[data-piscines-total]', { timeout: 15000 })
await page.waitForSelector('[data-piscines-row]', { timeout: 15000 })
await wait(700)
await shotPanel('01-solaire-piscines')
log.piscines_total = await page.$eval('[data-piscines-total]', (e) => e.textContent)

// ── #1b — SOLAIRE / Ensoleillement (fiche soleil remplie : profil mensuel + ortho) ──
// On ouvre via le PRÉ-REMPLISSAGE (comme la tuile « Solaire » d'une fiche) : pas de fiche parcelle
// par-dessus. Le serveur de dev (uvicorn mono-worker) sert la fiche soleil lentement → timeout large.
await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForFunction(() => !!window.__labuse && !!window.__labuse.setSolairePrefill, { timeout: 30000 })
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|^ok$/i.test((x.textContent || '').trim())); if (b) b.click() })
await page.evaluate(() => { window.__labuse.setSolairePrefill('97422000BR0364'); window.__labuse.setModule('prospection-solaire') })
await page.waitForSelector('[data-solaire-fiche]', { timeout: 35000 })
await page.waitForSelector('[data-solaire-bar]', { timeout: 15000 })
await wait(1500)   // chargement de la vignette ortho IGN
await shotPanel('02-solaire-ensoleillement')
log.solaire_bars = (await page.$$('[data-solaire-bar]')).length

// ── #2 — PIÈGES ET RISQUES (quatre états : cartes + « Aucune intersection » + « Couverture inconnue ») ──
await fraisSur('risques')
await saisirIdu('97403000AN0006')
await page.waitForSelector('[data-o5-verifie]', { timeout: 35000 })
await page.waitForSelector('[data-o5-couverture-inconnue]', { timeout: 35000 })
await wait(900)
await shotPanel('03-pieges-apres')
// un 2ᵉ cliché DÉROULÉ sur les sections d'états (« Aucune intersection détectée » + « Couverture inconnue »)
await page.evaluate(() => {
  const el = document.querySelector('[data-o5-couverture-inconnue]')
  if (el) el.scrollIntoView({ block: 'center' })
})
await wait(500)
await shotPanel('04-pieges-etats')
log.pieges = {
  titre_clair: await page.$eval('[data-o5-verifie]', (e) => (e.textContent || '').includes('Aucune intersection détectée')),
  a_couverture_inconnue: !!(await page.$('[data-o5-couverture-inconnue]')),
  plus_ancien_libelle: !(await page.evaluate(() => document.body.textContent.includes('Vérifié, rien à signaler'))),
  familles_inconnues: await page.$eval('[data-o5-couverture-inconnue]', (e) => (e.textContent || '').replace(/\s+/g, ' ').trim()),
}

console.log(JSON.stringify(log, null, 2))
await b.close()
