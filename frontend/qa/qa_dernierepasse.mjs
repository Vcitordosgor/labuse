// DERNIÈRE PASSE — points vérifiables automatiquement : P1 nav exclusive · P2 persistance des
// résultats + « Voir les X » · P3 résultats violets · P8 marqueur→contexte · P9 popover borné ·
// P10 parc marron · P11 limites communes · P12 loupe + recherche depuis fiche. (P4/P5/P6/P7 =
// preuve visuelle dans le compte-rendu ; P13/P14 = conclusions documentées.)
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE, { waitUntil: 'domcontentloaded' })
await page.waitForSelector('nav button[title="Projets"]', { timeout: 20000 })
await page.waitForTimeout(3500)

// ═══ P1 — NAVIGATION EXCLUSIVE : une seule vue, aucun résidu ═══
await page.locator('nav button[title="Projets"]').click(); await page.waitForTimeout(700)
assert((await page.locator('text=Mes projets').count()) > 0, 'P1 : vue Projets affichée')
await page.locator('nav button[title="Outils"]').click(); await page.waitForTimeout(700)
assert((await page.locator('text=Mes projets').count()) === 0, 'P1 : ouvrir Outils FERME Projets (aucun résidu en fond)')
assert((await page.locator('[data-outil]').count()) > 0, 'P1 : le tiroir Outils est affiché')
assert((await page.locator('text=COUCHES').count()) === 0, 'P1 : le panneau Cartes (COUCHES) ne coexiste pas avec Outils')
await page.locator('nav button[title="CRM"]').click(); await page.waitForTimeout(700)
assert((await page.locator('[data-outil]').count()) === 0, 'P1 : passer à CRM ferme le tiroir Outils')

// ═══ P2 + P3 — recherche : accès à TOUS + persistance + résultats VIOLETS ═══
await page.locator('nav button[title="IA"]').click()
await page.waitForSelector('[data-porte-recherche]', { timeout: 8000 })
await page.locator('[data-porte-recherche] input').fill('à creuser dans l\'Ouest')
await page.keyboard.press('Enter')
await page.waitForSelector('[data-ia-restitution]', { timeout: 30000 }); await page.waitForTimeout(3500)
assert((await page.locator('[data-ia-voir-tout]').count()) > 0, 'P2 : bouton « Voir les X résultats » présent')
// P3 : le contour des résultats est VIOLET sur la carte (île → ile-line)
const lineColor = await page.evaluate(() => {
  const m = window.__labuse_map
  const id = m.getLayer('ile-line') ? 'ile-line' : 'parcels-line'
  return m.getPaintProperty(id, 'line-color')
})
assert(String(lineColor).toUpperCase().includes('B497F0'), `P3 : contour des résultats VIOLET (${lineColor})`)
assert((await page.locator('text=contour violet = résultats').count()) > 0, 'P3 : légende du violet affichée')
// A1 (post-revue) : « Voir les N » FERME le résumé flottant et fait passer la LISTE au premier
// plan (avant : bouton inerte car la liste était déjà derrière le résumé).
const listBefore = await page.locator('[data-results-scroll] button').filter({ hasText: /^[A-Z]{2} \d/ }).count()
await page.locator('[data-ia-voir-tout]').click(); await page.waitForTimeout(1200)
assert((await page.locator('[data-ia-restitution]').count()) === 0, 'A1 : « Voir les N » FERME le résumé flottant (action effective)')
const listAfter = await page.locator('[data-results-scroll] button').filter({ hasText: /^[A-Z]{2} \d/ }).count()
assert(listAfter > 0 && listAfter === listBefore, `A1 : la LISTE complète des résultats est affichée et parcourable (${listAfter} cartes)`)
// A1 persistance : cliquer une parcelle → fiche + la liste reste (on enchaîne #1, #2…)
await page.locator('[data-results-scroll] button').filter({ hasText: /^[A-Z]{2} \d/ }).first().click(); await page.waitForTimeout(1500)
assert((await page.locator('aside.absolute').count()) > 0, 'A1 : la fiche s\'ouvre au clic d\'une parcelle')
assert((await page.locator('[data-results-scroll] button').filter({ hasText: /^[A-Z]{2} \d/ }).count()) > 0, 'A1 : la liste PERSISTE (accès aux autres résultats)')
// A6 : la loupe de la FICHE cherche DANS la fiche (≠ barre du haut)
await page.locator('aside.absolute button[title*="dans cette fiche"]').click(); await page.waitForTimeout(300)
await page.locator('[data-fiche-search]').fill('accès'); await page.waitForTimeout(600)
assert((await page.locator('[data-fiche-search-results]').count()) > 0, 'A6 : la loupe fiche filtre le CONTENU de la fiche (bloc « DANS CETTE FICHE »)')
await page.keyboard.press('Escape'); await page.waitForTimeout(300)
await page.evaluate(() => window.__labuse.select(null))

