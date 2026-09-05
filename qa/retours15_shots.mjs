// RETOURS-15 — recette navigateur + captures U1-U8. PHASE=avant|apres, ONLY=U1,U2…
// Lancer depuis frontend/ (copie locale) : CHROME=<exe> PHASE=apres node ./retours15_shots.mjs
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000/socle/'
const OUT = '../docs/audit-2026-09/RETOURS-15/captures'
fs.mkdirSync(OUT, { recursive: true })
const SUFFIX = process.env.PHASE || 'apres'
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean)
const run = (s) => !ONLY.length || ONLY.includes(s)
const VP = Number(process.env.VP || 1440)

const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: VP, height: 900 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
const errors = []
page.on('pageerror', (e) => errors.push(String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}-${SUFFIX}.png` }); console.log('  shot', n, SUFFIX) }
let _n = 0
const go = async (hash = '') => { await page.goto(`${BASE}?r15=${++_n}${hash}`, { waitUntil: 'networkidle' }); await page.waitForTimeout(1500) }
const outil = async (key) => {
  await go()
  await page.click('[data-rail="outils"]'); await page.waitForTimeout(500)
  await page.click(`[data-outil="${key}"]`); await page.waitForTimeout(1400)
}
const basemap = async (label) => {
  await page.click('button[title="Fond de plan"]')
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: label, exact: true }).first().click()
  await page.waitForTimeout(2500)
  await page.mouse.click(400, 860)
  await page.waitForTimeout(300)
}
const jump = async (lon, lat, z, wait = 4000) => {
  await page.evaluate(([ln, lt, zz]) => window.__labuse_map?.jumpTo({ center: [ln, lt], zoom: zz }), [lon, lat, z])
  await page.waitForTimeout(wait)
}
const report = {}

// ── U1 — ortho entière, mer comprise, sans masque : 3 cadrages × 2 fonds + couture z12/13 ──
if (run('U1')) {
  await go()
  await basemap('Ortho IGN')
  await page.waitForTimeout(3500)
  await shot('U1-ortho-ile')                        // 1. île entière dézoomée : mer bleue continue
  await jump(55.222, -21.057, 15.6, 6000)
  await shot('U1-ortho-st-gilles-port')             // 2. port de plaisance : jetée ENTIÈRE, pas de biseau
  await jump(55.45, -20.878, 16, 6000)
  await shot('U1-ortho-st-denis-z16')               // 3. St-Denis z16 : Ortho Express nette
  await jump(55.222, -21.057, 12, 5000)
  await shot('U1-ortho-cote-z12')                   // couture : générique seul
  await jump(55.222, -21.057, 13.2, 5000)
  await shot('U1-ortho-cote-z13')                   // couture : Express au-dessus — pas de saut visible
  await go()
  await basemap('Plan IGN')
  await page.waitForTimeout(3000)
  await shot('U1-plan-ile')                         // même règle sur le fond IGN
  await jump(55.222, -21.057, 15.6, 5000)
  await shot('U1-plan-st-gilles-port')
}

// ── U2 — le PC de l'hôtel : fiche BC0331 + carte (mode « Tous », zoom chantier) ──
if (run('U2')) {
  await go('#idu=97418000BC0331')
  await page.waitForTimeout(3000)
  const autour = page.locator('text=Autour de cette parcelle').first()
  if (await autour.count()) { await autour.scrollIntoViewIfNeeded(); await autour.click(); await page.waitForTimeout(2500) }
  const bloc = page.locator('[data-permis-proximite]').first()
  if (await bloc.count()) await bloc.scrollIntoViewIfNeeded()
  await page.waitForTimeout(600)
  await shot('U2-fiche-BC0331-permis')
  await bloc.locator('button, [role="button"]').first().click().catch(() => {})
  await page.waitForTimeout(2500)
  report.U2_drawer_pc = await page.locator('text=97441816A0077').count()
  report.U2_drawer_origine = await page.locator("text=parcelle d'origine").count()
  await shot('U2-fiche-permis-drawer')
  // carte : outil permis, segment « Tous », ortho, zoom chantier
  await go('#m=permis')
  await page.waitForTimeout(3000)
  await page.click('[data-permis-seg="tous"]').catch(() => {})
  await page.waitForTimeout(3500)
  report.U2_compteur = await page.locator('text=/sur la carte/').first().innerText().catch(() => '?')
  await basemap('Ortho IGN')
  await jump(55.5122, -20.89435, 17.2, 6000)
  await shot('U2-carte-chantier-tous')
}

// ── U3 — libellés + « Tout » toujours dernier ──
if (run('U3')) {
  await go('#m=permis')
  await page.waitForTimeout(2500)
  report.U3_seg = await page.locator('[data-permis-segment]').innerText().catch(() => '?')
  await shot('U3-permis-segment')
  await page.click('[data-permis-filtres-toggle]')
  await page.waitForTimeout(800)
  await shot('U3-permis-filtres')
  // Radar (catégorie) : les 3 segments du tiroir de filtres
  await go('#radar=1')
  await page.waitForTimeout(2500)
  const drw = page.locator('[data-radar-filtrer]').first()
  if (await drw.count()) { await drw.click(); await page.waitForTimeout(800) }
  if (await page.locator('[data-radar-drawer]').count()) await shot('U3-radar-filtres')
}

// ── U4 — plus AUCUNE barre horizontale : scan global 1280/1440 sur les écrans clés ──
if (run('U4')) {
  const scan = () => page.evaluate(() => {
    const out = []
    for (const el of document.querySelectorAll('*')) {
      const cs = getComputedStyle(el)
      if (el.clientWidth > 40 && el.scrollWidth > el.clientWidth + 2 &&
          (cs.overflowX === 'auto' || cs.overflowX === 'scroll')) {
        out.push(`${el.tagName}.${String(el.className).slice(0, 60)} (${el.scrollWidth}>${el.clientWidth})`)
      }
    }
    return out
  })
  await go('#m=permis')
  await page.waitForTimeout(3000)
  report[`U4_permis_${VP}`] = await scan()
  await shot(`U4-permis-liste-${VP}`)
  await outil('communes')
  await page.click('[data-communes-porte="comparaison"]').catch(() => {})
  await page.waitForTimeout(2500)
  report[`U4_communes_${VP}`] = await scan()
  await outil('communes')
  await page.click('[data-communes-porte="evolution"]').catch(() => {})
  await page.waitForTimeout(2500)
  report[`U4_evolution_${VP}`] = await scan()
  await go('#idu=97418000BC0331')
  await page.waitForTimeout(3000)
  report[`U4_fiche_${VP}`] = await scan()
}

// ── U5 — toiture : servie / non déterminée (les états à l'écran) ──
if (run('U5')) {
  const fiche = async (idu) => {
    await outil('prospection-solaire')
    await page.click('[data-solaire-mode="ensoleillement"]')
    await page.waitForTimeout(1000)
    await page.fill('[data-solaire-idu]', idu)
    await page.press('[data-solaire-idu]', 'Enter')
    await page.waitForTimeout(5000)
    const cand = page.locator('[data-parcelinput-candidat]')
    if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(5000) }
  }
  await fiche('97411000AV0056')
  report.U5_servie = await page.locator('text=simple pente').count()
  await shot('U5-fiche-toit-servi')
  await fiche('97411000CE0134')
  report.U5_pans_non_nets = await page.locator('text=pans non nets').count()
  await shot('U5-fiche-toit-non-determine')
}

// ── U6 — taxe : « SDP restante au gabarit (parcelle déjà bâtie) » + ligne d'assiette ──
if (run('U6')) {
  await outil('taxe-amenagement')
  await page.fill('[data-taxe-parcelle]', 'BZ1065')
  await page.press('[data-taxe-parcelle]', 'Enter')
  await page.waitForTimeout(2500)
  const cand = page.locator('[data-parcelinput-candidat]')
  if (await cand.count()) { await cand.first().click(); await page.waitForTimeout(2500) }
  report.U6_restante = await page.locator('text=restante').count()
  report.U6_deja_batie = await page.locator('text=parcelle déjà bâtie').count()
  await shot('U6-taxe-prefill')
  const res = page.locator('[data-taxe-resultat]')
  if (await res.count()) {
    await res.scrollIntoViewIfNeeded()
    await page.waitForTimeout(400)
    report.U6_assiette = await page.locator('text=taux non renseigné').count()
    await shot('U6-taxe-resultat')
  }
}

// ── U7 — adresse sur UNE ligne, pleine largeur ──
if (run('U7')) {
  await go('#idu=97418000BC0331')
  await page.waitForTimeout(3000)
  const addr = page.locator('[data-fiche-adresse] > span').first()
  if (await addr.count()) {
    report.U7_une_ligne = await addr.evaluate((el) => {
      const cs = getComputedStyle(el)
      return { lignes: Math.round(el.getBoundingClientRect().height / parseFloat(cs.lineHeight || '14')),
               largeur: el.clientWidth, texte: el.textContent }
    })
  }
  await shot('U7-fiche-adresse')
}

// ── U8 — annuaire PLU : Saint-André / Saint-Leu (GPU vide dit + mairie) + servable (zip) ──
if (run('U8')) {
  await outil('plu')
  await page.click('[data-plu-voie="annuaire"]').catch(() => {})
  await page.waitForTimeout(2500)
  await page.click('[data-plu-commune="97409"]')
  await page.waitForTimeout(3500)
  report.U8_standre_pack = await page.locator('[data-plu-pack-vigueur]').count()
  report.U8_standre_absent = await page.locator('[data-plu-pack-absent]').count()
  await shot('U8-saint-andre')
  await page.click('[data-plu-retour]')
  await page.waitForTimeout(800)
  await page.click('[data-plu-commune="97413"]')
  await page.waitForTimeout(3500)
  await shot('U8-saint-leu')
  await page.click('[data-plu-retour]')
  await page.waitForTimeout(800)
  await page.click('[data-plu-commune="97411"]')   // contrôle : servable → zip direct
  await page.waitForTimeout(2000)
  report.U8_servable_zip = await page.locator('[data-plu-integral]').count()
  await shot('U8-servable-zip')
}

console.log('REPORT', JSON.stringify(report, null, 1))
console.log('erreurs page:', JSON.stringify(errors.slice(0, 10)))
await browser.close()
