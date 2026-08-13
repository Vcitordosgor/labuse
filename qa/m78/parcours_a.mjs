// M78-quater #6 — capture du PARCOURS A complet (recherche) : brief → récap → Corriger → récap →
// Oui → affinage (avec le champ libre) → Lancer. C'est ce que le mandant valide.
// Usage : BASE=http://127.0.0.1:8010/socle/ node qa/m78/parcours_a.mjs
import { chromium } from '../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync } from 'node:fs'

const BASE = (process.env.BASE || 'http://127.0.0.1:8010/socle/').replace(/\/?$/, '/')
const STAMP = new Date().toISOString().slice(0, 16).replace(/[:T]/g, '-')
const OUT = new URL('./captures/parcours_a-' + STAMP, import.meta.url).pathname
mkdirSync(OUT, { recursive: true })

// Playwright de ce repo attend un chromium plus récent que le cache → on lance le Chrome système.
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 980 } })
page.setDefaultTimeout(40000)
const log = []
const shot = async (name, note) => {
  await page.waitForTimeout(500)
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false })
  log.push(`📸 ${name} — ${note}`); console.log(`  📸 ${name} — ${note}`)
}

try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.locator('button[title="IA"]').click()
  await page.locator('[data-accueil]').waitFor()
  await shot('00-accueil', 'accueil : 3 cartes (Chercher/Demander/Vérifier), 6 exemples, pas de veilles')

  // ÉTAPE 1 — le client écrit
  await page.locator('[data-brief]').fill('je cherche un terrain de 1000m2 à saint paul')
  await shot('01-brief-saisi', 'brief saisi dans la barre')
  await page.locator('[data-accueil-envoyer]').click()

  // ÉTAPE 2 — le Copilote récapitule (plus de question de programme)
  await page.locator('[data-recap]').waitFor()
  await shot('02-recap', 'RÉCAP : « J’ai compris… C’est bien ça ? » + Oui / Corriger (aucune question programme)')

  // ÉTAPE 2a — Corriger → chips éditables
  await page.locator('[data-recap-corriger]').click()
  await page.locator('[data-recap-retour]').waitFor()
  await shot('03-corriger', 'CORRIGER : chips éditables + réécriture')

  // retour au récap
  await page.locator('[data-recap-retour]').click()
  await page.locator('[data-recap]').waitFor()
  await shot('04-retour-recap', 'retour au récap')

  // ÉTAPE 2b — Oui → affinage optionnel AVEC champ libre
  await page.locator('[data-recap-oui]').click()
  await page.locator('[data-recap-affiner]').waitFor()
  await page.locator('[data-recap-libre]').waitFor()
  await shot('05-affinage', 'AFFINAGE : suggestions + CHAMP LIBRE « …ou écrivez » + Lancer pleine largeur')

  // ajoute une suggestion + écrit dans le champ libre
  const sugg = page.locator('[data-recap-suggestion]').first()
  if (await sugg.count()) await sugg.click()
  await page.locator('[data-recap-libre]').fill('proche des écoles')
  await page.locator('[data-recap-libre]').press('Enter')
  await page.waitForTimeout(400)
  await shot('06-affinage-enrichi', 'chip ajoutée depuis le champ libre (« proche des écoles ») + une suggestion')

  // ÉTAPE 3 — Lancer
  await page.locator('[data-recap-lancer]').click()
  await page.waitForTimeout(2500)
  await shot('07-lancer', 'instruction lancée (le run tourne / entonnoir)')

  console.log('\nPARCOURS A capturé →', OUT)
} catch (e) {
  console.error('ÉCHEC capture :', String(e).slice(0, 300))
  await page.screenshot({ path: `${OUT}/ZZ-echec.png`, fullPage: false }).catch(() => {})
  process.exitCode = 1
} finally {
  await browser.close()
}