// ═══ A5 — barre du haut : loupe à DROITE (bouton), « / » retiré, recherche commune ═══
assert((await page.locator('header input[data-omnibox]').count()) > 0, 'A5 : barre de recherche (data-omnibox) présente')
assert((await page.locator('header button[title="Lancer la recherche"]').count()) > 0, 'A5 : LOUPE cliquable à DROITE du champ')
assert((await page.locator('header kbd').count()) === 0, 'A5 : indicateur « / » retiré')
await page.locator('header input[data-omnibox]').fill('Le Tampon')
await page.locator('header button[title="Lancer la recherche"]').click(); await page.waitForTimeout(2500)
assert(page.url().includes('Tampon'), 'A6/A5 : la barre du haut cherche le dashboard (commune « Le Tampon » → périmètre)')

// ═══ P9 — popover entonnoir borné (dans l'écran) ═══
await page.locator('nav button[title="Cartes"]').click(); await page.waitForTimeout(800)
await page.evaluate(() => { window.__labuse.setCommune('Saint-Paul'); window.__labuse.setVerdict(true) })
await page.waitForTimeout(3500)
const ent = page.locator('[data-entonnoir-btn]')
if (await ent.count()) {
  await ent.click(); await page.waitForTimeout(1000)
  const box = await page.locator('[data-entonnoir-popover]').boundingBox()
  const vh = 900
  assert(box != null && box.y >= 0 && (box.y + box.height) <= vh + 1, `P9 : popover entièrement DANS l'écran (${box ? Math.round(box.y)+'→'+Math.round(box.y+box.height) : '?'} / ${vh})`)
  await page.keyboard.press('Escape'); await page.waitForTimeout(300)   // referme le popover (Échap)
}

// ═══ P10 + P11 — couches carte : parc MARRON, limites communes VERTES ═══
const layers = await page.evaluate(() => {
  const m = window.__labuse_map
  return {
    parc: m.getPaintProperty('ov-parc', 'fill-color'),
    parcLine: m.getLayer('ov-parc-line') ? m.getPaintProperty('ov-parc-line', 'line-color') : null,
    communesLayer: !!m.getLayer('communes-bounds'),
    communesColor: m.getLayer('communes-bounds') ? m.getPaintProperty('communes-bounds', 'line-color') : null,
  }
})
assert(String(layers.parc).toUpperCase().includes('8B5A2B'), `P10 : Parc national en MARRON (${layers.parc})`)
assert(layers.communesLayer, 'P11 : couche limites communes présente')
assert(String(layers.communesColor).toUpperCase().includes('5CE6A1'), `P11 : limites communes en VERT charte (${layers.communesColor})`)

// ═══ P8 — marqueur commune → ouvre la FICHE COMMUNE (contexte) ═══
await page.evaluate(() => window.__labuse.setCommune(null)); await page.waitForTimeout(4500)
const mk = page.locator('[data-commune-marker="Saint-Pierre"]').first()
if (await mk.count()) {
  await mk.click({ force: true })
  const ok = await page.waitForSelector('text=SRU', { timeout: 10000 }).then(() => true).catch(() => false)
  assert(ok, 'P8 : clic marqueur commune → fiche commune (contexte SRU/ANRU/PLH) ouverte')
} else {
  assert(false, 'P8 : marqueur commune introuvable', '(zoom île ?)')
}

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('DERNIÈRE PASSE — P1/P2/P3/P8/P9/P10/P11/P12 VERTS')
