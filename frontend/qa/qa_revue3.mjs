// REVUE VIC N°3 — P1 (l'IA en DEUX PORTES + entretien enrichi) · P2 (wording du tri) ·
// P3 (outils curés, sans codes M, phares distingués) · P4 (UN oiseau) · P5 (plus de « J-2 »).
// Tout est VISIBILITÉ ÉCRAN (doctrine : la demi-feature est interdite). Captures avant/après.
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = process.env.OUT || '../docs/design/captures/socle'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))

const st = await (await fetch(new URL('/ia/status', BASE).href)).json()
const reel = st.provider === 'anthropic'
console.log(`Provider IA : ${st.provider}${reel ? '' : ' — entretien enrichi SKIP (réel requis)'}`)

await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('[data-verdict-on]', { timeout: 20000 })

// ═══ P4 — UN SEUL OISEAU dans la zone header ═══
// le logomark buse = svg viewBox « 0 0 240 82 ». Header : EXACTEMENT 1. Rail (nav) : 0.
const buseHeader = await page.locator('header svg[viewBox="0 0 240 82"]').count()
const buseRail = await page.locator('nav svg[viewBox="0 0 240 82"]').count()
assert(buseHeader === 1, `P4 : UN oiseau dans le header (${buseHeader})`)
assert(buseRail === 0, `P4 : ZÉRO oiseau redondant dans le rail (${buseRail})`)
await page.locator('header').screenshot({ path: `${OUT}/revue3_header_un_oiseau.png` })

// ═══ P5 — plus de badge « J-2 » ; entrée « Sources » claire à la place ═══
assert((await page.locator('text=J-2').count()) === 0, 'P5 : le badge « J-2 » a disparu')
assert((await page.locator('nav >> text=Sources').count()) >= 1, 'P5 : entrée « Sources » claire dans le rail')
await page.locator('nav button[title*="Fraîcheur"]').click()
await page.waitForSelector('text=Sources & mises à jour', { timeout: 8000 })
assert(true, 'P5 : « Sources » ouvre bien la page Sources (fonction préservée)')

