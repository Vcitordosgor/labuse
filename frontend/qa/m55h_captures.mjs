// M55-H — captures des 11 points + sondes non-régression (dev server :5173).
// Usage : cd frontend && node qa/m55h_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = process.env.OUT || '../reports/m55-h/captures'
const BASE = process.env.BASE || 'http://localhost:5173/socle/'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const errors = []
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()) })
const shot = (loc, name) => loc.screenshot({ path: `${OUT}/${name}.png` }).catch((e) => console.log(`✗ ${name}: ${e.message.split('\n')[0]}`))

await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(2200)
const aside = page.locator('aside').first()

// ── H2 : accueil ── (état initial : accueil visible sous les sections)
await shot(aside, 'h2_accueil')
// ── H1 : chevrons (fermé/ouvert) ──
await shot(page.locator('[data-filtres-toggle]'), 'h1_chevron_ferme')
await shot(page.locator('[data-couches-toggle]'), 'h1_chevron_ouvert')

// ── H8 : cliquer le titre de la section OUVERTE (Couches) ne la ferme pas ──
await page.locator('[data-couches-toggle]').click(); await page.waitForTimeout(400)
const couchesToujours = await page.locator('[data-couches-drawer]').count()
console.log('H8 — clic sur section ouverte, reste ouverte :', couchesToujours > 0)
// ouvrir Filtres → Couches se replie ; jamais zéro section
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(800)
const etat = { filtres: await page.locator('[data-filtres-drawer]').count(), couches: await page.locator('[data-couches-drawer]').count() }
console.log('H8 — filtres ouvert / couches repliée :', JSON.stringify(etat))

// ── H3 : zone des deux boutons + reset séparé ──
await page.locator('[data-filtres-drawer]').evaluate((el) => { el.scrollTop = el.scrollHeight })
await page.waitForTimeout(300)
await shot(aside, 'h3_zone_boutons')
// ── H7 : menu périmètre une ligne ──
await page.locator('[data-commune-select]').click(); await page.waitForTimeout(600)
await shot(page.locator('.floating').first(), 'h7_menu_perimetre')
await page.keyboard.press('Escape'); await page.waitForTimeout(300)

// ── analyse : rituel + H5 groupes + H9 IDU + H10 ventilation ──
const t0 = Date.now()
await page.locator('[data-analyser-btn]').click()
await page.locator('[data-voir-parcelles]').waitFor({ timeout: 10000 })
console.log('rituel (clic → Voir) :', Date.now() - t0, 'ms')
await page.locator('[data-voir-parcelles]').click()
await page.locator('[data-results-scroll] > button').first().waitFor({ timeout: 30000 })
await page.waitForTimeout(2500)
await shot(aside, 'h9_h10_liste_idu_ventilation')
const vent = await page.locator('[data-results-panel] p.mt-3').first().innerText()
console.log('H10 ventilation :', vent.replace(/\n/g, ' '))
const chips = await page.locator('[data-tier-chip]').allInnerTexts()
console.log('H5 groupes (uniq):', [...new Set(chips.map(c => c.split(' ·')[0]))].join(' → '))
const ref = await page.locator('[data-results-scroll] > button').first().innerText()
console.log('H9 1re carte :', JSON.stringify(ref.split('\n')[0]))

// ── H4 : tri Surface — les deux sens ──
await page.locator('[data-sort="surface"]').click(); await page.waitForTimeout(2500)
let pill = await page.locator('[data-sort="surface"]').innerText()
const s1 = await page.locator('[data-results-scroll] > button').first().innerText()
await page.locator('[data-sort="surface"]').click(); await page.waitForTimeout(2500)
const pill2 = await page.locator('[data-sort="surface"]').innerText()
const s2 = await page.locator('[data-results-scroll] > button').first().innerText()
console.log('H4 :', JSON.stringify(pill), '1re =', s1.split('\n')[2], '→ re-clic', JSON.stringify(pill2), '1re =', s2.split('\n')[2])
await shot(page.locator('[data-tri-bar]'), 'h4_tri_surface_asc')

// ── H11 : modale sans ligne de date ──
await page.locator('[data-comprendre-btn]').click(); await page.waitForTimeout(600)
const dateLigne = await page.locator('[data-algo-date]').count()
const modaleTxt = await page.locator('[data-algo-overlay]').innerText()
console.log('H11 — ligne de date absente :', dateLigne === 0, '· q_v8/12-07 dans modale :',
  /q_v8|12\/07\/2026/.test(modaleTxt))
await shot(page.locator('[data-algo-overlay] > div'), 'h11_modale')
await page.locator('[data-algo-overlay]').click({ position: { x: 10, y: 10 } }); await page.waitForTimeout(300)

// ── H11 : page Sources — dates de sources PRÉSENTES, date de run ABSENTE ──
await page.evaluate(() => { const a = document.querySelector('[data-nav-sources]'); if (a) a.click() })
await page.waitForTimeout(300)
// fallback : navigation par le menu si data-nav absent
if (!(await page.locator('[data-sources-page]').count())) {
  await page.locator('text=Sources').first().click().catch(() => {})
  await page.waitForTimeout(1500)
}
if (await page.locator('[data-sources-page]').count()) {
  const src = await page.locator('[data-sources-page]').innerText()
  console.log('H11 Sources — run/date absents :', !/q_v8|gelé le|12\/07\/2026/.test(src),
    '· dates de sources présentes :', /2026|2025/.test(src))
  await shot(page.locator('[data-sources-modele]'), 'h11_sources_modele')
}

// ── NR : carte == liste (M55-G) — Salazie + procédure ──
const p2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await p2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 }); await p2.waitForTimeout(2000)
await p2.locator('[data-filtres-toggle]').click(); await p2.waitForTimeout(600)
await p2.locator('button:has-text("97433")').click(); await p2.waitForTimeout(500)
await p2.locator('[data-signaux-vie] button:has-text("Procédure collective")').click(); await p2.waitForTimeout(1000)
await p2.locator('[data-analyser-btn]').click(); await p2.waitForTimeout(3800)
await p2.locator('[data-voir-parcelles]').click(); await p2.waitForTimeout(2500)
await p2.evaluate(() => window.__labuse_map.flyTo({ center: [55.54, -21.03], zoom: 13, duration: 0 }))
await p2.waitForTimeout(3500)
const cl = await p2.evaluate(() => {
  const m = window.__labuse_map
  const ids = new Set(m.queryRenderedFeatures({ layers: ['ile-fill'] }).map((f) => f.properties?.idu))
  return ids.size
})
const pied = await p2.locator('[data-results-panel]').innerText()
console.log('NR carte==liste — liste :', (pied.match(/(\d[\d\s ]*) affichée/) || [,'?'])[1], '· peintes :', cl)
await p2.close()

// ── NR mobile ──
await page.setViewportSize({ width: 375, height: 720 })
await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
await page.locator('[data-couches-mobile]').click(); await page.waitForTimeout(800)
await page.screenshot({ path: `${OUT}/nr_mobile.png` })

console.log('captures OK →', OUT, '· console errors:', errors.length)
console.log(errors.slice(0, 4).join('\n'))
await browser.close()
