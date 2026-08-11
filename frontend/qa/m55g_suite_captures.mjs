// M55-G suite — captures des 8 ajustements + non-régression (dev server :5173).
// Usage : cd frontend && node qa/m55g_suite_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const OUT = process.env.OUT || '../reports/m55-g/captures/suite'
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

// ── S5/S6/S7/S4 : panneau Filtres (sans bandeau, CTA renommé, sans sous-titres, 7 signaux) ──
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(1200)
await shot(aside, 's7_panneau_sans_soustitres')
await shot(page.locator('[data-signaux-vie]'), 's4_signaux_7_un_niveau')
await shot(page.locator('[data-appel]'), 's5_s6_appel_sans_bandeau')
const nSignaux = await page.locator('[data-signaux-vie] button').count()
const plus = await page.locator('[data-signaux-plus]').count()
console.log('signaux (chips+i attendu 7):', nSignaux, '· lien "Plus de signaux" (attendu 0):', plus)

// ── rituel 3 s + S3 (état post-analyse) + S2 (tri) ──
const t0 = Date.now()
await page.locator('[data-analyser-btn]').click()
await page.locator('[data-voir-parcelles]').waitFor({ timeout: 10000 })
console.log('rituel (clic → Voir) :', Date.now() - t0, 'ms')
await page.locator('[data-voir-parcelles]').click(); await page.waitForTimeout(2000)
await shot(page.locator('[data-tri-bar]'), 's2_tri_une_ligne')
await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(1000)
await shot(aside, 's3_post_analyse_deux_boutons')
const drawerTxt = await page.locator('[data-filtres-drawer]').innerText()
console.log('post-analyse — "Relancer" présent :', drawerTxt.includes('Relancer l’analyse'),
  '· chips verdict absentes :', !drawerTxt.includes('Brûlante'), '· phrase absente :', !drawerTxt.includes('LABUSE a analysé'))
// S6 : la modale porte la date du run (S5)
await page.locator('[data-comprendre-btn]').click().catch(() => {})
await page.waitForTimeout(600)
const dateOk = await page.locator('[data-algo-date]').innerText().catch(() => 'absent')
console.log('modale — date du run :', dateOk)
await page.locator('[data-algo-overlay]').click({ position: { x: 10, y: 10 } }).catch(() => {})
await page.waitForTimeout(300)

// ── S8 : mode factuel — tri Surface ↓ ──
if (!(await page.locator('[data-filtres-drawer]').count())) {
  await page.locator('[data-filtres-toggle]').click(); await page.waitForTimeout(600)
}
const des = page.locator('[data-desactiver]')
if (await des.count()) { await des.click(); await page.waitForTimeout(600) }
await page.locator('[data-voir-factuel]').click()
await page.locator('[data-results-scroll] > button').first().waitFor({ timeout: 20000 })
await page.waitForTimeout(400)
await shot(aside, 's8_factuel_surface_desc')
const pill = await page.locator('[data-sort="surface"]').innerText()
console.log('pill surface active :', JSON.stringify(pill))

// ── Non-régression : vieux lien avec clés sv= SUPPRIMÉES (nu_pm, cession) ──
const p2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await p2.goto(BASE + '#f=1&sv=nu_pm,cession,procedure&al=1', { waitUntil: 'networkidle', timeout: 60000 })
await p2.waitForTimeout(2500)
await p2.locator('[data-filtres-toggle]').click(); await p2.waitForTimeout(1000)
const t2 = await p2.locator('[data-filtres-drawer]').innerText()
const compteur = (t2.match(/[\d\s ]+ parcelles correspondent[^\n]*/) || ['absent'])[0]
console.log('vieux lien sv=nu_pm,cession,procedure → compteur :', compteur.trim(),
  '(attendu : le compte de « procedure » seul, 658)')
await p2.close()

// ── Non-régression : mobile 375 ──
await page.setViewportSize({ width: 375, height: 720 })
await page.goto(BASE, { waitUntil: 'networkidle' }); await page.waitForTimeout(2000)
await page.locator('[data-couches-mobile]').click(); await page.waitForTimeout(800)
await page.screenshot({ path: `${OUT}/nr_mobile.png` })

console.log('captures suite OK →', OUT, '· console errors:', errors.length)
console.log(errors.slice(0, 5).join('\n'))
await browser.close()