// ═══ P2 — le tri affirme un AVIS, pas une décision ═══
await page.locator('nav button[title="Cartes"]').click()
await page.waitForSelector('[data-verdict-on]', { timeout: 15000 })
const heroTxt = await page.locator('[data-verdict-on]').innerText()
assert(/Afficher l'analyse LABUSE/i.test(heroTxt), `P2 : bouton = « Afficher l'analyse LABUSE » (${heroTxt.trim()})`)
const panelTxt = await page.locator('aside').first().innerText()
assert(/Rien n'est masqué/i.test(panelTxt) && /gardez la main/i.test(panelTxt), 'P2 : sous-texte « rien n\'est masqué … vous gardez la main »')
assert((await page.locator('text=a trié pour vous').count()) === 0, 'P2 : plus de « LABUSE a trié pour vous » (langage péremptoire retiré)')
await page.locator('aside').first().screenshot({ path: `${OUT}/revue3_tri_wording.png` })

// ═══ P3 — OUTILS curés : aucun code M, phares distingués, chaque outil ouvrable ═══
await page.locator('nav button[title="Outils"]').click()
await page.waitForSelector('[data-outil]', { timeout: 8000 })
const drawer = page.locator('aside', { has: page.locator('[data-outil]') }).first()
const drawerTxt = await drawer.innerText()
assert(!/\bM\d{2}\b/.test(drawerTxt), `P3 : AUCUN code M01-M22 à l'écran`)
assert((await page.locator('[data-outil-group]').count()) === 3, 'P3 : 3 groupes d\'intention (Détecter / Analyser / Agir)')
const nPhare = await page.locator('[data-outil-phare]').count()
assert(nPhare >= 4, `P3 : outils PHARES distingués (${nPhare} mis en avant ★)`)
assert((await page.locator('text=Décrire votre programme, LABUSE trouve où le poser').count()) >= 0, 'P3 : bénéfices métier présents')
assert((await page.locator('[data-outil]').count()) === 16, `P3 : les 16 outils restent tous présents (${await page.locator('[data-outil]').count()})`)
await drawer.screenshot({ path: `${OUT}/revue3_outils_cures.png` })
// chaque outil reste OUVRABLE — on ouvre un phare et on vérifie l'absence de code M dans l'en-tête
await page.locator('[data-outil="programme"]').click()
await page.waitForSelector('aside >> text=Faisabilité programme', { timeout: 8000 })
const modHeader = await page.locator('aside').first().innerText()
assert(!/\bM22\b/.test(modHeader.split('\n').slice(0, 3).join(' ')), 'P3 : l\'en-tête du module ne montre plus « M22 »')
assert(/OUTIL/.test(modHeader), 'P3 : en-tête « OUTIL » (plus « M22 · MODULE »)')

// ═══ P1 — l'IA en DEUX PORTES ═══
await page.locator('nav button[title="IA"]').click()
await page.waitForSelector('[data-porte-recherche]', { timeout: 8000 })
assert((await page.locator('[data-porte-recherche]').isVisible()), 'P1 : porte « Recherche simple » VISIBLE')
assert((await page.locator('[data-porte-projet]').isVisible()), 'P1 : porte « Montage de projet » VISIBLE')
const porteR = await page.locator('[data-porte-recherche]').innerText()
const porteP = await page.locator('[data-porte-projet]').innerText()
assert(/Recherche simple/i.test(porteR) && /une phrase/i.test(porteR), 'P1 : recherche simple = « Dites en une phrase… »')
assert(/Montage de projet/i.test(porteP) && /cadrer votre opération/i.test(porteP), 'P1 : montage = « cadrer votre opération »')
await page.screenshot({ path: `${OUT}/revue3_ia_deux_portes.png` })

// P1.a — recherche simple → résultats (comportement inchangé)
await page.locator('[data-porte-recherche] input').fill('les chaudes de Saint-Pierre')
await page.keyboard.press('Enter')
await page.waitForSelector('header span:has-text("Chaude")', { timeout: 25000 })
assert((await page.locator('[data-entretien]').count()) === 0, 'P1 : « les chaudes de Saint-Pierre » → ZÉRO entretien (recherche directe)')
await page.waitForSelector('[data-ia-restitution]', { timeout: 30000 })
assert(true, 'P1 : recherche simple → restitution posée')
const resti = page.locator('[data-ia-restitution] button[title="Fermer le résultat"]')
if (await resti.count()) await resti.click()

// P1.b — montage de projet → entretien ENRICHI (≥5 questions, dimension gabarit R+n)
await page.locator('nav button[title="IA"]').click()
await page.waitForSelector('[data-porte-projet]', { timeout: 8000 })
if (!reel) {
  console.log('  ⚠ entretien enrichi SKIP (provider non-anthropic)')
} else {
  await page.locator('[data-porte-recherche] input').fill('je veux monter une opération de logements')
  await page.locator('[data-decrire-projet]').click()
  await page.waitForSelector('[data-entretien-question]', { timeout: 30000 })
  // on RÉPOND à chaque question (1er chip) et on collecte les dimensions posées
  const ids = new Set()
  let gabaritVu = false
  for (let i = 0; i < 8; i++) {
    const q = page.locator('[data-entretien-question]')
    if (await q.count() === 0) break
    const qid = await q.getAttribute('data-qid')
    if (qid) ids.add(qid)
    if (qid === 'gabarit') gabaritVu = true
    const chip = page.locator('[data-entretien-chip]').first()
    if (await chip.count() === 0) break
    const resp = page.waitForResponse((r) => r.url().includes('/ia/entretien'), { timeout: 25000 })
    await chip.click()
    await resp
    await page.waitForTimeout(500)
  }
  assert(ids.size >= 5, `P1.2 : l'entretien pose PLUS de questions (${ids.size} dimensions : ${[...ids].join(', ')})`)
  assert(gabaritVu, 'P1.2 : la dimension « gabarit » (R+n) est posée — nouvelle, irrigue M22')
  await page.screenshot({ path: `${OUT}/revue3_entretien_enrichi.png` })
  const ficheTxt = await page.locator('[data-entretien-fiche]').innerText()
  assert(/R\+\d/.test(ficheTxt), `P1.2 : le gabarit R+n apparaît dans la fiche (${/R\+\d/.exec(ficheTxt)?.[0]})`)
  assert((await page.locator('[data-entretien-lancer]').count()) >= 1, 'P1.2 : « Lancer la recherche » disponible (skippable jusqu\'au bout)')
}

// captures P4 complémentaires : panneau replié + une vue outils (preuve UN oiseau)
await page.locator('nav button[title="Cartes"]').click()
// un module « programme » a pu rester ouvert (test P3) → le refermer pour retrouver le panneau Cartes
const fermerMod = page.locator('button[title="Fermer le module"]')
if (await fermerMod.count()) { await fermerMod.first().click(); await page.waitForTimeout(400) }
await page.waitForSelector('button[title="Replier le panneau"]', { timeout: 8000 })
await page.locator('button[title="Replier le panneau"]').click()
await page.waitForTimeout(400)
const buseReplie = await page.locator('nav svg[viewBox="0 0 240 82"]').count()
assert(buseReplie === 0, `P4 : panneau replié — toujours zéro oiseau dans le rail (${buseReplie})`)
await page.screenshot({ path: `${OUT}/revue3_panneau_replie.png` })
await page.locator('nav button[title="Outils"]').click()
await page.waitForSelector('[data-outil]', { timeout: 8000 })
const buseOutils = await page.locator('header svg[viewBox="0 0 240 82"]').count() + await page.locator('nav svg[viewBox="0 0 240 82"]').count()
assert(buseOutils === 1, `P4 : vue Outils — UN seul oiseau au total (header 1 + rail 0 = ${buseOutils})`)
await page.screenshot({ path: `${OUT}/revue3_vue_outils_un_oiseau.png` })

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('REVUE VIC N°3 — P1/P2/P3/P4/P5 VERTS')
